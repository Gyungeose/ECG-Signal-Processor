# main.py - Entry Point
 
'''
Entry point for the ECG Signal Processor. Handles data source selection,
streams samples through the processing pipeline, drives the live display,
and prints a summary on completion.
 
PIPELINE ORCHESTRATION
----------------------
Each incoming sample is written into the circular sweep buffer for display,
and into the chunk buffer for processing. When the chunk buffer fills, a
full processing chunk is dispatched to processor.py. After every 6 samples
the display frame is updated at ~30 FPS.
 
Data flow per tick:
    sample → append_plot_sample()       (display buffer)
           → buffer.add_sample()        (chunk buffer)
           → process_streaming_chunk()  (when chunk ready)
           → compute_metrics()          (HR, RMSSD)
           → afib_detector.update()     (arrhythmia status — receives pre-computed RMSSD)
           → update_live_plot()         (render frame)
 
POSITION IN PIPELINE
--------------------
main.py orchestrates all modules:
    data_sources.py  →  processor.py  →  metrics.py  →  arrhythmia.py  →  display.py
'''
 
import os
import sys
import time
import numpy as np
import matplotlib.pyplot as plt
from metrics import compute_metrics, compute_rmssd
from data_sources import stream_from_csv, stream_from_serial, stream_from_network, stream_synthetic
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
    print("[WARN] pyqtgraph or Qt backend unavailable; live GUI mode is disabled.")
 
app = None
if HAS_PYQTGRAPH:
    app = QtWidgets.QApplication([])
 
# =============================================================================
# DATA SOURCE SELECTION
# =============================================================================
 
print("\n" + "=" * 70)
print("ECG STREAMING DATA SOURCE SELECTOR")
print("=" * 70)
print("\nAvailable data sources:")
print("  1. Synthetic (simulated for testing)")
print("  2. CSV File (test with pre-recorded data)")
print("  3. Serial Port (live sensor connection)")
print("  4. Network (wireless/cloud streaming)")
print("=" * 70)
 
 
def select_data_source():
    '''Prompt user to select a data source interactively.'''
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
 
 
DATA_SOURCE, choice_idx = select_data_source()
source_labels = ['Synthetic', 'CSV File', 'Serial Port', 'Network']
print(f"\n[OK] Selected: {source_labels[choice_idx - 1]}")
 
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
    serial_port  = "COM3"
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
 
# =============================================================================
# PIPELINE SETUP
# =============================================================================
 
print(f"\n{'=' * 70}")
print(f"ECG Signal Processor - Streaming Mode")
print(f"{'=' * 70}")
print(f"Data Source: {source_name}")
print(f"Processing signal in streaming chunks...\n")
 
fs = 360.0
 
processor     = create_streaming_processor(fs, window_duration_sec=3.0,
                                           overlap_duration_sec=1.0)
afib_detector = AfibDetector()
 
has_display     = bool(os.environ.get('DISPLAY', '')) or os.name == 'nt'
live_plot_state = None
 
if has_display and HAS_PYQTGRAPH:
    try:
        live_plot_state = setup_live_plot(app, fs, rolling_window_sec=10.0)
    except Exception as e:
        import traceback
        print(f"[ERR] Live plot setup failed: {e}")
        traceback.print_exc()
elif has_display and not HAS_PYQTGRAPH:
    print("[WARN] Display detected but pyqtgraph unavailable, skipping live plot.")
 
chunk_count  = 0
sample_count = 0
 
# =============================================================================
# STREAMING LOOP
# =============================================================================
 
try:
    data_iter = iter(data_generator)
 
    def process_tick():
        global sample_count, chunk_count
        try:
            for _ in range(6):
                try:
                    sample = next(data_iter)
                except StopIteration:
                    timer.stop()
                    return
                sample_count += 1
                if live_plot_state is not None:
                    append_plot_sample(live_plot_state, sample)
                chunk = processor['buffer'].add_sample(sample)
                if chunk is not None:
                    process_streaming_chunk(processor, chunk, chunk_count)
                    chunk_count += 1
 
            if live_plot_state is not None:
                peaks   = processor['all_r_peaks']
                metrics = compute_metrics(peaks, fs)
 
                # Pass the already-computed RMSSD into the AFib detector so it
                # does not recompute the same value from the same peak list.
                afib_status, afib_confidence = afib_detector.update(
                    peaks, fs, rmssd=metrics['rmssd']
                )
 
                update_live_plot(
                    live_plot_state, fs, sample_count, peaks,
                    hr=metrics['hr'],
                    rmssd=metrics['rmssd'],
                    afib_status=afib_status,
                    afib_confidence=afib_confidence,
                )
        except Exception as e:
            import traceback
            print(f"[ERR] process_tick crashed: {e}")
            traceback.print_exc()
            timer.stop()
 
    timer = QtCore.QTimer()
    timer.timeout.connect(process_tick)
    timer.start(33)
    QtWidgets.QApplication.instance().exec()
 
