# processor.py - Central Pipeline Coordinator
 
'''
Coordinates all DSP stages per chunk for a multi-lead ECG stream.
 
Receives raw multi-lead chunks (shape: window_samples × N_leads), routes
each lead through its own filter chain, runs QRS detection on the designated
detection lead (default: Lead II), and maintains the global peak and signal
history used by metrics.py, arrhythmia.py, and display.py.
 
DETECTION LEAD
--------------
R-peak detection runs on a single designated lead — by default Lead II,
which produces the clearest upright QRS in most patients and is the
clinical standard for rhythm monitoring. The resulting R-peak indices are
shared across all leads as temporal anchors for fiducial detection.
 
If Lead II is not present in the record (e.g. a 2-lead MIT-BIH record
using MLII/V5), the processor falls back to the first available lead.
 
POSITION IN PIPELINE
--------------------
data_sources.py  →  buffer.py  →  processor.py  →  metrics.py  →  arrhythmia.py
                                        ↑ YOU ARE HERE
'''
 
import numpy as np
from collections import deque
from filters import FilterState
from buffer import StreamingBuffer
from detection import AdaptiveThresholdState, detect_qrs_chunk
 
 
# Maximum history retained for post-processing visualisation (seconds)
_HISTORY_CAP_SEC = 30
 
# Lead used for R-peak detection by default
_DETECTION_LEAD  = 'II'
 
 
def _make_filter_set(fs: float) -> dict:
    '''
    Create one complete set of filters for a single lead.
 
    Called once per lead during processor setup — each lead gets its own
    independent filter state so phase continuity is maintained per-lead
    across chunk boundaries.
    '''
    return {
        'notch':    FilterState.create_notch(fs=fs, freq=60.0),
        'highpass': FilterState.create_highpass(fs=fs, cutoff=0.5, order=2),
        'display':  FilterState.create_display(fs=fs, lowcut=0.5, highcut=40.0),
        'bandpass': FilterState.create(fs=fs, lowcut=5.0, highcut=15.0, order=2),
    }
 
 
def create_streaming_processor(fs: float,
                                lead_names: list,
                                window_duration_sec: float = 3.0,
                                overlap_duration_sec: float = 1.0,
                                detection_lead: str = _DETECTION_LEAD) -> dict:
    '''
    Create a multi-lead streaming ECG processor.
 
    One filter set is instantiated per lead at setup time. R-peak detection
    runs only on `detection_lead`; all other leads are filtered for display
    and fiducial detection but do not run independent peak detection.
 
    Args:
        fs:                   Sampling frequency in Hz.
        lead_names:           List of lead name strings from the data source.
        window_duration_sec:  Chunk size in seconds.
        overlap_duration_sec: Overlap between consecutive chunks in seconds.
        detection_lead:       Lead name to use for R-peak detection.
 
    Returns:
        Processor state dict. All mutable state lives here — nothing is
        stored as a module-level global.
    '''
    n_leads     = len(lead_names)
    history_cap = int(_HISTORY_CAP_SEC * fs)
 
    # Resolve which lead index drives detection
    if detection_lead in lead_names:
        detection_idx = lead_names.index(detection_lead)
    else:
        detection_idx = 0
        print(f'[WARN] Detection lead "{detection_lead}" not found in '
              f'{lead_names} — falling back to "{lead_names[0]}"')
 
    return {
        'buffer': StreamingBuffer(
            window_duration_sec=window_duration_sec,
            overlap_duration_sec=overlap_duration_sec,
            fs=fs,
            n_leads=n_leads,
        ),
 
        # One filter set per lead — keyed by lead name for clarity
        'filters': {
            name: _make_filter_set(fs) for name in lead_names
        },
 
        'threshold_state': AdaptiveThresholdState(),
 
        # Lead configuration
        'lead_names':     lead_names,
        'n_leads':        n_leads,
        'detection_lead': lead_names[detection_idx],
        'detection_idx':  detection_idx,
 
        # Global R-peak list (full session, used by metrics and arrhythmia)
        'all_r_peaks': [],
 
        # Bounded deque for deduplication across overlapping chunk boundaries
        'dedup_r_peaks': deque(maxlen=500),
 
        # Per-lead bounded signal histories — each deque holds the last
        # _HISTORY_CAP_SEC seconds of that lead's display-filtered signal.
        # Keyed by lead name.
        'display_history': {
            name: deque(maxlen=history_cap) for name in lead_names
        },
        'filtered_history': {
            name: deque(maxlen=history_cap) for name in lead_names
        },
 
        # Integrator history for the detection lead only (used for debug plots)
        'integrator_history': deque(maxlen=history_cap),
 
        # Lightweight per-chunk metadata for post-processing visualisation
        'processed_chunks': [],
 
        'fs': fs,
    }
 
 
