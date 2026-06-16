# detection.py - R-Peak Detection

''' 
This module is responsible for finding R-peaks in a continuous, streaming
ECG signal chunks using the Pan-Tompkins algorithm — the industry standard for
real-time QRS detection.

The R-peak is the sharp, high-amplitude spike at the centre of the QRS
complex, produced by rapid ventricular depolarisation. It is the most
reliably detectable feature in the ECG and serves as the temporal anchor
for everything else: RR intervals, heart rate, and the P, Q, S, and T waves 
of each individual beat.

HOW IT WORKS
------------
Incoming chunks are processed through: derivative → square → moving-window
integration, producing an envelope that peaks at each QRS. A dual-threshold
scheme with searchback separates true peaks from noise.

ADAPTIVE IMPROVEMENTS
---------------------
The baseline Pan-Tompkins algorithm uses fixed parameters tuned for narrow,
normal-morphology QRS complexes. This implementation extends it with three
adaptive behaviours that improve robustness on abnormal beats (PVCs, BBB):

1. Adaptive snap radius           — scales with recent QRS width
2. Adaptive refractory period     — grows for wide beats, preventing double-detection
3. Slope quality gate             — rejects candidates lacking R-peak's steep bilateral slope

POSITION IN PIPELINE
--------------------
filters.py     →   preprocesses the raw signal (bandpass, notch)
detection.py   →   finds R-peaks in the filtered stream           ← YOU ARE HERE
fiducial.py    →   locates P, Q, S, T within each beat window
'''

import numpy as np
from scipy.signal import find_peaks
from collections import deque
from dataclasses import dataclass, field
from typing import List, Tuple
 
