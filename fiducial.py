# fiducial.py - Fiducial Point Detection (Beat Level)
 
'''
Locates the P, Q, S, and T waves within an individual beat window, anchored
to a confirmed R-peak. This is the prerequisite for morphological feature
extraction — every clinical interval (PR, QRS, QT) and segment (ST) is
derived from these fiducial point locations.
 
HOW IT WORKS
------------
Given a trustworthy R-peak index (from detection.py), small search windows
are opened relative to R. Within each window, the relevant point is found by
amplitude (local minimum/maximum) rather than by searching the whole signal
blindly — physiology constrains where each wave must be.
 
Fiducial points are located on the DISPLAY-filtered signal (0.5-40 Hz, full
PQRST morphology), not the narrow bandpass signal used for QRS detection.
The detection-band signal deliberately suppresses P and T waves, so it
cannot be used to find them.
 
ADAPTIVE SEARCH WINDOWS
------------------------
Search window sizes are NOT fixed constants. A patient with a wide QRS
(BBB, certain conduction abnormalities) needs proportionally wider Q/S
search windows, or the true Q/S point gets clipped before it's found.
 
Window sizes scale with `mean_qrs_width_ms` — the same adaptive, per-patient
QRS width estimate already tracked in detection.py's AdaptiveThresholdState
(via get_mean_qrs_width_ms()). This keeps fiducial detection consistent with
the project's population-seeded, patient-adapted baseline philosophy: no
hard mode switching, no one-size-fits-all thresholds.
 
POSITION IN PIPELINE
--------------------
detection.py  →  processor.py  →  fiducial.py  →  features.py
                                        ↑ YOU ARE HERE
'''
 
import numpy as np
from typing import Optional
 
 
# Fallback seed used only before any beats have been observed (cold start).
# Matches detection.py's NORMAL_QRS_WIDTH_MS for consistency.
NORMAL_QRS_WIDTH_MS = 80.0
 
# Search window expressed as a fraction of mean QRS width, clamped to
# physiologically sane bounds so a single noisy estimate can't blow the
# window out to something absurd.
Q_WINDOW_FRACTION   = 0.5    # Q window ≈ half the QRS width, looking backward
S_WINDOW_FRACTION   = 0.75   # S window slightly wider — S trough trails further
MIN_WINDOW_MS       = 30.0
MAX_WINDOW_MS       = 120.0
 
 
def _ms_to_samples(ms: float, fs: float) -> int:
    '''Convert a millisecond duration to an integer sample count.'''
    return max(1, int((ms / 1000.0) * fs))
 
 
def _adaptive_window_ms(mean_qrs_width_ms: float, fraction: float) -> float:
    '''
    Scale a search window to this patient's own recent QRS width, clamped
    to sane physiological bounds.
    '''
    window_ms = mean_qrs_width_ms * fraction
    return float(np.clip(window_ms, MIN_WINDOW_MS, MAX_WINDOW_MS))
 
 
def find_q_point(display_signal: np.ndarray, r_idx: int, fs: float,
                  mean_qrs_width_ms: float = NORMAL_QRS_WIDTH_MS) -> Optional[int]:
    '''
    Locate the Q wave — the local minimum immediately before the R-peak.
 
    The search window scales with `mean_qrs_width_ms` (the patient's own
    recent QRS width, from AdaptiveThresholdState.get_mean_qrs_width_ms()),
    so a wide-QRS patient gets a proportionally wider search range rather
    than being clipped by a fixed window.
 
    Returns None if the search window falls outside the signal bounds
    (e.g. R-peak too close to the start of the buffer).
    '''
    search_ms = _adaptive_window_ms(mean_qrs_width_ms, Q_WINDOW_FRACTION)
    half_win  = _ms_to_samples(search_ms, fs)
 
    lo = max(0, r_idx - half_win)
    hi = r_idx  # search strictly before R
 
    if hi <= lo:
        return None
 
    window = display_signal[lo:hi]
    q_idx  = lo + int(np.argmin(window))
    return q_idx
 
 
def find_s_point(display_signal: np.ndarray, r_idx: int, fs: float,
                  mean_qrs_width_ms: float = NORMAL_QRS_WIDTH_MS) -> Optional[int]:
    '''
    Locate the S wave — the local minimum immediately after the R-peak.
 
    The search window scales with `mean_qrs_width_ms`, the same adaptive
    value used for Q. S typically trails slightly further than Q precedes,
    so S_WINDOW_FRACTION is larger than Q_WINDOW_FRACTION.
 
    Returns None if the search window falls outside the signal bounds
    (e.g. R-peak too close to the end of the buffer).
    '''
    search_ms = _adaptive_window_ms(mean_qrs_width_ms, S_WINDOW_FRACTION)
    half_win  = _ms_to_samples(search_ms, fs)
 
    lo = r_idx + 1   # search strictly after R
    hi = min(len(display_signal), r_idx + half_win)
 
    if hi <= lo:
        return None
 
    window = display_signal[lo:hi]
    s_idx  = lo + int(np.argmin(window))
    return s_idx
 
 
def find_qs_points(display_signal: np.ndarray, r_idx: int, fs: float,
                    mean_qrs_width_ms: float = NORMAL_QRS_WIDTH_MS) -> dict:
    '''
    Locate both Q and S for a single beat in one call.
 
    Args:
        mean_qrs_width_ms: This patient's recent mean QRS width in ms.
                           Pass threshold_state.get_mean_qrs_width_ms(fs)
                           from detection.py to keep the search adaptive.
 
    Returns:
        {
            'q_idx': int | None,
            's_idx': int | None,
        }
    '''
    return {
        'q_idx': find_q_point(display_signal, r_idx, fs, mean_qrs_width_ms),
        's_idx': find_s_point(display_signal, r_idx, fs, mean_qrs_width_ms),
    }
    