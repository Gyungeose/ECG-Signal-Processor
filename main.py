# main.py - Entry Point
 
'''
Entry point for the ECG Signal Processor. Handles data source selection,
streams multi-lead samples through the processing pipeline, drives the live
display, and prints a summary on completion.
 
PIPELINE ORCHESTRATION
----------------------
Each incoming sample dict is unpacked — the sample row goes into the
circular sweep buffers (one per lead, for display) and into the chunk
buffer (for processing). When the chunk buffer fills, a full multi-lead
chunk is dispatched to processor.py. After every 6 samples the display
frame is updated at ~30 FPS.
 
Data flow per tick:
    sample_dict → append_plot_sample()      (display buffers, all leads)
                → buffer.add_sample()       (chunk buffer)
                → process_streaming_chunk() (when chunk ready)
                → compute_metrics()         (HR, RMSSD)
                → afib_detector.update()    (arrhythmia status)
                → update_live_plot()        (render frame)
 
POSITION IN PIPELINE
--------------------
main.py orchestrates all modules:
    data_sources.py → buffer.py → processor.py → metrics.py → arrhythmia.py → display.py
'''
 
import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from metrics import compute_metrics, compute_rmssd
from data_sources import (stream_ptbxl, stream_chapman, stream_mitbih,
                           stream_from_csv, stream_from_serial,
                           stream_from_network, stream_synthetic,
                           STANDARD_12_LEAD_NAMES)
from processor import create_streaming_processor, process_streaming_chunk
from display import setup_live_plot, append_plot_sample, update_live_plot
from arrhythmia import AfibDetector
 
try:
    import pyqtgraph as pg
    from pyqtgraph.Qt import QtWidgets, QtCore
    HAS_PYQTGRAPH = True
except ImportError:
    pg = None
    QtWidgets = None
    QtCore = None
    HAS_PYQTGRAPH = False
    print('[WARN] pyqtgraph or Qt backend unavailable; live GUI mode is disabled.')
 
app = None
if HAS_PYQTGRAPH:
    app = QtWidgets.QApplication([])
 
# =============================================================================
# DATA SOURCE SELECTION
# =============================================================================
 
print('\n' + '=' * 70)
print('ECG STREAMING DATA SOURCE SELECTOR')
print('=' * 70)
print('\nAvailable data sources:')
print('  1. Synthetic          (simulated single-lead, for testing)')
print('  2. MIT-BIH            (2-lead WFDB, 360 Hz)')
print('  3. PTB-XL             (12-lead WFDB, 500 Hz)')
print('  4. Chapman-Shaoxing   (12-lead WFDB, 500 Hz)')
print('  5. CSV File           (generic multi-lead CSV)')
print('  6. Serial Port        (live hardware)')
print('  7. Network            (TCP socket)')
print('=' * 70)
 
 
def select_data_source():
    '''Prompt user to select a data source interactively.'''
    while True:
        try:
            choice = input('\nSelect data source (1-7): ').strip()
            if choice in ('1', '2', '3', '4', '5', '6', '7'):
                return int(choice)
            print('  [ERR] Invalid choice. Please enter 1–7.')
        except KeyboardInterrupt:
            print('\n\n  [ERR] Selection cancelled')
            sys.exit(0)
 
 
choice = select_data_source()
 
if choice == 1:
    print('\n[SYN] Synthetic ECG — 30s at 360 Hz, 72 bpm')
    data_generator = stream_synthetic(fs=360.0, duration=30.0, heart_rate=72)
    source_name    = 'Synthetic ECG'
 
elif choice == 2:
    record = os.path.splitext(input('  MIT-BIH record path: ').strip())[0]
    data_generator = stream_mitbih(record)
    source_name    = f'MIT-BIH: {record}'

elif choice == 3:
    record = os.path.splitext(input('  PTB-XL record path: ').strip())[0]
    data_generator = stream_ptbxl(record)
    source_name    = f'PTB-XL: {record}'

elif choice == 4:
    record = os.path.splitext(input('  Chapman record path: ').strip())[0]
    data_generator = stream_chapman(record)
    source_name    = f'Chapman-Shaoxing: {record}'
 
elif choice == 5:
    filepath = input('  CSV file path: ').strip()
    fs_str   = input('  Sampling frequency Hz (Enter for 360): ').strip()
    fs_csv   = float(fs_str) if fs_str else 360.0
    data_generator = stream_from_csv(filepath, fs=fs_csv)
    source_name    = f'CSV: {filepath}'
 
elif choice == 6:
    port     = input('  Serial port (Enter for COM3): ').strip() or 'COM3'
    baud_str = input('  Baud rate (Enter for 115200): ').strip()
    baud     = int(baud_str) if baud_str else 115200
    data_generator = stream_from_serial(port, baudrate=baud)
    source_name    = f'Serial: {port} @ {baud}'
 
