# data_sources.py - Data Source Generators
 
'''
Streaming data generators for all supported ECG sources.
 
Every generator yields one sample-row at a time as a dict:
 
    {
        'samples':    np.ndarray,   # shape (N_leads,) — simultaneous voltages in mV
        'lead_names': list[str],    # e.g. ['I','II','III','aVR','aVL','aVF','V1'...'V6']
        'fs':         float,        # sampling frequency in Hz
        'n_leads':    int,          # number of leads
        'source':     str,          # database identifier
    }
 
This uniform contract means the rest of the pipeline (buffer.py, processor.py)
never needs to know which database or format the data came from — it only sees
the dict. Adding a new database means adding a new generator here; nothing
else changes.
 
SUPPORTED SOURCES
-----------------
PTB-XL          12-lead, WFDB format (.dat/.hea), 500 Hz or 100 Hz
Chapman-Shaoxing 12-lead, WFDB format (.dat/.hea), 500 Hz
MIT-BIH         2-lead,  WFDB format (.dat/.hea), 360 Hz
CSV             Any number of leads, plain CSV, user-specified fs
Synthetic       Single lead (Lead II proxy), generated on the fly
 
INSTALLATION
------------
WFDB format requires the wfdb library:
    pip install wfdb
'''
 
import numpy as np
from typing import Generator
 
# Standard 12-lead order used across PTB-XL and Chapman-Shaoxing
STANDARD_12_LEAD_NAMES = [
    'I', 'II', 'III', 'aVR', 'aVL', 'aVF',
    'V1', 'V2', 'V3', 'V4', 'V5', 'V6'
]
 
 
# --------------------------------------------------------------------------- #
#  WFDB reader (PTB-XL, Chapman-Shaoxing, MIT-BIH)                            #
# --------------------------------------------------------------------------- #
 
def stream_from_wfdb(record_path: str,
                     source: str = 'wfdb') -> Generator:
    '''
    Stream any WFDB-format ECG record sample by sample.
 
    Works with PTB-XL, Chapman-Shaoxing, MIT-BIH, and any other PhysioNet
    database that distributes data as .dat/.hea pairs. Pass the record path
    without file extension (e.g. '/data/ptbxl/records500/00001_hr').
 
    Lead names are read directly from the .hea header, so they will match
    the database's own naming convention automatically.
 
    Args:
        record_path: Path to the WFDB record, without file extension.
        source:      Label identifying the database (stored in the dict for
                     downstream use — does not affect signal processing).
 
    Yields:
        Sample dicts with 'samples', 'lead_names', 'fs', 'n_leads', 'source'.
    '''
    try:
        import wfdb
    except ImportError:
        print('[ERR] wfdb not installed. Run: pip install wfdb')
        return
 
    try:
        record = wfdb.rdrecord(record_path)
    except Exception as e:
        print(f'[ERR] Could not read WFDB record {record_path}: {e}')
        return
 
    signal   = record.p_signal          # shape (n_samples, n_leads), in mV
    fs       = float(record.fs)
    lead_names = list(record.sig_name)
    n_leads  = signal.shape[1]
    n_samples= signal.shape[0]
 
    print(f'[OK] Loaded {source} record: {n_samples} samples, '
          f'{n_leads} leads {lead_names}, {fs} Hz')
 
    for i in range(n_samples):
        row = signal[i]
        # Replace NaN (missing samples in some records) with 0.0
        row = np.where(np.isnan(row), 0.0, row)
        yield {
            'samples':    row,
            'lead_names': lead_names,
            'fs':         fs,
            'n_leads':    n_leads,
            'source':     source,
        }
 
 
def stream_ptbxl(record_path: str) -> Generator:
    '''Stream a PTB-XL record (12-lead, 500 Hz or 100 Hz WFDB format).'''
    return stream_from_wfdb(record_path, source='ptbxl')
 
 
def stream_chapman(record_path: str) -> Generator:
    '''Stream a Chapman-Shaoxing record (12-lead, 500 Hz WFDB format).'''
    return stream_from_wfdb(record_path, source='chapman')
 
 
