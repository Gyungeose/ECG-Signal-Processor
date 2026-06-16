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

afib_detector = AfibDetector()

# Try to show a live plot when a display is available
has_display = bool(os.environ.get('DISPLAY', '')) or os.name == 'nt'
live_plot_state = None
if has_display and HAS_PYQTGRAPH:
    try:
        live_plot_state = setup_live_plot(app, fs, rolling_window_sec=10.0)
    except Exception as e:
        import traceback
        print(f"[ERR] Live plot setup failed: {e}")
        traceback.print_exc()
        live_plot_state = None
elif has_display and not HAS_PYQTGRAPH:
    print("[WARN] Display detected but pyqtgraph is unavailable, skipping live plot setup.")

chunk_count = 0
sample_count = 0
start_time = None

try:
    data_iter = iter(data_generator)
    
    def process_tick():
        global sample_count, chunk_count, start_time
        try:
            for _ in range(6):
                try:
                    sample = next(data_iter)
                except StopIteration:
                    timer.stop()
                    return
                sample_count += 1
                if start_time is None:
                    start_time = time.time()
                if live_plot_state is not None:
                    append_plot_sample(live_plot_state, sample)
                chunk = processor['buffer'].add_sample(sample)
                if chunk is not None:
                    process_streaming_chunk(processor, chunk, chunk_count)
                    chunk_count += 1
            if live_plot_state is not None:
                peaks   = processor['all_r_peaks']
                metrics = compute_metrics(peaks, fs)
                afib_status, afib_confidence = afib_detector.update(peaks, fs)

                update_live_plot(live_plot_state, fs, sample_count, peaks,
                                hr=metrics['hr'],
                                rmssd=metrics['rmssd'],
                                afib_status=afib_status,
                                afib_confidence=afib_confidence)
                
        except Exception as e:
            import traceback
            print(f"[ERR] process_tick crashed: {e}")
            traceback.print_exc()
            timer.stop()

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