# Physiological bounds for adaptive parameters
MIN_SNAP_RADIUS_MS   = 50    # Normal narrow QRS
MAX_SNAP_RADIUS_MS   = 100   # Wide PVC / BBB
MIN_REFRACTORY_MS    = 250   # Pan-Tompkins default
MAX_REFRACTORY_MS    = 360   # Widest plausible QRS + margin
NORMAL_QRS_WIDTH_MS  = 80    # Seed value before any beats observed
SLOPE_HISTORY_BEATS  = 8     # How many beats to average slope threshold over
 
 
@dataclass
class AdaptiveThresholdState:
    '''
    Maintains adaptive threshold state for Pan-Tompkins dual-threshold method.
 
    Beyond the original threshold tracking, this class also tracks:
      - qrs_widths:    recent QRS width estimates (samples) used to scale the
                       snap radius and refractory period dynamically
      - slope_refs:    recent confirmed R-peak slope strengths used to gate
                       candidate peaks on morphological plausibility
    '''
 
    # Peak history (last 8 detected R-peaks)
    peak_values:      deque = field(default_factory=lambda: deque(maxlen=8))
    peak_times:       deque = field(default_factory=lambda: deque(maxlen=8))
    integrator_peaks: deque = field(default_factory=lambda: deque(maxlen=8))
 
    # QRS width history — drives adaptive snap radius and refractory period
    qrs_widths:       deque = field(default_factory=lambda: deque(maxlen=8))
 
    # Slope reference history — drives the morphological quality gate
    slope_refs:       deque = field(default_factory=lambda: deque(maxlen=SLOPE_HISTORY_BEATS))
 
    # Noise and signal estimates
    noise_level:  float = 0.0
    signal_level: float = 0.0
 
    # Threshold values
    signal_threshold1:     float = 0.0
    signal_threshold2:     float = 0.0
    integrator_threshold1: float = 0.0
    integrator_threshold2: float = 0.0
 
    # ------------------------------------------------------------------ #
    #  Adaptive parameter helpers                                         #
    # ------------------------------------------------------------------ #
 
    def get_mean_qrs_width_ms(self, fs: float) -> float:
        '''
        Return the mean QRS width in milliseconds across recent beats.
        Falls back to a physiologically normal seed if no beats observed yet.
        '''
        if len(self.qrs_widths) == 0:
            return NORMAL_QRS_WIDTH_MS
        return float(np.mean(self.qrs_widths)) / fs * 1000.0
 
    def get_snap_radius(self, fs: float) -> int:
        '''
        Adaptive snap radius in samples.
 
        Scales with mean QRS width so that wide beats (PVCs, BBB) get a
        proportionally wider search window when snapping from the integrator
        peak back to the true R-peak in the filtered signal.
 
        Clamped to [MIN_SNAP_RADIUS_MS, MAX_SNAP_RADIUS_MS].
        '''
        mean_qrs_ms = self.get_mean_qrs_width_ms(fs)
        snap_ms = np.clip(mean_qrs_ms / 2.0, MIN_SNAP_RADIUS_MS, MAX_SNAP_RADIUS_MS)
        return max(1, int((snap_ms / 1000.0) * fs))
 
    def get_refractory_samples(self, fs: float) -> int:
        '''
        Adaptive refractory period in samples.
 
        A wide QRS occupies more time, so the refractory period must grow to
        prevent the trailing edge of the beat being mistaken for the next peak.
 
        Base: MIN_REFRACTORY_MS. Scales linearly with QRS width above normal,
        clamped to MAX_REFRACTORY_MS.
        '''
        mean_qrs_ms = self.get_mean_qrs_width_ms(fs)
        extra_ms = max(0.0, mean_qrs_ms - NORMAL_QRS_WIDTH_MS)
        refractory_ms = np.clip(
            MIN_REFRACTORY_MS + extra_ms,
            MIN_REFRACTORY_MS,
            MAX_REFRACTORY_MS
        )
        return max(1, int((refractory_ms / 1000.0) * fs))
 
    def record_qrs_width(self, width_samples: int):
        self.qrs_widths.append(width_samples)
 
    # ------------------------------------------------------------------ #
    #  Slope quality gate helpers                                         #
    # ------------------------------------------------------------------ #
 
    def record_slope_ref(self, slope_strength: float):
        '''
        Store the slope strength of a confirmed R-peak.
        slope_strength is the minimum of the mean absolute derivative on the
        upslope and downslope windows — a conservative measure of both sides.
        '''
        self.slope_refs.append(slope_strength)
 
    def get_slope_threshold(self) -> float:
        '''
        Return the minimum slope strength a candidate must show to pass the
        quality gate. Set to 30% of the mean confirmed-peak slope so the gate
        rejects clear imposters without clipping legitimate wide/low-amplitude
        beats.
 
        Returns 0.0 (gate open) until enough history is available.
        '''
        if len(self.slope_refs) < 3:
            return 0.0
        return 0.30 * float(np.mean(self.slope_refs))
 
    # ------------------------------------------------------------------ #
    #  Original threshold machinery (unchanged logic, preserved exactly)  #
    # ------------------------------------------------------------------ #
 
    def update_noise_level(self, chunk: np.ndarray, detected_peaks: List[int]):
        if len(detected_peaks) == 0:
            self.noise_level = 0.5 * np.std(chunk)
        else:
            noise_samples = [
                chunk[i] for i in range(len(chunk))
                if not any(abs(i - p) < 50 for p in detected_peaks)
            ]
            self.noise_level = (
                0.5 * np.std(noise_samples) if noise_samples
                else 0.5 * np.std(chunk)
            )
 
    def update_signal_level(self, peak_amplitude: float):
        if len(self.peak_values) == 0:
            self.signal_level = peak_amplitude
        else:
            weights = np.linspace(0.5, 1.0, len(self.peak_values) + 1)
            all_peaks = list(self.peak_values) + [peak_amplitude]
            self.signal_level = np.average(all_peaks, weights=weights)
 
    def update_thresholds(self):
        if len(self.peak_values) == 0:
            self.signal_threshold1 = 0.5 * self.signal_level
            self.signal_threshold2 = 0.25 * self.signal_level
            self.integrator_threshold1 = (
                0.5 * np.mean(list(self.integrator_peaks))
                if self.integrator_peaks else 0.0
            )
            self.integrator_threshold2 = (
                0.25 * np.mean(list(self.integrator_peaks))
                if self.integrator_peaks else 0.0
            )
        else:
            self.signal_threshold1 = (
                self.noise_level + 0.25 * (self.signal_level - self.noise_level)
            )
            self.signal_threshold2 = 0.5 * self.signal_threshold1
 
            if self.integrator_peaks:
                mean_int = np.mean(list(self.integrator_peaks))
                self.integrator_threshold1 = self.noise_level + 0.6 * mean_int
                self.integrator_threshold2 = 0.5 * self.integrator_threshold1
            else:
                self.integrator_threshold1 = 0.0
                self.integrator_threshold2 = 0.0
 
    def record_peak(self, peak_amplitude: float, integrator_peak: float, time_ms: float):
        self.peak_values.append(peak_amplitude)
        self.integrator_peaks.append(integrator_peak)
        self.peak_times.append(time_ms)
        self.update_signal_level(peak_amplitude)
 
    def get_expected_rr_interval(self) -> float:
        if len(self.peak_times) < 2:
            return 360
        return float(np.mean(np.diff(list(self.peak_times))))
 
    def reset(self):
        self.peak_values.clear()
        self.peak_times.clear()
        self.integrator_peaks.clear()
        self.qrs_widths.clear()
        self.slope_refs.clear()
        self.noise_level           = 0.0
        self.signal_level          = 0.0
        self.signal_threshold1     = 0.0
        self.signal_threshold2     = 0.0
        self.integrator_threshold1 = 0.0
        self.integrator_threshold2 = 0.0
 
 
