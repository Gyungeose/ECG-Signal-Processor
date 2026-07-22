# fiducial.py - Fiducial Point Detection (Beat Level)
 
'''
Locates the P, Q, S, and T waves within an individual beat window, anchored
to a confirmed R-peak. This is the prerequisite for morphological feature
extraction — every clinical interval (PR, QRS, QT) and segment (ST) is
derived from these fiducial point locations.
 
HOW IT WORKS
------------
Given a trustworthy R-peak index (from detection.py), physiologically-
bounded search windows are opened relative to R. Within each window, the
relevant point is found by amplitude (local minimum or maximum) rather than
searching the whole signal blindly — physiology constrains where each wave
must be.
 
Fiducial points are located on the DISPLAY-filtered signal (0.5-40 Hz, full
PQRST morphology), not the narrow bandpass signal used for QRS detection.
The detection-band signal deliberately suppresses P and T waves, so it
cannot be used to find them.
 
ADAPTIVE SEARCH WINDOWS
------------------------
Search window sizes scale with the patient's own observed QRS width
(from AdaptiveThresholdState.get_mean_qrs_width_ms()) and mean RR interval
(from AdaptiveThresholdState.get_expected_rr_interval()). This keeps
fiducial detection consistent with the project's population-seeded,
patient-adapted baseline philosophy — no hard mode switching, no one-size-
fits-all thresholds.
 
POLARITY HANDLING
-----------------
T wave polarity is lead-dependent. aVR normally has an inverted (negative)
T wave; all other standard leads are treated as positive. The correct
search function (argmax vs argmin) is selected automatically from lead_id.
 
POSITION IN PIPELINE
--------------------
detection.py  →  processor.py  →  fiducial.py  →  features.py
                                        ↑ YOU ARE HERE
'''
 
import numpy as np
from typing import Optional
 
 
# --------------------------------------------------------------------------- #
#  Constants                                                                    #
# --------------------------------------------------------------------------- #
 
# Fallback QRS width seed — matches detection.py's NORMAL_QRS_WIDTH_MS
NORMAL_QRS_WIDTH_MS = 80.0
 
# Q/S search window as a fraction of mean QRS width
Q_WINDOW_FRACTION = 0.5    # Q looks backward ~half the QRS width
S_WINDOW_FRACTION = 0.75   # S looks forward ~three-quarters (trails further)
MIN_QS_WINDOW_MS  = 30.0
MAX_QS_WINDOW_MS  = 120.0
 
# T wave search: fixed lower bound + RR-adaptive upper bound
T_SEARCH_START_MS = 100.0  # clear QRS + ST segment before searching
T_SEARCH_MAX_MS   = 400.0  # physiological maximum T wave offset from R
T_RR_FRACTION     = 0.70   # don't search past 70% of mean RR (avoids next beat)
 
# Leads with normally inverted (negative) T waves
_INVERTED_T_LEADS = {'aVR'}
 
 
# --------------------------------------------------------------------------- #
#  Utilities                                                                    #
# --------------------------------------------------------------------------- #
 
def _ms_to_samples(ms: float, fs: float) -> int:
    return max(1, int((ms / 1000.0) * fs))
 
 
def _adaptive_qs_window_ms(mean_qrs_width_ms: float, fraction: float) -> float:
    '''Scale a Q/S search window to this patient's QRS width.'''
    return float(np.clip(
        mean_qrs_width_ms * fraction,
        MIN_QS_WINDOW_MS,
        MAX_QS_WINDOW_MS
    ))
 
 
def _t_search_end_ms(mean_rr_ms: float) -> float:
    '''
    Compute the upper bound of the T wave search window.
 
    The tighter of two constraints:
      - physiological maximum (T_SEARCH_MAX_MS)
      - 70% of mean RR interval (prevents wandering into the next beat
        at fast heart rates where beats are closer together)
    '''
    rr_bound = mean_rr_ms * T_RR_FRACTION
    return float(min(T_SEARCH_MAX_MS, rr_bound))
 
 
# --------------------------------------------------------------------------- #
#  Q wave                                                                       #
# --------------------------------------------------------------------------- #
 
def find_q_point(display_signal: np.ndarray, r_idx: int, fs: float,
                  mean_qrs_width_ms: float = NORMAL_QRS_WIDTH_MS) -> Optional[int]:
    '''
    Locate the Q wave — the local minimum immediately before the R-peak.
 
    Search window scales with `mean_qrs_width_ms` so wide-QRS beats
    (PVCs, BBB) get a proportionally wider search range.
 
    Returns None if the search window falls outside signal bounds.
    '''
    search_ms = _adaptive_qs_window_ms(mean_qrs_width_ms, Q_WINDOW_FRACTION)
    half_win  = _ms_to_samples(search_ms, fs)
 
    lo = max(0, r_idx - half_win)
    hi = r_idx  # strictly before R
 
    if hi <= lo:
        return None
 
    return lo + int(np.argmin(display_signal[lo:hi]))
 
 
