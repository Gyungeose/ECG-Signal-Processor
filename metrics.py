# metrics.py - Clinical Metric Computation
 
'''
Computes clinical metrics from detected R-peak indices.
 
All functions are pure — same input always gives same output, no side
effects, no state. This makes them easy to test and safe to call from
anywhere in the pipeline.
 
METRICS PROVIDED
----------------
HR      Heart rate in bpm, derived from the mean of the last 8 RR intervals.
        Rate-limiting to 8 intervals keeps the display responsive to changes
        without being jittery on a single outlier interval.
 
RMSSD   Root mean square of successive RR differences (ms).
        The standard HRV metric for beat-to-beat variability. Elevated in
        AFib; depressed in states of low autonomic activity.
 
POSITION IN PIPELINE
--------------------
detection.py  →  processor.py  →  metrics.py  →  arrhythmia.py  →  display.py
                                       ↑ YOU ARE HERE
'''
 
import numpy as np
 
 
def compute_hr(r_peak_indices, fs: float):
    '''
    Compute heart rate in bpm from the last 8 RR intervals.
 
    Returns None if fewer than 2 peaks are available.
    '''
    if len(r_peak_indices) < 2:
        return None
    recent = np.array(r_peak_indices[-9:])   # last 9 peaks = last 8 intervals
    rr_ms  = np.diff(recent / fs) * 1000.0
    avg_rr = float(np.mean(rr_ms))
    if avg_rr <= 0:
        return None
    return int(round(60000.0 / avg_rr))
 
 
def compute_rmssd(r_peak_indices, fs: float) -> float:
    '''
    Compute RMSSD (ms) from R-peak indices.
 
    RMSSD is the root mean square of successive differences of RR intervals.
    Requires at least 3 peaks (2 intervals → 1 successive difference).
 
    Returns NaN if insufficient data.
    '''
    if len(r_peak_indices) < 3:
        return float('nan')
    times_ms        = (np.array(r_peak_indices) / float(fs)) * 1000.0
    rr_ms           = np.diff(times_ms)
    successive_diffs= np.diff(rr_ms)
    return float(np.sqrt(np.mean(successive_diffs ** 2)))
 
 
def compute_metrics(r_peak_indices, fs: float) -> dict:
    '''
    Compute all real-time clinical metrics in a single call.
 
    This is the primary entry point for main.py — call this once per
    display frame and pass the results to display.py.
 
    Returns:
        hr:    int | None   — heart rate in bpm
        rmssd: float | None — RMSSD in ms, or None if insufficient data
    '''
    peaks = list(r_peak_indices)
    hr    = compute_hr(peaks, fs)
    rmssd = compute_rmssd(peaks, fs)
    return {
        'hr':    hr,
        'rmssd': rmssd if not np.isnan(rmssd) else None,
    }
 