# processor.py - Central Pipeline Coordinator
 
'''
Coordinates all DSP stages per chunk. Receives raw ECG samples, routes them
through the filter chain, dispatches to QRS detection, and maintains the
global peak and signal history used by metrics.py and display.py.
 
POSITION IN PIPELINE
--------------------
filters.py  →  buffer.py  →  processor.py  →  metrics.py  →  arrhythmia.py
                                  ↑ YOU ARE HERE
'''
 
import numpy as np
from collections import deque
from filters import FilterState
from buffer import StreamingBuffer
from detection import AdaptiveThresholdState, detect_qrs_chunk
 
 
# Maximum history retained for post-processing visualisation (seconds)
_HISTORY_CAP_SEC = 30
 
 
def create_streaming_processor(fs: float, window_duration_sec: float = 3.0,
                                overlap_duration_sec: float = 1.0) -> dict:
    '''
    Create a streaming ECG processor with sliding window buffer and adaptive
    thresholding.
 
    Returns a dict containing all processor components. All mutable state
    lives in this dict — nothing is stored as a module-level global.
    '''
    history_cap = int(_HISTORY_CAP_SEC * fs)
 
    return {
        'buffer': StreamingBuffer(
            window_duration_sec=window_duration_sec,
            overlap_duration_sec=overlap_duration_sec,
            fs=fs
        ),
        # Two-stage filtering: High-pass (0.5 Hz) + Bandpass (5–15 Hz)
        'notch_filter':    FilterState.create_notch(fs=fs, freq=60.0),
        'highpass_filter': FilterState.create_highpass(fs=fs, cutoff=0.5, order=2),
        'display_filter':  FilterState.create_display(fs=fs, lowcut=0.5, highcut=40.0),
        'bandpass_filter': FilterState.create(fs=fs, lowcut=5.0, highcut=15.0, order=2),
        'threshold_state': AdaptiveThresholdState(),
 
        # Global R-peak list (full session, used by metrics and arrhythmia)
        'all_r_peaks': [],
 
        # Bounded deque for deduplication — only recent peaks can produce
        # cross-chunk duplicates; no need to scan the full session history
        'dedup_r_peaks': deque(maxlen=500),
 
        # Bounded signal histories — capped at _HISTORY_CAP_SEC of samples.
        # The post-processing plot uses only the last 5 s; storing more is waste.
        'filtered_history':   deque(maxlen=history_cap),
        'display_history':    deque(maxlen=history_cap),
        'integrator_history': deque(maxlen=history_cap),
 
        # Lightweight chunk metadata for post-processing visualisation.
        # Full signal arrays are NOT stored here — they live in the history deques.
        'processed_chunks': [],
 
        'fs': fs,
    }
 
 
def process_streaming_chunk(processor: dict, chunk: np.ndarray,
                             global_chunk_idx: int):
    '''
    Process a single chunk of ECG data through the streaming pipeline.
    Updates processor state in-place.
 
    Signal path
    -----------
    raw → notch → highpass ──┬── bandpass → QRS detection
                              └── display filter → display history
    '''
    fs = processor['fs']
 
    # ------------------------------------------------------------------ #
    #  1) Powerline interference removal                                  #
    # ------------------------------------------------------------------ #
    chunk_notched = processor['notch_filter'].apply_chunk(chunk)
 
    # ------------------------------------------------------------------ #
    #  2) Baseline wander removal (0.5 Hz high-pass)                     #
    #     This also removes DC offset — no explicit chunk_mean subtraction
    #     is needed.                                                      #
    # ------------------------------------------------------------------ #
    highpass_filtered = processor['highpass_filter'].apply_chunk(chunk_notched)
 
    # ------------------------------------------------------------------ #
    #  3) Display path — wide-band filter preserves full PQRST morphology #
    # ------------------------------------------------------------------ #
    display_filtered = processor['display_filter'].apply_chunk(highpass_filtered)
 
    # ------------------------------------------------------------------ #
    #  4) Detection path — narrow bandpass isolates QRS energy            #
    # ------------------------------------------------------------------ #
    filtered = processor['bandpass_filter'].apply_chunk(highpass_filtered)
 
    # ------------------------------------------------------------------ #
    #  5) QRS detection                                                   #
    # ------------------------------------------------------------------ #
    window_samples   = processor['buffer'].window_samples
    start_global_idx = processor['buffer'].global_sample_idx - window_samples
 
    r_peaks_local, integrator = detect_qrs_chunk(
        filtered, fs, processor['threshold_state']
    )
 
    # ------------------------------------------------------------------ #
    #  6) Global index conversion and deduplication                       #
    #     dedup_r_peaks is a bounded deque (maxlen=500) — O(1) append,   #
    #     and the linear scan stays short regardless of session length.   #
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
    #  7) Append to bounded signal histories                              #
    #     Overlap samples are skipped on all chunks after the first to   #
    #     avoid double-counting the overlap region.                       #
    # ------------------------------------------------------------------ #
    overlap_samples = processor['buffer'].overlap_samples
    if len(processor['filtered_history']) == 0:
        processor['filtered_history'].extend(filtered.tolist())
        processor['display_history'].extend(display_filtered.tolist())
        processor['integrator_history'].extend(integrator.tolist())
    else:
        processor['filtered_history'].extend(filtered[overlap_samples:].tolist())
        processor['display_history'].extend(display_filtered[overlap_samples:].tolist())
        processor['integrator_history'].extend(integrator[overlap_samples:].tolist())
 
    # ------------------------------------------------------------------ #
    #  8) Store lightweight chunk metadata (no signal arrays)             #
    # ------------------------------------------------------------------ #
    processor['processed_chunks'].append({
        'global_start_idx':      start_global_idx,
        'chunk_len':              len(filtered),
        'chunk_idx':              global_chunk_idx,
        'r_peaks_global':         deduped_r_peaks,
        'signal_threshold1':      processor['threshold_state'].signal_threshold1,
        'signal_threshold2':      processor['threshold_state'].signal_threshold2,
        'integrator_threshold1':  processor['threshold_state'].integrator_threshold1,
        'integrator_threshold2':  processor['threshold_state'].integrator_threshold2,
        'noise_level':            processor['threshold_state'].noise_level,
        'signal_level':           processor['threshold_state'].signal_level,
    })