# --------------------------------------------------------------------------- #
#  S wave                                                                       #
# --------------------------------------------------------------------------- #
 
def find_s_point(display_signal: np.ndarray, r_idx: int, fs: float,
                  mean_qrs_width_ms: float = NORMAL_QRS_WIDTH_MS) -> Optional[int]:
    '''
    Locate the S wave — the local minimum immediately after the R-peak.
 
    S_WINDOW_FRACTION is slightly wider than Q_WINDOW_FRACTION because the
    S trough typically trails further from R than Q precedes it.
 
    Returns None if the search window falls outside signal bounds.
    '''
    search_ms = _adaptive_qs_window_ms(mean_qrs_width_ms, S_WINDOW_FRACTION)
    half_win  = _ms_to_samples(search_ms, fs)
 
    lo = r_idx + 1  # strictly after R
    hi = min(len(display_signal), r_idx + half_win)
 
    if hi <= lo:
        return None
 
    return lo + int(np.argmin(display_signal[lo:hi]))
 
 
# --------------------------------------------------------------------------- #
#  T wave                                                                       #
# --------------------------------------------------------------------------- #
 
def find_t_wave(display_signal: np.ndarray, r_idx: int, fs: float,
                mean_rr_ms: float,
                mean_qrs_width_ms: float = NORMAL_QRS_WIDTH_MS,
                lead_id: str = 'II') -> Optional[int]:
    '''
    Locate the T wave peak after the R-peak.
 
    Search window:
        lower bound — R + T_SEARCH_START_MS (clears QRS and ST segment)
        upper bound — R + min(T_SEARCH_MAX_MS, mean_rr_ms * T_RR_FRACTION)
 
    The upper bound is RR-adaptive so the search never wanders into the
    next beat at fast heart rates. At 150 bpm (RR ≈ 400ms), the upper
    bound becomes 70% × 400ms = 280ms, well before the next P wave.
 
    Polarity:
        aVR           → argmin (normally inverted T wave)
        all other leads → argmax (normally upright T wave)
 
    Args:
        display_signal:    Display-filtered signal (0.5-40 Hz).
        r_idx:             Confirmed R-peak sample index.
        fs:                Sampling frequency (Hz).
        mean_rr_ms:        Patient's mean RR interval in ms.
                           Pass threshold_state.get_expected_rr_interval().
        mean_qrs_width_ms: Patient's mean QRS width in ms (used only for
                           context; T window uses RR, not QRS width).
        lead_id:           Lead name — determines T wave polarity assumption.
 
    Returns:
        Sample index of the T wave peak, or None if the window falls
        outside signal bounds or contains only NaN.
    '''
    lo = r_idx + _ms_to_samples(T_SEARCH_START_MS, fs)
    hi = r_idx + _ms_to_samples(_t_search_end_ms(mean_rr_ms), fs)
    hi = min(hi, len(display_signal))
 
    if hi <= lo:
        return None
 
    window = display_signal[lo:hi]
 
    # Guard against all-NaN windows (e.g. during void gap)
    if np.all(np.isnan(window)):
        return None
 
    if lead_id in _INVERTED_T_LEADS:
        # Inverted T — find the most negative point
        local_idx = int(np.nanargmin(window))
    else:
        # Upright T — find the most positive point
        local_idx = int(np.nanargmax(window))
 
    return lo + local_idx
 
 
# --------------------------------------------------------------------------- #
#  Combined per-beat call                                                       #
# --------------------------------------------------------------------------- #
 
def find_qst_points(display_signal: np.ndarray, r_idx: int, fs: float,
                     mean_rr_ms: float,
                     mean_qrs_width_ms: float = NORMAL_QRS_WIDTH_MS,
                     lead_id: str = 'II') -> dict:
    '''
    Locate Q, S, and T for a single beat in one call.
 
    Args:
        display_signal:    Display-filtered signal (0.5-40 Hz).
        r_idx:             Confirmed R-peak sample index.
        fs:                Sampling frequency (Hz).
        mean_rr_ms:        Patient's mean RR interval in ms.
        mean_qrs_width_ms: Patient's mean QRS width in ms.
        lead_id:           Lead name — affects T wave polarity.
 
    Returns:
        {
            'q_idx': int | None,
            's_idx': int | None,
            't_idx': int | None,
        }
    '''
    return {
        'q_idx': find_q_point(display_signal, r_idx, fs, mean_qrs_width_ms),
        's_idx': find_s_point(display_signal, r_idx, fs, mean_qrs_width_ms),
        't_idx': find_t_wave(display_signal, r_idx, fs, mean_rr_ms,
                              mean_qrs_width_ms, lead_id),
    }
 