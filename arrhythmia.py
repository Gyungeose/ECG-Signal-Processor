# arrhythmia.py - Arrhythmia Detection
 
'''
Arrhythmia detection logic — both the raw signal analysis and the stateful
decision layer that sits on top of it.
 
TWO LAYERS
----------
1. detect_afib()     — pure function, analyses the last 8 RR intervals and
                       returns raw metrics (CV, RMSSD) and an initial detected
                       flag. Stateless: same input always gives same output.
 
2. AfibDetector      — stateful class that wraps detect_afib() and adds
                       hysteresis: an alert is only raised after 3 consecutive
                       positive detections, and cleared after 3 consecutive
                       negatives. This prevents single-beat noise from
                       triggering or clearing an alarm.
 
                       Returns a status string and confidence level ready for
                       display.py to consume directly — no AFib logic leaks
                       into main.py or display.py.
 
POSITION IN PIPELINE
--------------------
detection.py  →  processor.py  →  metrics.py  →  arrhythmia.py  →  display.py
                                                        ↑ YOU ARE HERE
'''
 
import numpy as np
from typing import Optional
 
 
# --------------------------------------------------------------------------- #
#  Raw detection (stateless)                                                   #
# --------------------------------------------------------------------------- #
 
def detect_afib(r_peaks: list, fs: float,
                cv_threshold: float    = 0.15,
                rmssd_threshold: float = 50.0,
                min_peaks: int         = 8,
                rmssd: Optional[float] = None) -> dict:
    '''
    Detect AFib using RR interval irregularity.
 
    Uses two complementary metrics so that neither alone can trigger a
    false positive:
 
      CV (coefficient of variation) — std / mean of RR intervals.
      Heart-rate normalised, so it flags irregularity regardless of whether
      the heart is fast or slow.
 
      RMSSD — root mean square of successive RR differences.
      Sensitive to beat-to-beat variability, the hallmark of AFib.
 
    Both must exceed their thresholds for a positive result.
 
    Args:
        r_peaks:        List of R-peak sample indices.
        fs:             Sampling frequency (Hz).
        cv_threshold:   CV threshold for AFib detection (default 0.15).
        rmssd_threshold:RMSSD threshold in ms (default 50.0 ms).
        min_peaks:      Minimum peaks required before detection runs.
        rmssd:          Pre-computed RMSSD in ms, or None to compute here.
                        Pass the value from compute_metrics() to avoid
                        redundant computation.
 
    Returns a dict with:
        detected:    bool
        cv:          coefficient of variation (0.0 – 1.0)
        rmssd:       ms
        confidence:  'low' | 'medium' | 'high'
    '''
    result = {'detected': False, 'cv': 0.0, 'rmssd': 0.0, 'confidence': 'low'}
 
    if len(r_peaks) < min_peaks + 1:
        return result
 
    recent_peaks = np.array(r_peaks[-(min_peaks + 1):])
    rr_ms        = np.diff(recent_peaks / fs) * 1000.0
 
    mean_rr = np.mean(rr_ms)
    if mean_rr == 0:
        return result
 
    cv = np.std(rr_ms) / mean_rr
 
    # Use the pre-computed RMSSD if supplied; compute only if not provided
    if rmssd is None:
        successive_diffs = np.diff(rr_ms)
        rmssd            = float(np.sqrt(np.mean(successive_diffs ** 2)))
 
    result['cv']    = float(cv)
    result['rmssd'] = float(rmssd)
 
    if cv > cv_threshold and rmssd > rmssd_threshold:
        result['detected'] = True
        if cv > cv_threshold * 1.5 and rmssd > rmssd_threshold * 1.5:
            result['confidence'] = 'high'
        elif cv > cv_threshold * 1.2:
            result['confidence'] = 'medium'
        else:
            result['confidence'] = 'low'
 
    return result
 
 
# --------------------------------------------------------------------------- #
#  Stateful decision layer                                                     #
# --------------------------------------------------------------------------- #
 
class AfibDetector:
    '''
    Stateful wrapper around detect_afib() that adds hysteresis.
 
    An alert is only raised after `confirm_threshold` consecutive positive
    detections, and cleared after `clear_threshold` consecutive negatives.
    This prevents a single noisy beat from triggering or clearing an alarm —
    the same principle used in clinical alarm systems.
 
    Usage:
        detector = AfibDetector()
        ...
        status, confidence = detector.update(r_peaks, fs, rmssd=metrics['rmssd'])
        # pass status and confidence directly to update_live_plot()
    '''
 
    def __init__(self, confirm_threshold: int = 3, clear_threshold: int = 3):
        '''
        Args:
            confirm_threshold: consecutive positives required to raise alert
            clear_threshold:   consecutive negatives required to clear alert
        '''
        self.confirm_threshold = confirm_threshold
        self.clear_threshold   = clear_threshold
        self._positive_streak  = 0
        self._negative_streak  = 0
        self._alert_active     = False
 
    def update(self, r_peaks: list, fs: float,
               rmssd: Optional[float] = None) -> tuple:
        '''
        Feed the latest R-peak list and get back a display-ready status.
 
        Args:
            r_peaks: List of global R-peak sample indices.
            fs:      Sampling frequency (Hz).
            rmssd:   Pre-computed RMSSD in ms from compute_metrics(), or None
                     to let detect_afib() compute it. Passing it in avoids a
                     redundant computation when main.py has already called
                     compute_metrics() this frame.
 
        Returns:
            status:     'detected' | 'possible' | 'suspected' | 'normal'
            confidence: 'high' | 'medium' | 'low'
        '''
        result = detect_afib(r_peaks, fs, rmssd=rmssd)
 
        if result['detected']:
            self._positive_streak += 1
            self._negative_streak  = 0
        else:
            self._negative_streak += 1
            self._positive_streak  = 0
 
        if self._positive_streak >= self.confirm_threshold:
            self._alert_active = True
 
        if self._negative_streak >= self.clear_threshold:
            self._alert_active = False
 
        confidence = result['confidence']
 
        if self._alert_active:
            if confidence == 'high':
                return 'detected', 'high'
            elif confidence == 'medium':
                return 'possible', 'medium'
            else:
                return 'suspected', 'low'
 
        return 'normal', confidence
 
    def reset(self):
        '''Clear all streak and alert state — call when switching records.'''
        self._positive_streak = 0
        self._negative_streak = 0
        self._alert_active    = False