def stream_mitbih(record_path: str) -> Generator:
    '''Stream a MIT-BIH record (2-lead, 360 Hz WFDB format).'''
    return stream_from_wfdb(record_path, source='mitbih')
 
 
# --------------------------------------------------------------------------- #
#  CSV reader (generic multi-lead)                                             #
# --------------------------------------------------------------------------- #
 
def stream_from_csv(filepath: str,
                    fs: float = 360.0,
                    lead_names: list = None) -> Generator:
    '''
    Stream an ECG CSV file sample by sample.
 
    Each row in the CSV should contain one sample per lead. If the first row
    is a header, lead names are read from it; otherwise `lead_names` is used
    if provided, or generic names ('Lead_0', 'Lead_1', ...) are assigned.
 
    Handles both pre-normalised (mV range) and large-integer (ADC units)
    values — integer ranges are rescaled to ±2 mV automatically.
 
    Args:
        filepath:   Path to the CSV file.
        fs:         Sampling frequency in Hz.
        lead_names: Optional list of lead name strings. Overridden by header
                    row if the CSV has one.
 
    Yields:
        Sample dicts with 'samples', 'lead_names', 'fs', 'n_leads', 'source'.
    '''
    import csv
 
    def _is_number(s):
        try:
            float(s)
            return True
        except (ValueError, TypeError):
            return False
 
    try:
        with open(filepath, 'r', newline='') as f:
            reader   = csv.reader(f)
            first    = next(reader, [])
            has_header = first and not all(_is_number(v.strip()) for v in first)
 
            if has_header:
                header     = [h.strip() for h in first]
                lead_names = header
                rows       = list(reader)
            else:
                rows       = [first] + list(reader)
 
        if not rows:
            print(f'[ERR] CSV file is empty: {filepath}')
            return
 
        # Determine number of leads from first valid row
        first_valid = next((r for r in rows if r), None)
        if first_valid is None:
            return
        n_leads = len(first_valid)
 
        if lead_names is None or len(lead_names) != n_leads:
            lead_names = [f'Lead_{i}' for i in range(n_leads)]
 
        # Sample 200 rows to decide whether to normalise
        sample_rows = []
        for row in rows[:200]:
            try:
                sample_rows.append([float(v) for v in row if v.strip()])
            except ValueError:
                continue
 
        if sample_rows:
            all_vals  = np.array(sample_rows).flatten()
            val_range = np.max(all_vals) - np.min(all_vals)
            if val_range > 100:
                # ADC integer values — rescale to ±2 mV
                mid   = (np.max(all_vals) + np.min(all_vals)) / 2.0
                scale = 4.0 / val_range
                print(f'[INFO] CSV: large integer values detected, '
                      f'rescaling to ±2 mV (range {val_range:.0f})')
            else:
                mid, scale = 0.0, 1.0
                print(f'[INFO] CSV: pre-normalised values detected '
                      f'(range {val_range:.3f})')
        else:
            mid, scale = 0.0, 1.0
 
        print(f'[OK] CSV: {len(rows)} samples, {n_leads} leads '
              f'{lead_names}, {fs} Hz')
 
        for row in rows:
            if not row:
                continue
            try:
                vals = np.array([float(v) for v in row[:n_leads]], dtype=float)
                vals = (vals - mid) * scale
                yield {
                    'samples':    vals,
                    'lead_names': lead_names,
                    'fs':         fs,
                    'n_leads':    n_leads,
                    'source':     'csv',
                }
            except (ValueError, IndexError):
                continue
 
    except FileNotFoundError:
        print(f'[ERR] File not found: {filepath}')
 
 
# --------------------------------------------------------------------------- #
#  Serial / Network (live hardware)                                            #
# --------------------------------------------------------------------------- #
 
