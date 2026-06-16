# Module 

import numpy as np
from filters import FilterState
from buffer import StreamingBuffer
from detection import AdaptiveThresholdState, detect_qrs_chunk

def create_streaming_processor(fs: float, window_duration_sec: float = 3.0,
                              overlap_duration_sec: float = 1.0):
    """
    Create a streaming ECG processor with sliding window buffer and adaptive thresholding.
    
    Returns:
        Dictionary containing all processor components
    """
    return {
        'buffer': StreamingBuffer(
            window_duration_sec=window_duration_sec,
            overlap_duration_sec=overlap_duration_sec,
            fs=fs
        ),
        # Two-stage filtering: High-pass (0.5 Hz) + Bandpass (5-15 Hz)
        'notch_filter': FilterState.create_notch(fs=fs, freq=60.0),
        'highpass_filter': FilterState.create_highpass(fs=fs, cutoff=0.5, order=2),
        'display_filter': FilterState.create_display(fs=fs, lowcut=0.5, highcut=40.0),
        'bandpass_filter': FilterState.create(fs=fs, lowcut=5.0, highcut=15.0, order=2),
        'threshold_state': AdaptiveThresholdState(),
        'all_r_peaks': [],  # Global list of unique detected R-peaks (with global indices)
        'dedup_r_peaks': [],  # Used to suppress duplicate overlapping detections
        'filtered_history': [],  # Continuous stream of filtered ECG values
        'display_history': [],  # Continuous stream of display-band ECG values
        'integrator_history': [],  # Continuous stream of integrator values
        'processed_chunks': [],  # Store processed chunks for visualization
        'fs': fs
    }


def process_streaming_chunk(processor: dict, chunk: np.ndarray, global_chunk_idx: int):
    """
    Process a single chunk of ECG data through the streaming pipeline.
    Updates processor state in-place.
    """
    fs = processor['fs']
    
    # 0) DC offset removal - center signal at 0.0 mV
    chunk_mean = np.mean(chunk)
    chunk_centered = chunk - chunk_mean
    
    # 1) Remove powerline interference with a notch filter before further filtering
    chunk_notched = processor['notch_filter'].apply_chunk(chunk_centered)
    
    # 2) Apply high-pass filter (0.5 Hz) to remove baseline wander
    highpass_filtered = processor['highpass_filter'].apply_chunk(chunk_notched)
    
    # Display path — wide-band filter preserves full PQRST morphology
    display_filtered = processor['display_filter'].apply_chunk(highpass_filtered)
    
    # 3) Apply bandpass filter (5-15 Hz) for QRS complex isolation
    filtered = processor['bandpass_filter'].apply_chunk(highpass_filtered)
    
    # 2) Detect R-peaks using adaptive dual-threshold method
    window_samples = processor['buffer'].window_samples
    start_global_idx = (processor['buffer'].global_sample_idx - window_samples)

    print(f"chunk={global_chunk_idx} | start={start_global_idx} | window={window_samples} | chunk_len={len(filtered)}")

    r_peaks_local, integrator = detect_qrs_chunk(
        filtered, fs, processor['threshold_state']
    )
    
    # 3) Convert local indices to global indices and deduplicate overlapping detections
    deduped_r_peaks = []
    for idx in r_peaks_local:
        global_idx = start_global_idx + int(idx)
        is_dup = any(abs(global_idx - existing) <= 3 for existing in processor['dedup_r_peaks'])
        print(f"Peak local={idx}, global={global_idx}, duplicate={is_dup}")

        if not any(abs(global_idx - existing) <= 3 for existing in processor['dedup_r_peaks']):
            processor['dedup_r_peaks'].append(global_idx)
            processor['all_r_peaks'].append(global_idx)
            deduped_r_peaks.append(global_idx)

    # 4) Maintain a continuous history of filtered signal and integrator values
    overlap_samples = processor['buffer'].overlap_samples
    if len(processor['filtered_history']) == 0:
        processor['filtered_history'].extend(filtered.tolist())
        processor['display_history'].extend(display_filtered.tolist())
        processor['integrator_history'].extend(integrator.tolist())
    else:
        processor['filtered_history'].extend(filtered[overlap_samples:].tolist())
        processor['display_history'].extend(display_filtered[overlap_samples:].tolist())
        processor['integrator_history'].extend(integrator[overlap_samples:].tolist())

    # Store for visualization (store all processing stages)
    processor['processed_chunks'].append({
        'raw': chunk.copy(),           # Original chunk
        'centered': chunk_centered.copy(),  # After DC removal
        'highpass': highpass_filtered.copy(),  # After high-pass filter
        'filtered': filtered.copy(),   # After bandpass filter (final)
        'integrator': integrator.copy(),
        'r_peaks_local': r_peaks_local,
        'r_peaks_global': deduped_r_peaks,
        'global_start_idx': start_global_idx,
        'chunk_idx': global_chunk_idx,
        'dc_offset': chunk_mean,       # Store DC offset for reference
        'signal_threshold1': processor['threshold_state'].signal_threshold1,
        'signal_threshold2': processor['threshold_state'].signal_threshold2,
        'integrator_threshold1': processor['threshold_state'].integrator_threshold1,
        'integrator_threshold2': processor['threshold_state'].integrator_threshold2,
        'noise_level': processor['threshold_state'].noise_level,
        'signal_level': processor['threshold_state'].signal_level
    })