def process_streaming_chunk(processor: dict, chunk: np.ndarray,
                             global_chunk_idx: int):
    '''
    Process one multi-lead chunk through the full pipeline.
 
    Args:
        processor:        State dict from create_streaming_processor.
        chunk:            Shape (window_samples, n_leads) — raw voltage data.
        global_chunk_idx: Monotonically increasing chunk counter from main.py.
 
    Updates processor state in-place.
 
    Signal path per lead
    --------------------
    raw → notch → highpass ──┬── bandpass → QRS detection (detection lead only)
                              └── display filter → display history
    '''
    fs            = processor['fs']
    lead_names    = processor['lead_names']
    detection_idx = processor['detection_idx']
    overlap       = processor['buffer'].overlap_samples
 
    window_samples   = processor['buffer'].window_samples
    start_global_idx = processor['buffer'].global_sample_idx - window_samples
 
    detection_filtered = None   # bandpass signal for the detection lead
 
    # ------------------------------------------------------------------ #
    #  Filter each lead independently                                     #
    # ------------------------------------------------------------------ #
    for i, name in enumerate(lead_names):
        raw_lead = chunk[:, i]               # (window_samples,)
        flt      = processor['filters'][name]
 
        # 1) Notch → 2) Highpass → 3a) Display path / 3b) Detection path
        notched   = flt['notch'].apply_chunk(raw_lead)
        highpassed = flt['highpass'].apply_chunk(notched)
        displayed  = flt['display'].apply_chunk(highpassed)
        bandpassed = flt['bandpass'].apply_chunk(highpassed)
 
        # Append to display history (skip overlap on all but first chunk)
        hist_d = processor['display_history'][name]
        hist_f = processor['filtered_history'][name]
 
        if len(hist_d) == 0:
            hist_d.extend(displayed.tolist())
            hist_f.extend(bandpassed.tolist())
        else:
            hist_d.extend(displayed[overlap:].tolist())
            hist_f.extend(bandpassed[overlap:].tolist())
 
        if i == detection_idx:
            detection_filtered = bandpassed
 
    # ------------------------------------------------------------------ #
    #  QRS detection on the designated detection lead only                #
    # ------------------------------------------------------------------ #
    r_peaks_local, integrator = detect_qrs_chunk(
        detection_filtered, fs, processor['threshold_state']
    )
 
    # Append integrator history (detection lead only)
    hist_i = processor['integrator_history']
    if len(hist_i) == 0:
        hist_i.extend(integrator.tolist())
    else:
        hist_i.extend(integrator[overlap:].tolist())
 
    # ------------------------------------------------------------------ #
    #  Global index conversion and deduplication                          #
    # ------------------------------------------------------------------ #
    deduped_r_peaks = []
    for idx in r_peaks_local:
        global_idx = start_global_idx + int(idx)
        is_dup     = any(abs(global_idx - existing) <= 3
                         for existing in processor['dedup_r_peaks'])
        if not is_dup:
            processor['dedup_r_peaks'].append(global_idx)
            processor['all_r_peaks'].append(global_idx)
            deduped_r_peaks.append(global_idx)
 
    # ------------------------------------------------------------------ #
    #  Lightweight chunk metadata                                          #
    # ------------------------------------------------------------------ #
    processor['processed_chunks'].append({
        'global_start_idx':      start_global_idx,
        'chunk_len':              window_samples,
        'chunk_idx':              global_chunk_idx,
        'r_peaks_global':         deduped_r_peaks,
        'signal_threshold1':      processor['threshold_state'].signal_threshold1,
        'signal_threshold2':      processor['threshold_state'].signal_threshold2,
        'integrator_threshold1':  processor['threshold_state'].integrator_threshold1,
        'integrator_threshold2':  processor['threshold_state'].integrator_threshold2,
        'noise_level':            processor['threshold_state'].noise_level,
        'signal_level':           processor['threshold_state'].signal_level,
    })
 