def stream_from_serial(port: str = 'COM3', baudrate: int = 115200,
                       n_leads: int = 1,
                       lead_names: list = None,
                       fs: float = 360.0) -> Generator:
    '''
    Stream ECG data from a serial device.
 
    Expects the device to send one row of N_leads float values per sample,
    space- or comma-separated, terminated by newline.
 
    Args:
        port:       Serial port (e.g. 'COM3' or '/dev/ttyUSB0').
        baudrate:   Baud rate.
        n_leads:    Number of leads the device transmits.
        lead_names: Lead name list. Defaults to ['Lead_0', ...].
        fs:         Sampling frequency in Hz.
    '''
    if lead_names is None:
        lead_names = [f'Lead_{i}' for i in range(n_leads)]
 
    try:
        import serial
        ser = serial.Serial(port, baudrate, timeout=1.0)
        print(f'[OK] Connected to {port} at {baudrate} baud')
        try:
            while True:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if not line:
                    continue
                parts = line.replace(',', ' ').split()
                if len(parts) < n_leads:
                    continue
                try:
                    vals = np.array([float(p) for p in parts[:n_leads]])
                    yield {
                        'samples':    vals,
                        'lead_names': lead_names,
                        'fs':         fs,
                        'n_leads':    n_leads,
                        'source':     'serial',
                    }
                except ValueError:
                    continue
        except KeyboardInterrupt:
            print('\n[OK] Serial stream stopped')
        finally:
            ser.close()
    except ImportError:
        print('[ERR] pyserial not installed. Run: pip install pyserial')
    except Exception as e:
        print(f'[ERR] Serial error: {e}')
 
 
def stream_from_network(host: str = 'localhost', port: int = 5000,
                        n_leads: int = 1,
                        lead_names: list = None,
                        fs: float = 360.0) -> Generator:
    '''
    Stream ECG data from a TCP socket.
 
    Expects the server to send one newline-terminated row of N_leads float
    values per sample, space- or comma-separated.
    '''
    if lead_names is None:
        lead_names = [f'Lead_{i}' for i in range(n_leads)]
 
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5.0)
    try:
        sock.connect((host, port))
        print(f'[OK] Connected to {host}:{port}')
        buf = ''
        while True:
            data = sock.recv(1024).decode('utf-8', errors='ignore')
            if not data:
                break
            buf += data
            while '\n' in buf:
                line, buf = buf.split('\n', 1)
                parts = line.strip().replace(',', ' ').split()
                if len(parts) < n_leads:
                    continue
                try:
                    vals = np.array([float(p) for p in parts[:n_leads]])
                    yield {
                        'samples':    vals,
                        'lead_names': lead_names,
                        'fs':         fs,
                        'n_leads':    n_leads,
                        'source':     'network',
                    }
                except ValueError:
                    continue
    except socket.timeout:
        print('[ERR] Network connection timed out')
    except KeyboardInterrupt:
        print('\n[OK] Network stream stopped')
    finally:
        sock.close()
 
 
# --------------------------------------------------------------------------- #
#  Synthetic generator (testing)                                               #
# --------------------------------------------------------------------------- #
 
def stream_synthetic(fs: float = 360.0, duration: float = 30.0,
                     heart_rate: int = 72) -> Generator:
    '''
    Generate a synthetic single-lead ECG stream for testing.
 
    Produces a Lead II proxy — upright QRS, positive T wave — which is
    sufficient to test the full pipeline without real patient data.
 
    Yields sample dicts with n_leads=1 and lead_names=['II'].
    '''
    print(f'[SYN] Generating synthetic ECG: {duration}s at {fs} Hz, '
          f'{heart_rate} bpm')
 
    total_samples = int(duration * fs)
    rr_samples    = int(fs * 60.0 / heart_rate)
    signal        = np.zeros(total_samples)
 
    for beat_start in range(0, total_samples, rr_samples):
        # QRS spike
        for offset in range(-25, 26):
            idx = beat_start + offset
            if 0 <= idx < total_samples:
                signal[idx] += 1.5 * np.exp(-0.5 * (offset / 5.0) ** 2)
        # T wave ~200ms after QRS
        t_centre = beat_start + int(0.2 * fs)
        for offset in range(-30, 31):
            idx = t_centre + offset
            if 0 <= idx < total_samples:
                signal[idx] += 0.3 * np.exp(-0.5 * (offset / 15.0) ** 2)
 
    signal += 0.02 * np.random.randn(total_samples)
 
    for sample in signal:
        yield {
            'samples':    np.array([float(sample)]),
            'lead_names': ['II'],
            'fs':         fs,
            'n_leads':    1,
            'source':     'synthetic',
        }
 