elif choice == 7:
    host     = input('  Host (Enter for localhost): ').strip() or 'localhost'
    port_str = input('  Port (Enter for 5000): ').strip()
    port     = int(port_str) if port_str else 5000
    data_generator = stream_from_network(host, port)
    source_name    = f'Network: {host}:{port}'
 
else:
    print(f'[ERR] Unknown choice')
    sys.exit(1)
 
# =============================================================================
# PIPELINE SETUP
# =============================================================================
# Peek at the first sample to learn n_leads, lead_names, and fs.
# The generator is not reset — the first sample is processed normally.
 
data_iter  = iter(data_generator)
first_dict = next(data_iter, None)
if first_dict is None:
    print('[ERR] Data source yielded no samples.')
    sys.exit(1)
 
fs         = first_dict['fs']
lead_names = first_dict['lead_names']
n_leads    = first_dict['n_leads']
 
print(f'\n{"=" * 70}')
print(f'ECG Signal Processor — Streaming Mode')
print(f'{"=" * 70}')
print(f'Source:     {source_name}')
print(f'Leads ({n_leads}): {lead_names}')
print(f'Sample rate: {fs} Hz')
print(f'Processing signal in streaming chunks...\n')
 
processor     = create_streaming_processor(
    fs=fs,
    lead_names=lead_names,
    window_duration_sec=3.0,
    overlap_duration_sec=1.0,
)
afib_detector = AfibDetector()
 
has_display     = bool(os.environ.get('DISPLAY', '')) or os.name == 'nt'
live_plot_state = None
 
if has_display and HAS_PYQTGRAPH:
    try:
        live_plot_state = setup_live_plot(
            app, fs,
            lead_names=lead_names,
            rolling_window_sec=10.0,
        )
    except Exception as e:
        import traceback
        print(f'[ERR] Live plot setup failed: {e}')
        traceback.print_exc()
elif has_display and not HAS_PYQTGRAPH:
    print('[WARN] Display detected but pyqtgraph unavailable.')
 
chunk_count  = 0
sample_count = 0
 
# =============================================================================
# STREAMING LOOP
# =============================================================================
 
def _process_sample(sample_dict: dict):
    '''Feed one sample dict through the display buffer and chunk buffer.'''
    global sample_count, chunk_count
 
    sample_row = sample_dict['samples']   # shape (n_leads,)
    sample_count += 1
 
    if live_plot_state is not None:
        append_plot_sample(live_plot_state, sample_row)
 
    chunk = processor['buffer'].add_sample(sample_row)
    if chunk is not None:
        process_streaming_chunk(processor, chunk, chunk_count)
        chunk_count += 1
 
 
try:
    # Process the first sample that was used for peeking
    _process_sample(first_dict)
 
    if HAS_PYQTGRAPH and live_plot_state is not None:
 
        def process_tick():
            global sample_count, chunk_count
            try:
                for _ in range(6):
                    sample_dict = next(data_iter, None)
                    if sample_dict is None:
                        timer.stop()
                        return
                    _process_sample(sample_dict)
 
                peaks                        = processor['all_r_peaks']
                metrics                      = compute_metrics(peaks, fs)
                afib_status, afib_confidence = afib_detector.update(peaks, fs)
 
                update_live_plot(
                    live_plot_state, fs, sample_count, peaks,
                    hr=metrics['hr'],
                    rmssd=metrics['rmssd'],
                    afib_status=afib_status,
                    afib_confidence=afib_confidence,
                )
            except Exception as e:
                import traceback
                print(f'[ERR] process_tick crashed: {e}')
                traceback.print_exc()
                timer.stop()
 
        timer = QtCore.QTimer()
        timer.timeout.connect(process_tick)
        timer.start(33)
        QtWidgets.QApplication.instance().exec()
 
    else:
        # Headless mode — consume the full stream without display
        for sample_dict in data_iter:
            _process_sample(sample_dict)
 
except KeyboardInterrupt:
    print('\n[OK] Stream interrupted by user')
except Exception as e:
    import traceback
    print(f'[ERR] {e}')
    traceback.print_exc()
 
# =============================================================================
# POST-PROCESSING SUMMARY
# =============================================================================
 
print(f'\n{"=" * 70}')
print('PROCESSING COMPLETE')
print(f'{"=" * 70}')
 
duration_sec   = sample_count / fs if fs > 0 else 0.0
unique_r_peaks = sorted(processor['all_r_peaks'])
 
print(f'  Total samples:     {sample_count}')
print(f'  Duration:          {duration_sec:.2f} s')
print(f'  Chunks processed:  {chunk_count}')
print(f'  R-peaks detected:  {len(unique_r_peaks)}')
print(f'  Detection lead:    {processor["detection_lead"]}')
 