# --------------------------------------------------------------------------- #
#  QRS width estimation                                                        #
# --------------------------------------------------------------------------- #
 
def _estimate_qrs_width(filtered_chunk: np.ndarray, r_idx: int,
                         fs: float, window_ms: float = 80.0) -> int:
    '''
    Estimate QRS width in samples around a confirmed R-peak.
 
    Strategy: walk outward from R until the signal crosses a threshold equal
    to 10% of the R-peak amplitude (the point where the steep QRS slope
    transitions into the flatter ST/PR baseline). The total span between
    left and right crossing points is the QRS width.
 
    Falls back to a normal seed width if the crossing is not found within the
    search window — this prevents runaway estimates on noisy beats.
    '''
    amplitude    = filtered_chunk[r_idx]
    threshold    = 0.10 * abs(amplitude)
    max_half_win = int((window_ms / 1000.0) * fs)
    normal_seed  = int((NORMAL_QRS_WIDTH_MS / 1000.0) * fs)
 
    left = r_idx
    for i in range(r_idx, max(0, r_idx - max_half_win), -1):
        if abs(filtered_chunk[i]) < threshold:
            left = i
            break
 
    right = r_idx
    for i in range(r_idx, min(len(filtered_chunk), r_idx + max_half_win)):
        if abs(filtered_chunk[i]) < threshold:
            right = i
            break
 
    width = right - left
    min_w = int(0.040 * fs)
    max_w = int(0.200 * fs)
    return int(np.clip(width, min_w, max_w)) if width > 0 else normal_seed
 
 
# --------------------------------------------------------------------------- #
#  Slope quality gate                                                          #
# --------------------------------------------------------------------------- #
 
def _measure_slope_strength(filtered_chunk: np.ndarray, r_idx: int,
                              fs: float, window_ms: float = 30.0) -> float:
    '''
    Measure the slope strength on both sides of a candidate R-peak.
 
    Computes the mean absolute derivative over a short window before and after
    the candidate. Returns the minimum of the two sides — a conservative
    measure that requires both upslope and downslope to be steep.
 
    A true R-peak has sustained steep slopes on both sides.
    A noise spike has slopes that collapse within one or two samples.
    '''
    half_win = max(2, int((window_ms / 1000.0) * fs))
    deriv    = np.abs(np.ediff1d(filtered_chunk, to_end=0))
 
    lo_up   = max(0,               r_idx - half_win)
    hi_up   = r_idx
    lo_down = r_idx
    hi_down = min(len(deriv),      r_idx + half_win)
 
    up_slope   = float(np.mean(deriv[lo_up:hi_up]))    if hi_up   > lo_up   else 0.0
    down_slope = float(np.mean(deriv[lo_down:hi_down])) if hi_down > lo_down else 0.0
 
    return min(up_slope, down_slope)
 
 
def _check_slope_gate(filtered_chunk: np.ndarray, r_idx: int,
                       fs: float,
                       threshold_state: AdaptiveThresholdState) -> Tuple[bool, float]:
    '''
    Check the morphological slope gate and return both the pass/fail result
    and the measured slope strength.
 
    Returning the slope value here avoids a second call to
    _measure_slope_strength() in the main detection loop — the caller can
    use it directly for record_slope_ref() without recomputing.
 
    The gate is inactive (always passes) until 3 confirmed peaks have been
    recorded, preventing false rejections during initialisation.
 
    Returns:
        (passed: bool, slope_strength: float)
    '''
    slope_threshold = threshold_state.get_slope_threshold()
    slope           = _measure_slope_strength(filtered_chunk, r_idx, fs)
    if slope_threshold == 0.0:
        return True, slope   # Gate inactive during warm-up
    return slope >= slope_threshold, slope
 
 
# --------------------------------------------------------------------------- #
#  Shared peak acceptance logic                                                #
# --------------------------------------------------------------------------- #
 
def _accept_peak(filtered_chunk: np.ndarray, integrator: np.ndarray,
                 p: int, fs: float,
                 threshold_state: AdaptiveThresholdState,
                 search_radius: int,
                 amplitude_threshold: float) -> Tuple[bool, int]:
    '''
    Attempt to accept a candidate integrator peak as a confirmed R-peak.
 
    Shared by both the T1 and searchback paths to avoid duplicating the
    snap, amplitude check, slope gate, and state-recording logic.
 
    Returns:
        (accepted: bool, r_idx: int)
        r_idx is valid only when accepted is True.
    '''
    lo = max(0, p - search_radius)
    hi = min(len(filtered_chunk), p + search_radius + 1)
    if lo >= hi:
        return False, 0
 
    local_max_idx  = np.argmax(filtered_chunk[lo:hi])
    r_idx          = lo + int(local_max_idx)
    peak_amplitude = filtered_chunk[r_idx]
 
    if peak_amplitude < amplitude_threshold:
        return False, 0
 
    passed, slope_strength = _check_slope_gate(filtered_chunk, r_idx, fs, threshold_state)
    if not passed:
        return False, 0
 
    # Record all state for this confirmed peak
    qrs_width       = _estimate_qrs_width(filtered_chunk, r_idx, fs)
    threshold_state.record_qrs_width(qrs_width)
    threshold_state.record_slope_ref(slope_strength)
 
    peak_time_ms    = (r_idx / fs) * 1000.0
    integrator_peak = integrator[r_idx] if r_idx < len(integrator) else 0.0
    threshold_state.record_peak(peak_amplitude, integrator_peak, peak_time_ms)
 
    return True, r_idx
 
 