except KeyboardInterrupt:
    print("\n[OK] Stream interrupted by user")
except StopIteration:
    print("[OK] Data stream ended")
except Exception as e:
    import traceback
    print(f"Error during processing: {e}")
    traceback.print_exc()
 
# =============================================================================
# POST-PROCESSING SUMMARY
# =============================================================================
 
print(f"\n{'=' * 70}")
print("PROCESSING COMPLETE")
print(f"{'=' * 70}")
duration_sec   = sample_count / fs if fs > 0 else 0.0
unique_r_peaks = sorted(processor['all_r_peaks'])
 
print(f"Total samples processed:           {sample_count}")
print(f"Total recording duration:          {duration_sec:.2f} seconds")
print(f"Total chunks:                      {chunk_count}")
print(f"Unique R-peaks detected:           {len(unique_r_peaks)}")
 
if len(unique_r_peaks) > 1:
    rr_intervals = np.diff(np.array(unique_r_peaks) / fs) * 1000.0
    avg_rr       = np.mean(rr_intervals)
    hr           = 60000.0 / avg_rr if avg_rr > 0 else 0
    print(f"Average RR Interval:               {avg_rr:.1f} ms")
    print(f"Estimated Heart Rate:              {hr:.1f} bpm")
 
rmssd_val = compute_rmssd(np.array(unique_r_peaks), fs)
if not np.isnan(rmssd_val):
    print(f"RMSSD:                             {rmssd_val:.2f} ms")
 
# Adaptive threshold statistics
print(f"\n{'=' * 70}")
print("ADAPTIVE THRESHOLD STATISTICS")
print(f"{'=' * 70}")
ts = processor['threshold_state']
print(f"  Signal Threshold 1 (T1): {ts.signal_threshold1:.6f}")
print(f"  Signal Threshold 2 (T2): {ts.signal_threshold2:.6f}")
print(f"  Integrator Threshold 1:  {ts.integrator_threshold1:.6f}")
print(f"  Integrator Threshold 2:  {ts.integrator_threshold2:.6f}")
print(f"  Estimated Signal Level:  {ts.signal_level:.6f}")
print(f"  Estimated Noise Level:   {ts.noise_level:.6f}")
print(f"  SNR Ratio:               {ts.signal_level / max(ts.noise_level, 1e-6):.2f}")
print(f"  Peak History (last 8):   {len(ts.peak_values)} peaks")
if len(ts.peak_values) > 0:
    peak_list = list(ts.peak_values)
    print(f"  Mean Peak Amplitude:     {np.mean(peak_list):.6f}")
    print(f"  Peak Amplitude Range:    {np.min(peak_list):.6f} to {np.max(peak_list):.6f}")
 
# =============================================================================
# POST-PROCESSING VISUALISATION
# =============================================================================
 
