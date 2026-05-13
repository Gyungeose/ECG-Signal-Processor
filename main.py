import wfdb
import os
import time
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import butter, sosfilt, find_peaks
from collections import deque
from dataclasses import dataclass, field
from typing import Tuple, List, Optional

app = QtWidgets.QApplication([])

# Connect to the PhysioNet MIT-BIH database

def load_cardiology_data():
    print("Connecting to PhysioNet MIT-BIH Database...")
    
    # Download record '100' (a pre-recorded ECG sample) with 1500 samples (~4 seconds at 360Hz)
    record = wfdb.rdrecord('100', pn_dir='mitdb', sampto=1500)
    
    v_signal = record.p_signal[:, 0] / 200.0 # Extract the voltage signal from Lead II (standard cardiac rhythm strip)
    fs = record.fs # Get the sampling frequency (360 Hz = 360 measurements per second)

    # Converts sample indices to actual time in seconds using: Time = Sample Index / Sampling Frequency
    time = np.arange(len(v_signal)) / fs
    
    return time, v_signal, record.record_name


@dataclass
class StreamingBuffer:
    """Sliding window buffer for streaming ECG data processing."""
    window_duration_sec: float
    overlap_duration_sec: float
    fs: float
    global_sample_idx: int = 0
    
    def __post_init__(self):
        """Initialize buffer dimensions."""
        self.window_samples = int(self.window_duration_sec * self.fs)
        self.overlap_samples = int(self.overlap_duration_sec * self.fs)
        self.stride_samples = self.window_samples - self.overlap_samples
        self.buffer = deque(maxlen=self.window_samples)
    
    def add_sample(self, value: float) -> Optional[np.ndarray]:
        """
        Add a single sample to the buffer.
        Returns a complete window chunk if ready, None otherwise.
        """
        self.buffer.append(value)
        self.global_sample_idx += 1
        
        if len(self.buffer) == self.window_samples:
            chunk = np.array(list(self.buffer), dtype=float)
            # Advance by stride (remove overlap for next chunk)
            for _ in range(self.stride_samples):
                self.buffer.popleft()
            return chunk
        return None
    
    def add_samples(self, samples: np.ndarray) -> List[np.ndarray]:
        """
        Add multiple samples and return all complete chunks.
        """
        chunks = []
        for sample in samples:
            chunk = self.add_sample(sample)
            if chunk is not None:
                chunks.append(chunk)
        return chunks
    
    def get_current_buffer(self) -> np.ndarray:
        """Get the current buffer contents (for incomplete windows)."""
        return np.array(list(self.buffer), dtype=float)
    
    def current_time_range(self) -> Tuple[float, float]:
        """Get time range (start, end) in seconds for current buffer."""
        start_idx = self.global_sample_idx - len(self.buffer)
        end_idx = self.global_sample_idx
        return start_idx / self.fs, end_idx / self.fs