if len(unique_r_peaks) > 1:
    rr   = np.diff(np.array(unique_r_peaks) / fs) * 1000.0
    hr   = 60000.0 / np.mean(rr) if np.mean(rr) > 0 else 0
    print(f'  Avg RR interval:   {np.mean(rr):.1f} ms')
    print(f'  Heart rate:        {hr:.1f} bpm')
 
rmssd_val = compute_rmssd(np.array(unique_r_peaks), fs)
if not np.isnan(rmssd_val):
    print(f'  RMSSD:             {rmssd_val:.2f} ms')
 
# Adaptive threshold statistics
print(f'\n{"=" * 70}')
print('ADAPTIVE THRESHOLD STATISTICS')
print(f'{"=" * 70}')
ts = processor['threshold_state']
print(f'  Signal Threshold 1:  {ts.signal_threshold1:.6f}')
print(f'  Signal Threshold 2:  {ts.signal_threshold2:.6f}')
print(f'  Integrator T1:       {ts.integrator_threshold1:.6f}')
print(f'  Integrator T2:       {ts.integrator_threshold2:.6f}')
print(f'  Signal Level:        {ts.signal_level:.6f}')
print(f'  Noise Level:         {ts.noise_level:.6f}')
print(f'  SNR:                 {ts.signal_level / max(ts.noise_level, 1e-6):.2f}')
if ts.peak_values:
    peak_list = list(ts.peak_values)
    print(f'  Mean Peak Amplitude: {np.mean(peak_list):.6f}')
 
# Post-processing matplotlib plot (detection lead only)
detection_lead = processor['detection_lead']
full_display   = np.array(
    list(processor['display_history'][detection_lead]), dtype=float
)
full_integrator = np.array(list(processor['integrator_history']), dtype=float)
max_end_idx     = len(full_display)
 
if max_end_idx > 0:
    time_axis       = np.arange(max_end_idx) / fs
    rolling_samples = int(5.0 * fs)
 
    if max_end_idx > rolling_samples:
        s               = max_end_idx - rolling_samples
        plot_time       = time_axis[s:]
        plot_display    = full_display[s:]
        plot_integrator = full_integrator[s:] if len(full_integrator) >= max_end_idx else full_integrator
        title_suffix    = ' (Last 5s)'
    else:
        s               = 0
        plot_time       = time_axis
        plot_display    = full_display
        plot_integrator = full_integrator
        title_suffix    = ''
 
    ds = max(1, int(fs / 250.0))
    plot_time       = plot_time[::ds]
    plot_display    = plot_display[::ds]
    if len(plot_integrator) >= len(plot_time):
        plot_integrator = plot_integrator[::ds]
 
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True,
                                    gridspec_kw={'height_ratios': [2, 1]})
 
    ax1.plot(plot_time, plot_display, color='#1f77b4', linewidth=1.2,
             label=f'Display ECG — {detection_lead}')
 
    if unique_r_peaks:
        rt = np.array(unique_r_peaks) / fs
        mask = (rt >= plot_time[0]) & (rt <= plot_time[-1])
        rt = rt[mask]
        if len(rt) > 0:
            ry = [plot_display[int(np.argmin(np.abs(plot_time - t)))]
                  for t in rt]
            ax1.plot(rt, ry, 'ro', markersize=7,
                     label=f'R-peaks ({len(rt)})', zorder=5)
 
    ax1.set_ylabel('Voltage (mV)', fontsize=11)
    ax1.set_title(f'ECG — {source_name}{title_suffix}',
                  fontsize=12, fontweight='bold')
    ax1.grid(True, linestyle='--', alpha=0.5)
    ax1.legend(loc='upper right', fontsize=10)
 
    if len(plot_integrator) == len(plot_time):
        ax2.plot(plot_time, plot_integrator, color='#9467bd', linewidth=1.0)
        ax2.fill_between(plot_time, 0, plot_integrator,
                         alpha=0.3, color='#9467bd')
        ax2.set_ylabel('Integrator Energy', fontsize=11)
        ax2.set_title('Pan-Tompkins Integrator Output',
                      fontsize=12, fontweight='bold')
        ax2.grid(True, linestyle='--', alpha=0.5)
 
    ax2.set_xlabel('Time (seconds)', fontsize=11)
    plt.tight_layout()
 
    if has_display:
        print('\n  [INFO] Displaying post-processing plot...')
        plt.show()
    else:
        plt.savefig('ecg_analysis_plot.png', dpi=300, bbox_inches='tight')
        plt.close()
        print('\n  [INFO] Plot saved to ecg_analysis_plot.png')
 
else:
    print('\n[WRN] No signal history — cannot generate plot')
 
print(f'\n{"=" * 70}\n')
 