if len(processor['processed_chunks']) > 0:
    # History deques → numpy arrays for plotting
    full_display    = np.array(list(processor['display_history']),    dtype=float)
    full_integrator = np.array(list(processor['integrator_history']), dtype=float)
    max_end_idx     = len(full_display)
 
    if max_end_idx > 0:
        # Offset into the full session that the capped history represents.
        # If the history deque filled, it holds only the last _HISTORY_CAP_SEC
        # seconds; earlier samples were dropped. We compute the global start
        # index so that time axis labels remain correct.
        history_start_global = max(0, sample_count - max_end_idx)
        time_axis = (history_start_global + np.arange(max_end_idx)) / fs
 
        rolling_samples = int(5.0 * fs)
 
        if max_end_idx > rolling_samples:
            start_idx       = max_end_idx - rolling_samples
            plot_time       = time_axis[start_idx:]
            plot_filtered   = full_display[start_idx:]
            plot_integrator = full_integrator[start_idx:]
            plot_title_suffix = " (Last 5s)"
        else:
            start_idx       = 0
            plot_time       = time_axis
            plot_filtered   = full_display
            plot_integrator = full_integrator
            plot_title_suffix = ""
 
        # Downsample for visualisation only
        downsample_factor = max(1, int(fs / 250.0))
        plot_indices    = np.arange(0, len(plot_time), downsample_factor)
        plot_time       = plot_time[plot_indices]
        plot_filtered   = plot_filtered[plot_indices]
        plot_integrator = plot_integrator[plot_indices]
 
        fig, (ax1, ax2, ax3) = plt.subplots(
            3, 1, figsize=(14, 10), sharex=True,
            gridspec_kw={'height_ratios': [2.5, 2.5, 1.5]}
        )
 
        ax1.plot(plot_time, plot_filtered, color='#1f77b4', linewidth=1.2,
                 label='Display ECG (0.5–40 Hz)')
 
        if len(unique_r_peaks) > 0:
            r_peak_times = np.array(unique_r_peaks) / fs
            rolling_mask = (r_peak_times >= plot_time[0]) & (r_peak_times <= plot_time[-1])
            r_peak_times = r_peak_times[rolling_mask]
            if len(r_peak_times) > 0:
                peak_y = [
                    plot_filtered[int(np.argmin(np.abs(plot_time - t)))]
                    for t in r_peak_times
                ]
                ax1.plot(r_peak_times, peak_y, 'ro', markersize=7,
                         label=f'R-peaks ({len(r_peak_times)})', zorder=5)
 
        ax1.set_ylabel("Voltage (mV)", fontsize=11)
        ax1.set_title(f"ECG Waveform — {source_name}{plot_title_suffix}",
                      fontsize=12, fontweight='bold')
        ax1.grid(True, linestyle='--', alpha=0.5)
        ax1.legend(loc='upper right', fontsize=10)
 
        ax2.plot(plot_time, plot_integrator, color='#9467bd', linewidth=1.0)
        ax2.fill_between(plot_time, 0, plot_integrator, alpha=0.3, color='#9467bd')
        ax2.set_ylabel("Integrator Energy", fontsize=11)
        ax2.set_title("Pan-Tompkins Integrator Output", fontsize=12, fontweight='bold')
        ax2.grid(True, linestyle='--', alpha=0.5)
 
        chunk_colors = plt.cm.tab20(
            np.linspace(0, 1, min(len(processor['processed_chunks']), 20))
        )
        for chunk_idx, chunk_data in enumerate(processor['processed_chunks']):
            c_start = chunk_data['global_start_idx']
            c_end   = c_start + chunk_data['chunk_len']
            if c_end > (history_start_global + start_idx) and c_start < (history_start_global + max_end_idx):
                t_start = max(c_start, history_start_global + start_idx) / fs
                t_end   = min(c_end,   history_start_global + max_end_idx) / fs
                if t_start <= plot_time[-1] and t_end >= plot_time[0]:
                    ax3.axvline(t_start, color=chunk_colors[chunk_idx % 20],
                                alpha=0.6, linewidth=2)
                    t_centre = (t_start + t_end) / 2
                    if plot_time[0] <= t_centre <= plot_time[-1]:
                        ax3.text(t_centre, 0.5, f'C{chunk_idx}',
                                 ha='center', va='center', fontsize=8,
                                 bbox=dict(boxstyle='round', facecolor='white', alpha=0.7))
 
        ax3.set_ylabel("Chunks", fontsize=11)
        ax3.set_xlabel("Time (seconds)", fontsize=11)
        ax3.set_ylim(0, 1)
        ax3.set_yticks([])
        ax3.set_title("Chunk Processing Boundaries", fontsize=11, fontweight='bold')
        ax3.grid(True, linestyle='--', alpha=0.5, axis='x')
 
        plt.tight_layout()
 
        if has_display:
            print("\n  [INFO] Displaying post-processing plot...")
            plt.show()
        else:
            output_file = "ecg_analysis_plot.png"
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            plt.close()
            print(f"\n  [INFO] Plot saved to {output_file}")
 
else:
    print("\n[WRN] No chunks processed — cannot generate visualisation")
 
print(f"\n{'=' * 70}\n")