# --------------------------------------------------------------------------- #
#  Main detection function                                                     #
# --------------------------------------------------------------------------- #
 
def detect_qrs_chunk(filtered_chunk: np.ndarray, fs: float,
                     threshold_state: AdaptiveThresholdState,
                     integrator_window_ms: int = 150,
                     refractory_ms: int = 250) -> Tuple[np.ndarray, np.ndarray]:
    '''
    Detect R-peaks using Pan-Tompkins dual-threshold adaptive method.
 
    Args:
        filtered_chunk:       Pre-filtered signal chunk from filters.py
        fs:                   Sampling frequency (Hz)
        threshold_state:      AdaptiveThresholdState carrying cross-chunk history
        integrator_window_ms: Moving window length (Pan-Tompkins default 150 ms)
        refractory_ms:        Minimum inter-peak distance — now used only as the
                              floor; actual refractory is computed adaptively
 
    Returns:
        (r_peak_indices_local, integrator_chunk)
    '''
 
    # ------------------------------------------------------------------ #
    #  1–3: Pan-Tompkins preprocessing                                    #
    # ------------------------------------------------------------------ #
    deriv      = np.ediff1d(filtered_chunk, to_end=0)
    squared    = deriv ** 2
    win_len    = max(1, int((integrator_window_ms / 1000.0) * fs))
    integrator = np.convolve(squared, np.ones(win_len) / win_len, mode='same')
 
    # ------------------------------------------------------------------ #
    #  4: Noise estimate                                                  #
    # ------------------------------------------------------------------ #
    threshold_state.update_noise_level(integrator, [])
 
    # ------------------------------------------------------------------ #
    #  5: Compute adaptive parameters for this chunk                      #
    # ------------------------------------------------------------------ #
    distance      = threshold_state.get_refractory_samples(fs)
    search_radius = threshold_state.get_snap_radius(fs)
 
    # ------------------------------------------------------------------ #
    #  6: Find candidate peaks in integrator                              #
    # ------------------------------------------------------------------ #
    peaks_t1, _ = find_peaks(
        integrator, distance=distance,
        height=max(1e-12, threshold_state.integrator_threshold1)
    )
    peaks_t2, _ = find_peaks(
        integrator, distance=int(distance * 0.5),
        height=max(1e-12, threshold_state.integrator_threshold2)
    )
 
    r_peaks       = []
    last_peak_idx = -float('inf')
 
    # ------------------------------------------------------------------ #
    #  7: Process THRESHOLD1 candidates                                   #
    # ------------------------------------------------------------------ #
    for p in peaks_t1:
        if (p - last_peak_idx) < distance:
            continue
 
        accepted, r_idx = _accept_peak(
            filtered_chunk, integrator, p, fs,
            threshold_state, search_radius,
            threshold_state.signal_threshold1
        )
        if accepted:
            r_peaks.append(r_idx)
            last_peak_idx = r_idx
 
    # ------------------------------------------------------------------ #
    #  8: Searchback — triggers only on a time gap, not candidate counts #
    # ------------------------------------------------------------------ #
    expected_rr  = threshold_state.get_expected_rr_interval()
    chunk_end    = len(filtered_chunk)
    gap_since_last = chunk_end - (last_peak_idx if last_peak_idx > -float('inf') else 0)
 
    if gap_since_last > 1.66 * expected_rr:
        for p in sorted(peaks_t2, reverse=True):
            if (p - last_peak_idx) < distance:
                continue
 
            accepted, r_idx = _accept_peak(
                filtered_chunk, integrator, p, fs,
                threshold_state, search_radius,
                threshold_state.signal_threshold2
            )
            if accepted:
                r_peaks.append(r_idx)
                last_peak_idx = r_idx
                break
 
    # ------------------------------------------------------------------ #
    #  9: Update thresholds for next chunk                                #
    # ------------------------------------------------------------------ #
    threshold_state.update_thresholds()
 
    return np.array(sorted(r_peaks), dtype=int), integrator
 