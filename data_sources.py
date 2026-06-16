# Module 

import numpy as np
from typing import Tuple, List

def stream_from_csv(filepath: str, fs: float = 360.0) -> Tuple:
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
                       timeout: float = 1.0, sample_format: str = 'float') -> Tuple:
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
                       buffer_size: int = 1024) -> Tuple:
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
                     heart_rate: int = 72) -> Tuple:
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