@dataclass
class FilterState:
    """Stateful Butterworth filter using second-order sections (SOS)."""
    sos: np.ndarray
    zi: np.ndarray
    
    @classmethod
    def create(cls, fs: float, lowcut: float = 5.0, highcut: float = 15.0, order: int = 2):
        """Create a bandpass filter for QRS complex isolation."""
        nyq = 0.5 * fs
        low = lowcut / nyq
        high = highcut / nyq
        sos = butter(order, [low, high], btype='band', output='sos')
        # Initialize state for each second-order section
        zi = np.zeros((sos.shape[0], 2))
        return cls(sos=sos, zi=zi)
    
    @classmethod
    def create_highpass(cls, fs: float, cutoff: float = 0.5, order: int = 2):
        """Create a high-pass filter for baseline wander removal."""
        nyq = 0.5 * fs
        normal_cutoff = cutoff / nyq
        sos = butter(order, normal_cutoff, btype='high', output='sos')
        # Initialize state for each second-order section
        zi = np.zeros((sos.shape[0], 2))
        return cls(sos=sos, zi=zi)
    
    @classmethod
    def create_display(cls, fs: float, lowcut: float = 0.5, highcut: float = 40.0, order: int = 2):
        """Wide-band filter for display — preserves full PQRST morphology."""
        nyq = 0.5 * fs
        sos = butter(order, [lowcut / nyq, highcut / nyq], btype='band', output='sos')
        zi = np.zeros((sos.shape[0], 2))
        return cls(sos=sos, zi=zi)
    
    @classmethod
    def create_notch(cls, fs: float, freq: float = 60.0, quality: float = 30.0):
        """Notch filter to remove powerline interference (60 Hz US, 50 Hz international)."""
        from scipy.signal import iirnotch
        b, a = iirnotch(freq, quality, fs)
        sos = np.array([[b[0], b[1], b[2], 1.0, a[1], a[2]]])
        zi = np.zeros((sos.shape[0], 2))
        return cls(sos=sos, zi=zi)
        
    def apply_chunk(self, chunk: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Apply filter to a chunk while preserving state.
        
        Returns:
            (filtered_chunk, integrator_chunk)
        """
        filtered, self.zi = sosfilt(self.sos, chunk, zi=self.zi)
        return filtered
    
    def reset_state(self):
        """Reset filter state (useful for discontinuities in signal)."""
        self.zi = np.zeros((self.sos.shape[0], 2))


@dataclass
class AdaptiveThresholdState:
    """Maintains adaptive threshold state for Pan-Tompkins dual-threshold method."""
    # Peak history (last 8 detected R-peaks)
    peak_values: deque = field(default_factory=lambda: deque(maxlen=8))
    peak_times: deque = field(default_factory=lambda: deque(maxlen=8))
    integrator_peaks: deque = field(default_factory=lambda: deque(maxlen=8))
    
    # Noise and signal estimates
    noise_level: float = 0.0
    signal_level: float = 0.0
    
    # Threshold values
    signal_threshold1: float = 0.0
    signal_threshold2: float = 0.0
    integrator_threshold1: float = 0.0
    integrator_threshold2: float = 0.0
    
    def update_noise_level(self, chunk: np.ndarray, detected_peaks: List[int]):
        """
        Estimate noise level from signal regions between peaks.
        Assumes noise is in intervals where no peaks are detected.
        """
        if len(detected_peaks) == 0:
            # No peaks in this chunk - estimate noise from entire signal
            self.noise_level = 0.5 * np.std(chunk)
        else:
            # Find noise between detected peaks
            noise_samples = []
            for i in range(len(chunk)):
                # Check if this sample is far from any peak
                if not any(abs(i - p) < 50 for p in detected_peaks):  # 50 samples = ~140ms
                    noise_samples.append(chunk[i])
            
            if noise_samples:
                self.noise_level = 0.5 * np.std(noise_samples)
            else:
                # Fallback: use overall standard deviation
                self.noise_level = 0.5 * np.std(chunk)
    
    def update_signal_level(self, peak_amplitude: float):
        """Update signal level based on detected peak."""
        if len(self.peak_values) == 0:
            self.signal_level = peak_amplitude
        else:
            # Weighted average (more recent peaks have higher weight)
            weights = np.linspace(0.5, 1.0, len(self.peak_values) + 1)
            all_peaks = list(self.peak_values) + [peak_amplitude]
            self.signal_level = np.average(all_peaks, weights=weights)
    
    def update_thresholds(self):
        """
        Update thresholds using Pan-Tompkins dual-threshold method.
        
        Thresholds are based on:
        - Signal level: weighted average of last 8 peaks
        - Noise level: estimated from inter-peak regions
        """
        if len(self.peak_values) == 0:
            # Initialize with conservative thresholds
            self.signal_threshold1 = 0.5 * self.signal_level
            self.signal_threshold2 = 0.25 * self.signal_level
            self.integrator_threshold1 = 0.5 * np.mean(list(self.integrator_peaks)) if len(self.integrator_peaks) > 0 else 0.0
            self.integrator_threshold2 = 0.25 * np.mean(list(self.integrator_peaks)) if len(self.integrator_peaks) > 0 else 0.0
        else:
            # Pan-Tompkins dual-threshold approach
            # Threshold1: For initial detection (higher threshold)
            # Threshold2: For searching between peaks when no peak found (lower threshold)
            
            # Signal thresholds
            self.signal_threshold1 = self.noise_level + 0.25 * (self.signal_level - self.noise_level)
            self.signal_threshold2 = 0.5 * self.signal_threshold1
            
            # Integrator thresholds (based on last integrator peaks)
            if len(self.integrator_peaks) > 0:
                mean_integrator_peak = np.mean(list(self.integrator_peaks))
                self.integrator_threshold1 = self.noise_level + 0.6 * mean_integrator_peak
                self.integrator_threshold2 = 0.5 * self.integrator_threshold1
            else:
                self.integrator_threshold1 = 0.0
                self.integrator_threshold2 = 0.0
    
    def record_peak(self, peak_amplitude: float, integrator_peak: float, time_ms: float):
        """Record a detected peak for history."""
        self.peak_values.append(peak_amplitude)
        self.integrator_peaks.append(integrator_peak)
        self.peak_times.append(time_ms)
        self.update_signal_level(peak_amplitude)
    
    def get_expected_rr_interval(self) -> float:
        """
        Get expected RR interval based on last 8 detected peaks.
        Returns interval in samples.
        """
        if len(self.peak_times) < 2:
            return 360  # Default 1-second interval @ 360 Hz
        
        # Average RR interval from history
        rr_intervals = np.diff(list(self.peak_times))
        return np.mean(rr_intervals)
    
    def reset(self):
        """Reset all tracking state."""
        self.peak_values.clear()
        self.peak_times.clear()
        self.integrator_peaks.clear()
        self.noise_level = 0.0
        self.signal_level = 0.0
        self.signal_threshold1 = 0.0
        self.signal_threshold2 = 0.0
        self.integrator_threshold1 = 0.0
        self.integrator_threshold2 = 0.0



def detect_qrs_chunk(filtered_chunk: np.ndarray, fs: float, 
                     threshold_state: AdaptiveThresholdState,
                     integrator_window_ms: int = 150, 
                     refractory_ms: int = 250) -> Tuple[np.ndarray, np.ndarray]:
    """
    Detect R-peaks using Pan-Tompkins dual-threshold adaptive method.
    
    Implements the original Pan-Tompkins algorithm with adaptive dual thresholds:
    - THRESHOLD1: Main detection threshold (higher, fewer false positives)
    - THRESHOLD2: Searchback threshold (lower, used when no peak found in expected window)
    
    Args:
        filtered_chunk: Pre-filtered signal chunk
        fs: Sampling frequency
        threshold_state: AdaptiveThresholdState object tracking history and thresholds
        integrator_window_ms: Moving window length in ms (Pan-Tompkins default: 150ms)
        refractory_ms: Minimum time between peaks (Pan-Tompkins default: 250ms)
    
    Returns:
        (r_peak_indices_local, integrator_chunk)
    """
    # 1) Derivative (emphasize slope)
    deriv = np.ediff1d(filtered_chunk, to_end=0)
    
    # 2) Square to make all values positive and emphasize large slopes
    squared = deriv ** 2
    
    # 3) Moving-window integrator (heart of Pan-Tompkins)
    win_len = max(1, int((integrator_window_ms / 1000.0) * fs))
    integrator = np.convolve(squared, np.ones(win_len) / win_len, mode='same')
    
    # 4) Update noise level from this chunk's signal and integrator
    threshold_state.update_noise_level(integrator, [])
    
    # 5) Peak detection using dual thresholds
    distance = max(1, int((refractory_ms / 1000.0) * fs))
    search_radius = max(1, int(0.05 * fs))  # ±50 ms for local refinement
    
    # Find peaks in integrator exceeding THRESHOLD1
    peaks_t1, _ = find_peaks(integrator, distance=distance, 
                             height=max(1e-12, threshold_state.integrator_threshold1))
    
    # Find peaks in integrator exceeding THRESHOLD2 (for searchback)
    peaks_t2, _ = find_peaks(integrator, distance=int(distance * 0.5),
                             height=max(1e-12, threshold_state.integrator_threshold2))
    
    r_peaks = []
    last_peak_idx = -float('inf')
    
    # 6) Process peaks in order
    for p in peaks_t1:
        # Check refractory period
        if (p - last_peak_idx) < distance:
            continue
        
        # Refine peak location: find maximum in filtered signal nearby
        lo = max(0, p - search_radius)
        hi = min(len(filtered_chunk), p + search_radius + 1)
        
        if lo < hi:
            local_max_idx = np.argmax(filtered_chunk[lo:hi])
            r_idx = lo + int(local_max_idx)
            peak_amplitude = filtered_chunk[r_idx]
            
            # Check against signal THRESHOLD1
            if peak_amplitude >= threshold_state.signal_threshold1:
                r_peaks.append(r_idx)
                last_peak_idx = r_idx
                
                # Record peak for history and threshold updates
                peak_time_ms = (r_idx / fs) * 1000.0
                integrator_peak = integrator[r_idx] if r_idx < len(integrator) else 0
                threshold_state.record_peak(peak_amplitude, integrator_peak, peak_time_ms)
    
    # 7) Searchback: If no peak found in expected interval, use THRESHOLD2
    if len(r_peaks) == 0 or (len(peaks_t2) > 0 and len(r_peaks) < len(peaks_t1) * 0.5):
        # Look for peaks that exceeded THRESHOLD2 but not THRESHOLD1
        expected_rr = threshold_state.get_expected_rr_interval()
        search_window = int(1.5 * expected_rr)  # Search 1.5 × expected RR interval back
        
        for p in sorted(peaks_t2, reverse=True):
            if p < last_peak_idx + search_window:
                # Skip if too close to last detected peak
                if (p - last_peak_idx) < distance:
                    continue
                
                # Refine location
                lo = max(0, p - search_radius)
                hi = min(len(filtered_chunk), p + search_radius + 1)
                
                if lo < hi:
                    local_max_idx = np.argmax(filtered_chunk[lo:hi])
                    r_idx = lo + int(local_max_idx)
                    peak_amplitude = filtered_chunk[r_idx]
                    
                    # Check against signal THRESHOLD2
                    if peak_amplitude >= threshold_state.signal_threshold2:
                        r_peaks.append(r_idx)
                        last_peak_idx = r_idx
                        
                        peak_time_ms = (r_idx / fs) * 1000.0
                        integrator_peak = integrator[r_idx] if r_idx < len(integrator) else 0
                        threshold_state.record_peak(peak_amplitude, integrator_peak, peak_time_ms)
                        break  # Only take the first valid searchback peak
    
    # 8) Update thresholds for next chunk based on detected peaks
    threshold_state.update_thresholds()
    
    return np.array(sorted(r_peaks), dtype=int), integrator


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
    
    r_peaks_local, integrator = detect_qrs_chunk(
        filtered, fs, processor['threshold_state']
    )
    
    # 3) Convert local indices to global indices and deduplicate overlapping detections
    deduped_r_peaks = []
    for idx in r_peaks_local:
        global_idx = start_global_idx + int(idx)
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



def stream_from_csv(filepath: str, fs: float = 360.0) -> tuple:
    """
    Generator that streams ECG data from a CSV file.
    
    Args:
        filepath: Path to CSV file with ECG samples (one per line or column)
        fs: Sampling frequency (Hz)
    
    Yields:
        Individual ECG samples as floats, normalized to mV range
    """
    try:
        import csv
        print(f"Reading from CSV file: {filepath}")

        def _is_number(value: str) -> bool:
            try:
                float(value)
                return True
            except (ValueError, TypeError):
                return False

        def _is_integer_like(value: str) -> bool:
            try:
                return abs(float(value) - round(float(value))) < 0.01
            except (ValueError, TypeError):
                return False

        def _choose_column_by_header(header_row: List[str]) -> int:
            normalized = [str(h).strip().lower() for h in header_row]
            for keyword in ['mlii', 'ecg', 'lead', 'v5', 'ii', 'signal', 'amplitude']:
                for idx, name in enumerate(normalized):
                    if keyword in name:
                        return idx
            if len(normalized) > 1 and normalized[0] in ('', 'index', 'sample', 'time', 't'):
                return 1
            return 0

        def _choose_column_from_preview(rows: List[List[str]]) -> int:
            if not rows:
                return 0
            # Prefer the first column that is not a simple sequential integer index.
            for idx in range(len(rows[0])):
                try:
                    values = [float(row[idx]) for row in rows if len(row) > idx and _is_number(row[idx])]
                except ValueError:
                    continue
                if len(values) < 3:
                    continue
                if all(_is_integer_like(str(v)) for v in values[:3]):
                    continue
                return idx
            if len(rows[0]) > 1:
                return 1
            return 0

        sample_buffer = []
        max_samples_check = 1000
        selected_column = 0
        header_names = None
        preview_rows = []

        with open(filepath, 'r', newline='') as f:
            reader = csv.reader(f)
            try:
                first_row = next(reader)
            except StopIteration:
                first_row = []

            if first_row and not all(_is_number(str(h).strip()) for h in first_row):
                header_names = first_row
            elif first_row:
                preview_rows.append(first_row)

            for row in reader:
                if len(preview_rows) < 5:
                    preview_rows.append(row)
                if len(sample_buffer) >= max_samples_check:
                    continue
                try:
                    if header_names is None:
                        sample_val = float(row[0]) if row else None
                    else:
                        sample_val = float(row[0]) if row else None
                    if sample_val is not None:
                        sample_buffer.append(sample_val)
                except (ValueError, IndexError):
                    continue

        if header_names is not None:
            selected_column = _choose_column_by_header(header_names)
        else:
            selected_column = _choose_column_from_preview(preview_rows)

        # Re-run the first pass using the selected signal column if necessary
        sample_buffer = []
        with open(filepath, 'r', newline='') as f:
            reader = csv.reader(f)
            if header_names is not None:
                try:
                    next(reader)
                except StopIteration:
                    pass

            for row in reader:
                if len(sample_buffer) >= max_samples_check:
                    break
                if len(row) > selected_column:
                    try:
                        sample_val = float(row[selected_column])
                        sample_buffer.append(sample_val)
                    except (ValueError, IndexError):
                        continue

        if len(sample_buffer) > 0:
            min_val = min(sample_buffer)
            max_val = max(sample_buffer)
            range_val = max_val - min_val
            is_large_integer = (range_val > 100 and
                                all(abs(x - round(x)) < 0.01 for x in sample_buffer[:100]))

            if is_large_integer:
                normalization_factor = 4.0 / range_val
                offset = (max_val + min_val) / 2.0
                print(f"  [INFO] Detected large integer values (range: {min_val:.0f} to {max_val:.0f})")
                print(f"  [INFO] Normalizing to ±2.0 mV range")
            else:
                normalization_factor = 1.0
                offset = 0.0
                print(f"  [INFO] Values appear to be pre-normalized (range: {min_val:.3f} to {max_val:.3f})")
        else:
            normalization_factor = 1.0
            offset = 0.0

        with open(filepath, 'r', newline='') as f:
            reader = csv.reader(f)
            if header_names is not None:
                try:
                    next(reader)
                except StopIteration:
                    return

            for row in reader:
                try:
                    if len(row) > selected_column:
                        sample_val = float(row[selected_column])
                        normalized_val = (sample_val - offset) * normalization_factor
                        yield normalized_val
                except (ValueError, IndexError):
                    continue
    except FileNotFoundError:
        print(f"Error: File not found: {filepath}")
        return


def stream_from_serial(port: str = 'COM3', baudrate: int = 9600, 
                       timeout: float = 1.0, sample_format: str = 'float') -> tuple:
    """
    Generator that streams ECG data from a serial device.
    
    Args:
        port: Serial port (e.g., 'COM3' on Windows, '/dev/ttyUSB0' on Linux)
        baudrate: Baud rate (typically 9600, 115200, etc.)
        timeout: Read timeout in seconds
        sample_format: 'float' for 4-byte float, 'int' for integer values
    
    Yields:
        Individual ECG samples as floats
    """
    try:
        import serial
        import struct
        
        print(f"Connecting to serial port: {port} at {baudrate} baud...")
        ser = serial.Serial(port, baudrate, timeout=timeout)
        print(f"[OK] Connected to {port}")
        
        try:
            while True:
                if sample_format == 'float':
                    # Expecting 4-byte float samples
                    if ser.in_waiting >= 4:
                        data = ser.read(4)
                        sample = struct.unpack('f', data)[0]
                        yield sample
                elif sample_format == 'int':
                    # Expecting integer samples
                    if ser.in_waiting >= 2:
                        data = ser.read(2)
                        sample = struct.unpack('h', data)[0] / 1000.0  # Convert to mV
                        yield sample
        except KeyboardInterrupt:
            print("\n[OK] Serial stream stopped by user")
        finally:
            ser.close()
            print("[OK] Serial port closed")
    except ImportError:
        print("Error: pyserial not installed. Install with: pip install pyserial")
        return
    except Exception as e:
        print(f"Error: {e}")
        return


def stream_from_network(host: str = 'localhost', port: int = 5000,
                       buffer_size: int = 1024) -> tuple:
    """
    Generator that streams ECG data from a network socket.
    
    Args:
        host: Server hostname or IP address
        port: Server port number
        buffer_size: Socket buffer size in bytes
    
    Yields:
        Individual ECG samples as floats
    """
    try:
        import socket
        import struct
        
        print(f"Connecting to {host}:{port}...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        
        try:
            sock.connect((host, port))
            print(f"[OK] Connected to {host}:{port}")
            
            while True:
                data = sock.recv(4)  # 4-byte float per sample
                if not data:
                    print("[OK] Connection closed by server")
                    break
                try:
                    sample = struct.unpack('f', data)[0]
                    yield sample
                except struct.error:
                    continue
        except socket.timeout:
            print("Error: Connection timeout")
            return
        except KeyboardInterrupt:
            print("\n[OK] Network stream stopped by user")
        finally:
            sock.close()
            print("[OK] Socket closed")
    except Exception as e:
        print(f"Error: {e}")
        return


def stream_synthetic(fs: float = 360.0, duration: float = 30.0, 
                     heart_rate: int = 72) -> tuple:
    """
    Generator that simulates a real ECG stream for testing.
    
    Args:
        fs: Sampling frequency (Hz)
        duration: Duration to stream (seconds)
        heart_rate: Simulated heart rate (bpm)
    
    Yields:
        Individual ECG samples as floats
    """
    print(f"Generating synthetic ECG ({duration}s at {fs} Hz, {heart_rate} bpm)...")
    total_samples = int(duration * fs)
    rr_samples = int(fs * 60.0 / heart_rate)
    signal = np.zeros(total_samples)

    for beat_start in range(0, total_samples, rr_samples):
        # Sharp Gaussian QRS spike — energy in 5–20 Hz range
        for offset in range(-25, 26):
            idx = beat_start + offset
            if 0 <= idx < total_samples:
                signal[idx] += 1.5 * np.exp(-0.5 * (offset / 5.0) ** 2)
        # Small T-wave ~200ms after QRS
        t_center = beat_start + int(0.2 * fs)
        for offset in range(-30, 31):
            idx = t_center + offset
            if 0 <= idx < total_samples:
                signal[idx] += 0.3 * np.exp(-0.5 * (offset / 15.0) ** 2)

    signal += 0.02 * np.random.randn(total_samples)
    for sample in signal:
        yield float(sample)


def print_threshold_diagnostics(processor: dict, chunk_idx: int):
    """Print adaptive threshold state for diagnostics."""
    ts = processor['threshold_state']
    print(f"  [Chunk {chunk_idx}] Thresholds: "
          f"T1_signal={ts.signal_threshold1:.4f}, "
          f"T2_signal={ts.signal_threshold2:.4f}, "
          f"noise={ts.noise_level:.4f}, "
          f"signal={ts.signal_level:.4f}, "
          f"peaks_in_history={len(ts.peak_values)}")


def compute_rmssd(r_peak_indices, fs):
    """Compute RMSSD (ms) from R-peak indices.

    RMSSD is the root mean square of successive differences of RR intervals (in ms).
    """
    if len(r_peak_indices) < 3:
        return float('nan')
    # Convert indices to times (seconds) and then to milliseconds
    times_ms = (r_peak_indices / float(fs)) * 1000.0
    rr_ms = np.diff(times_ms)
    successive_diffs = np.diff(rr_ms)
    rmssd = np.sqrt(np.mean(successive_diffs ** 2))
    return float(rmssd)


def setup_live_plot(fs: float, rolling_window_sec: float = 10.0):
    win = pg.GraphicsLayoutWidget(show=True, title="ECG Monitor")
    win.resize(800, 600)
    win.show()

    plot = win.addPlot()
    plot.setYRange(-1.5, 1.5)
    plot.setXRange(0, 10)
    plot.setLabel('left', 'Voltage (mV)')
    plot.setLabel('bottom', 'Time (seconds)')
    plot.showGrid(x=True, y=True, alpha=0.3)
    plot.setMouseEnabled(x=False, y=False)

    n_samples = int(fs * rolling_window_sec)

    line_ecg = plot.plot(pen=pg.mkPen(color='#00ff88', width=2))
    scatter_r = pg.ScatterPlotItem(
        size=10, 
        pen=pg.mkPen(None), # No border for the scatter points
        brush=pg.mkBrush('#ff4444') # Red color fill for the scatter points
    )    
    plot.addItem(scatter_r)
    cursor_line = plot.addLine(x=0, pen=pg.mkPen(color="#2057ab", width=1)) # Vertical cursor line (dark gray)

    return {
        'win': win,
        'ax1': plot,
        'line_ecg': line_ecg,
        'scatter_r': scatter_r,
        'cursor_line': cursor_line,
        'rolling_window_sec': rolling_window_sec,
    }   

def update_live_plot(plot_state: dict, fs: float, display_history: List[float],
                     integrator_history: List[float], r_peaks: List[int]):
    if len(display_history) == 0:
        return

    filtered_array = np.asarray(display_history, dtype=float)

    window_samples = int(plot_state['rolling_window_sec'] * fs)
    total_samples = len(filtered_array)

    # Fixed x-axis: 0 to rolling_window_sec, always
    x_fixed = np.arange(window_samples) / fs

    # Cursor position: where in the fixed window are we right now?
    cursor_pos = total_samples % window_samples
    cursor_time = (cursor_pos / window_samples) * plot_state['rolling_window_sec']
    plot_state['cursor_line'].setValue(cursor_time)

    # Rearrange the last window_samples so cursor position maps to x=0 on left
    if total_samples >= window_samples:
        # Rotate the data so the oldest visible sample is on the left
        segment = filtered_array[-window_samples:]
        display_seg = np.roll(segment, -cursor_pos)

    else:
        # Not enough data yet — pad with NaN
        display_seg = np.full(window_samples, np.nan)
        display_seg[:total_samples] = filtered_array

    # Void: blank out a small region just ahead of the cursor
    void_samples = int(0.3 * fs)  # 0.3 second void
    void_start = window_samples - void_samples
    display_seg[void_start:] = np.nan

    plot_state['line_ecg'].setData(x_fixed, display_seg)

    # R-peaks — only show those in the current visible window
    if len(r_peaks) > 0 and total_samples >= window_samples:
        window_start_idx = total_samples - window_samples
        visible_peaks = [p for p in r_peaks if window_start_idx <= p < total_samples]
        if visible_peaks:
            # Map peak indices into the rotated display space
            rotated_indices = [(p - window_start_idx - cursor_pos) % window_samples 
                               for p in visible_peaks]
            # Only show peaks not in the void
            valid = [(xi, p) for xi, p in zip(rotated_indices, visible_peaks) 
                     if xi < void_start]
            if valid:
                r_x = [x_fixed[xi] for xi, _ in valid]
                r_y = [filtered_array[p] if p < len(filtered_array) else 0.0 
                       for _, p in valid]
                plot_state['scatter_r'].setData(r_x, r_y)
            else:
                plot_state['scatter_r'].setData([], [])
        else:
            plot_state['scatter_r'].setData([], [])
    else:
        plot_state['scatter_r'].setData([], [])

# ============================================================================
# STREAMING DATA SOURCE SELECTION
# ============================================================================

print("\n" + "=" * 70)
print("ECG STREAMING DATA SOURCE SELECTOR")
print("=" * 70)
print("\nAvailable data sources:")
print("  1. Synthetic (simulated for testing)")
print("  2. CSV File (test with pre-recorded data)")
print("  3. Serial Port (live sensor connection)")
print("  4. Network (wireless/cloud streaming)")
print("=" * 70)

# Interactive data source selection
def select_data_source():
    """Prompt user to select a data source interactively."""
    while True:
        try:
            choice = input("\nSelect data source (1-4): ").strip()
            
            if choice == "1":
                return "synthetic", 1
            elif choice == "2":
                return "csv", 2
            elif choice == "3":
                return "serial", 3
            elif choice == "4":
                return "network", 4
            else:
                print("  [ERR] Invalid choice. Please enter 1, 2, 3, or 4.")
        except KeyboardInterrupt:
            print("\n\n  [ERR] Selection cancelled")
            sys.exit(0)

# Get user selection
DATA_SOURCE, choice_idx = select_data_source()
source_labels = ['Synthetic', 'CSV File', 'Serial Port', 'Network']
print(f"\n[OK] Selected: {source_labels[choice_idx - 1]}")

# Source-specific configuration
if DATA_SOURCE == "synthetic":
    print("\n[SYN] Synthetic ECG Configuration:")
    print("  - Duration: 30 seconds")
    print("  - Sampling Rate: 360 Hz")
    print("  - Heart Rate: 72 bpm")
    data_generator = stream_synthetic(fs=360.0, duration=30.0, heart_rate=72)
    source_name = "Synthetic ECG Stream"

elif DATA_SOURCE == "csv":
    csv_file = "ecg_data.csv"
    print(f"\n[CSV] CSV File Configuration:")
    print(f"  - File: {csv_file}")
    custom_file = input("  Enter CSV filename (or press Enter for 'ecg_data.csv'): ").strip()
    if custom_file:
        csv_file = custom_file
    data_generator = stream_from_csv(csv_file, fs=360.0)
    source_name = f"CSV File: {csv_file}"

elif DATA_SOURCE == "serial":
    serial_port = "COM3"
    serial_speed = 115200
    print(f"\n[SER] Serial Port Configuration:")
    print(f"  - Default Port: {serial_port}")
    print(f"  - Default Baud Rate: {serial_speed}")
    custom_port = input("  Enter COM port (or press Enter for 'COM3'): ").strip()
    if custom_port:
        serial_port = custom_port
    speed_input = input("  Enter baud rate (or press Enter for '115200'): ").strip()
    if speed_input:
        try:
            serial_speed = int(speed_input)
        except ValueError:
            print("  [WRN] Invalid baud rate, using default 115200")
            serial_speed = 115200
    data_generator = stream_from_serial(serial_port, baudrate=serial_speed)
    source_name = f"Serial Port: {serial_port} @ {serial_speed} baud"

elif DATA_SOURCE == "network":
    server_host = "localhost"
    server_port = 5000
    print(f"\n[NET] Network Configuration:")
    print(f"  - Default Host: {server_host}")
    print(f"  - Default Port: {server_port}")
    custom_host = input("  Enter server IP/hostname (or press Enter for 'localhost'): ").strip()
    if custom_host:
        server_host = custom_host
    port_input = input("  Enter server port (or press Enter for '5000'): ").strip()
    if port_input:
        try:
            server_port = int(port_input)
        except ValueError:
            print("  [WRN] Invalid port, using default 5000")
            server_port = 5000
    data_generator = stream_from_network(server_host, server_port)
    source_name = f"Network: {server_host}:{server_port}"

else:
    print(f"Error: Unknown data source '{DATA_SOURCE}'")
    sys.exit(1)

# ============================================================================
# STREAMING PROCESSING PIPELINE
# ============================================================================

print(f"\n{'=' * 70}")
print(f"ECG Signal Processor - Streaming Mode")
print(f"{'=' * 70}")
print(f"Data Source: {source_name}")
print(f"Processing signal in streaming chunks...\n")

# Create streaming processor
fs = 360.0 # Sampling frequency
WINDOW = 10  # Window size in seconds
n_samples = fs * WINDOW  # Number of samples in the window 

processor = create_streaming_processor(fs, window_duration_sec=3.0,
                                      overlap_duration_sec=1.0)

# Try to show a live plot when a display is available
has_display = bool(os.environ.get('DISPLAY', '')) or os.name == 'nt'
live_plot_state = None
if has_display:
    try:
        live_plot_state = setup_live_plot(fs, rolling_window_sec=10.0)
    except Exception:
        live_plot_state = None

chunk_count = 0
sample_count = 0
start_time = None

try:
    data_iter = iter(data_generator)
        
    def process_tick():
        global chunk_count, sample_count, start_time

        try:
            sample = next(data_iter)
        except StopIteration:
            timer.stop()
            return
        
        sample_count += 1
        if start_time is None:
            start_time = time.time()

        chunk = processor['buffer'].add_sample(sample)

        if chunk is not None:
            process_streaming_chunk(processor, chunk, chunk_count)
            chunk_count += 1

            if chunk_count % 1 == 0:
                print_threshold_diagnostics(processor, chunk_count)

            if live_plot_state is not None:
                update_live_plot(
                    live_plot_state, 
                    fs, 
                    processor['display_history'], 
                    processor['integrator_history'], 
                    processor['all_r_peaks']
                )
    timer = QtCore.QTimer()
    timer.timeout.connect(process_tick)
    timer.start(33)  # ~30 FPS update rate for the live plot

    QtWidgets.QApplication.instance().exec()

        
except KeyboardInterrupt:
    print("\n[OK] Stream interrupted by user")
except StopIteration:
    print("[OK] Data stream ended")
except Exception as e:
    print(f"Error during processing: {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# POST-PROCESSING & RESULTS
# ============================================================================

print(f"\n{'=' * 70}")
print("PROCESSING COMPLETE")
print(f"{'=' * 70}")
duration_sec = sample_count / fs if fs > 0 else 0.0
print(f"Total samples processed: {sample_count}")
print(f"Total recording duration: {duration_sec:.2f} seconds")
print(f"Total chunks: {chunk_count}")
print(f"Total R-peaks detected: {len(processor['all_r_peaks'])}")

unique_r_peaks = sorted(processor['all_r_peaks'])
print(f"Unique R-peaks (after deduplication): {len(unique_r_peaks)}")

# Compute metrics
rmssd_val = compute_rmssd(np.array(unique_r_peaks), fs)

if len(unique_r_peaks) > 1:
    rr_intervals = np.diff(np.array(unique_r_peaks) / fs) * 1000  # in ms
    avg_rr = np.mean(rr_intervals)
    hr = 60000 / avg_rr if avg_rr > 0 else 0
    print(f"Average RR Interval: {avg_rr:.1f} ms")
    print(f"Estimated Heart Rate: {hr:.1f} bpm")

if not np.isnan(rmssd_val):
    print(f"RMSSD: {rmssd_val:.2f} ms")

# Reconstruct full signal for visualization (if we have enough data)
if len(processor['processed_chunks']) > 0:
    # Uncomment below to generate visualization
    # Calculate total length
    max_end_idx = 0
    for chunk_data in processor['processed_chunks']:
        end_idx = chunk_data['global_start_idx'] + len(chunk_data['filtered'])
        max_end_idx = max(max_end_idx, end_idx)
    
    print(f"\nVisualization data ready - opening plot window...")
    print(f"  Debug: max_end_idx={max_end_idx}, chunks={len(processor['processed_chunks'])}")
    
    # Check if we have a display available
    import os
    has_display = bool(os.environ.get('DISPLAY', '')) or os.name == 'nt'  # Windows has display
    print(f"  Debug: has_display={has_display}, os.name='{os.name}'")
    print(f"  Debug: has_display={has_display}, os.name='{os.name}'")
    
    if not has_display:
        print("  [INFO] No display detected - saving plot to file instead")
        import matplotlib
        matplotlib.use('Agg')  # Use non-interactive backend
    
    # Print adaptive threshold statistics
    print(f"\n{'='*70}")
    print("ADAPTIVE THRESHOLD STATISTICS")
    print(f"{'='*70}")
    ts = processor['threshold_state']
    print(f"Final Threshold State:")
    print(f"  Signal Threshold 1 (T1): {ts.signal_threshold1:.6f}")
    print(f"  Signal Threshold 2 (T2): {ts.signal_threshold2:.6f}")
    print(f"  Integrator Threshold 1:  {ts.integrator_threshold1:.6f}")
    print(f"  Integrator Threshold 2:  {ts.integrator_threshold2:.6f}")
    print(f"  Estimated Signal Level:  {ts.signal_level:.6f}")
    print(f"  Estimated Noise Level:   {ts.noise_level:.6f}")
    print(f"  SNR Ratio:               {ts.signal_level / max(ts.noise_level, 1e-6):.2f}")
    print(f"  Peak History (last 8):   {len(ts.peak_values)} peaks")
    if len(ts.peak_values) > 0:
        print(f"  Mean Peak Amplitude:     {np.mean(list(ts.peak_values)):.6f}")
        print(f"  Peak Amplitude Range:    {np.min(list(ts.peak_values)):.6f} to {np.max(list(ts.peak_values)):.6f}")
    print(f"{'='*70}")
    
    # Uncomment below to generate visualization
    # Calculate total length from the continuous streamed history
    full_display = np.array(processor['display_history'], dtype=float)
    full_integrator = np.array(processor['integrator_history'], dtype=float)
    max_end_idx = len(full_display)

    print(f"\nVisualization data ready - opening plot window...")
    print(f"  Debug: max_end_idx={max_end_idx}, chunks={len(processor['processed_chunks'])}")

    # Check if we have a display available
    import os
    has_display = bool(os.environ.get('DISPLAY', '')) or os.name == 'nt'  # Windows has display
    print(f"  Debug: has_display={has_display}, os.name='{os.name}'")

    if max_end_idx > 0 and True:  # Enable visualization
        print("  [INFO] Starting visualization generation...")

        # Create time array
        time_axis = np.arange(max_end_idx) / fs
        
        # ============================================================================
        # VISUALIZATION - ROLLING WINDOW & DOWNSAMPLING
        # ============================================================================
        
        # Rolling window: Show only last 5 seconds
        rolling_window_sec = 5.0
        rolling_samples = int(rolling_window_sec * fs)
        
        if max_end_idx > rolling_samples:
            # Use only the last rolling_samples
            start_idx = max_end_idx - rolling_samples
            plot_time = time_axis[start_idx:]
            plot_filtered = full_display[start_idx:]
            plot_integrator = full_integrator[start_idx:]
            plot_title_suffix = f" (Last {rolling_window_sec}s)"
        else:
            # Show all data if less than rolling window
            start_idx = 0
            plot_time = time_axis
            plot_filtered = full_display
            plot_integrator = full_integrator
            plot_title_suffix = ""
        
        # Downsampling for visualization (keep processing at full rate)
        viz_fs = 250.0  # Target visualization sampling rate
        downsample_factor = 1  # Default no downsampling
        
        if fs > viz_fs:
            # Downsample for visualization only
            downsample_factor = int(fs / viz_fs)
            plot_indices = np.arange(0, len(plot_time), downsample_factor)
            plot_time = plot_time[plot_indices]
            plot_filtered = plot_filtered[plot_indices]
            plot_integrator = plot_integrator[plot_indices]
            print(f"  [INFO] Downsampled visualization from {fs}Hz to {viz_fs}Hz")
        
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 10), sharex=True,
                                             gridspec_kw={'height_ratios': [2.5, 2.5, 1.5]})
        
        # Plot 1: Raw vs Filtered Signal
        ax1.plot(plot_time, plot_filtered, color='#1f77b4', linewidth=1.2, label='Display ECG (0.5-40 Hz)')
        if len(unique_r_peaks) > 0:
            r_peak_times = np.array(unique_r_peaks) / fs
            # Filter peaks to those within the rolling window
            rolling_mask = (r_peak_times >= plot_time[0]) & (r_peak_times <= plot_time[-1])
            r_peak_times_filtered = r_peak_times[rolling_mask]
            
            if len(r_peak_times_filtered) > 0:
                # For peaks in rolling window, find corresponding y-values in the downsampled plot
                peak_y_values = []
                for peak_time in r_peak_times_filtered:
                    if len(plot_time) == 0:
                        peak_y_values.append(0)
                        continue
                    plot_idx = int(np.argmin(np.abs(plot_time - peak_time)))
                    if 0 <= plot_idx < len(plot_filtered):
                        peak_y_values.append(plot_filtered[plot_idx])
                    else:
                        peak_y_values.append(0)

                ax1.plot(r_peak_times_filtered, peak_y_values, 'ro', 
                        markersize=7, label=f'Detected R-peaks ({len(r_peak_times_filtered)})', zorder=5)
        ax1.set_ylabel("Voltage (mV)", fontsize=11)
        ax1.set_title(f"ECG Waveform - {source_name} (Streaming Processing){plot_title_suffix}", fontsize=12, fontweight='bold')
        ax1.grid(True, linestyle='--', alpha=0.5)
        ax1.legend(loc='upper right', fontsize=10)
        
        # Plot 2: Integrator Signal
        ax2.plot(plot_time, plot_integrator, color='#9467bd', linewidth=1.0)
        ax2.fill_between(plot_time, 0, plot_integrator, alpha=0.3, color='#9467bd')
        ax2.set_ylabel("Integrator Energy", fontsize=11)
        ax2.set_title("Pan-Tompkins Integrator Output", fontsize=12, fontweight='bold')
        ax2.grid(True, linestyle='--', alpha=0.5)
        
        # Plot 3: Chunk Boundaries (adjusted for rolling window)
        if len(processor['processed_chunks']) > 0:
            chunk_colors = plt.cm.tab20(np.linspace(0, 1, min(len(processor['processed_chunks']), 20)))
            for chunk_idx, chunk_data in enumerate(processor['processed_chunks']):
                chunk_start_idx = chunk_data['global_start_idx']
                chunk_end_idx = chunk_start_idx + len(chunk_data['filtered'])
                
                # Only show chunks that overlap with the rolling window
                if chunk_end_idx > start_idx and chunk_start_idx < max_end_idx:
                    # Clip chunk boundaries to rolling window
                    plot_chunk_start = max(chunk_start_idx, start_idx)
                    plot_chunk_end = min(chunk_end_idx, max_end_idx)
                    
                    plot_chunk_start_time = plot_chunk_start / fs
                    plot_chunk_end_time = plot_chunk_end / fs
                    
                    # Only plot if chunk is visible in rolling window
                    if plot_chunk_start_time <= plot_time[-1] and plot_chunk_end_time >= plot_time[0]:
                        ax3.axvline(plot_chunk_start_time, color=chunk_colors[chunk_idx % 20], alpha=0.6, linewidth=2)
                        chunk_center_time = (plot_chunk_start_time + plot_chunk_end_time) / 2
                        if plot_time[0] <= chunk_center_time <= plot_time[-1]:
                            ax3.text(chunk_center_time, 0.5, 
                                    f'C{chunk_idx}', ha='center', va='center', fontsize=8,
                                    bbox=dict(boxstyle='round', facecolor='white', alpha=0.7))
        
        ax3.set_ylabel("Chunks", fontsize=11)
        ax3.set_xlabel("Time (seconds)", fontsize=11)
        ax3.set_ylim(0, 1)
        ax3.set_yticks([])
        ax3.set_title("Chunk Processing Boundaries", fontsize=11, fontweight='bold')
        ax3.grid(True, linestyle='--', alpha=0.5, axis='x')
        
        plt.tight_layout()
        
        if has_display:
            print("  [INFO] Displaying interactive plot...")
            plt.show()
            print("[OK] Interactive plot displayed")
        else:
            print("  [INFO] No display detected - saving plot to file...")
            output_file = "ecg_analysis_plot.png"
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            plt.close()
            print(f"[OK] Plot saved to file: {output_file}")
        
        print("[OK] Visualization complete")
else:
    print("\n[WRN] No chunks processed - cannot generate visualization")

if live_plot_state is not None:
    try:
        plt.ioff()
        plt.show()
    except Exception:
        pass

print(f"{'=' * 70}\n")