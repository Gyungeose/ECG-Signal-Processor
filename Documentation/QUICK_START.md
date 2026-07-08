# Quick Start Guide - ECG Streaming Processor

## Running the Refactored Code

### 1. Prerequisites
```bash
pip install wfdb numpy matplotlib scipy
```

### 2. Run the Main Script
```bash
cd c:\Users\mauri\Projects\ECG-Signal-Processor
python main.py
```

**Expected Output:**
```
======================================================================
ECG Signal Processor - Streaming Mode with Sliding Window Buffer
======================================================================

Configuration:
  Sampling Rate: 360.0 Hz
  Window Duration: 3.0 sec
  Overlap Duration: 1.0 sec
  Total Signal Length: 1500 samples (4.17 sec)

Processing signal in streaming chunks...
✓ Processed 2 chunks
✓ Detected 4 R-peaks
✓ After deduplication: 4 unique R-peaks
✓ RMSSD = 45.23 ms

======================================================================
STREAMING PROCESSING SUMMARY
======================================================================
Signal Duration: 4.17 seconds
Total Samples: 1500
...
```

---

## What You'll See

### Plot 1: Raw vs Filtered Signal
- **Red line**: Original ECG signal
- **Blue line**: Filtered signal (streaming output)
- **Red dots**: Detected R-peaks (heartbeats)

### Plot 2: Integrator Energy
- **Purple line**: Pan-Tompkins integrator output
- Shows energy peaks corresponding to heartbeats

### Plot 3: Chunk Boundaries
- **Colored lines**: Show where chunks begin
- **Labels (C0, C1, C2...)**: Chunk indices
- Demonstrates streaming processing

---

## Key Configuration Options

### Adjust Window Size
Edit `main.py`, find this line and modify:

```python
window_sec = 3.0        # Change this (3 seconds)
overlap_sec = 1.0       # Or this (1 second overlap)
```

**Recommendations:**
- **Faster response**: `window_sec = 1.5, overlap_sec = 0.5`
- **More stable**: `window_sec = 5.0, overlap_sec = 2.0`
- **Balanced**: `window_sec = 3.0, overlap_sec = 1.0` (default)

### Adjust Filter Parameters
Find this line in the code:
```python
processor['filter'] = FilterState.create(fs=fs, lowcut=0.5, highcut=40.0, order=2)
```

Change the parameters:
- `lowcut`: Remove low-frequency noise (baseline wander) - try 0.5-2.0
- `highcut`: Remove high-frequency noise - try 30-50
- `order`: Filter steepness - try 2-4 (higher = steeper but slower)

### Adjust QRS Detection Sensitivity
Find this line:
```python
threshold_factor=1.2
```

- **Lower value** (0.8-1.0): Detects more peaks (more false positives)
- **Higher value** (1.3-1.5): Detects fewer peaks (fewer false positives)
- **Default** (1.2): Balanced

---

## Integration with Real Sensor Data

### Example: Serial Port Connection

```python
import serial

def process_from_serial(port='/dev/ttyUSB0', baudrate=9600, fs=360.0):
    """Read ECG from serial port and process in real-time."""
    processor = create_streaming_processor(fs)
    ser = serial.Serial(port, baudrate)
    
    chunk_count = 0
    try:
        while True:
            # Read one sample (assume device sends float values)
            if ser.in_waiting >= 4:  # 4 bytes for float32
                data = ser.read(4)
                sample = struct.unpack('f', data)[0]
                
                chunk = processor['buffer'].add_sample(sample)
                if chunk is not None:
                    process_streaming_chunk(processor, chunk, chunk_count)
                    chunk_count += 1
                    
                    # Print latest R-peak
                    if len(processor['all_r_peaks']) > 0:
                        print(f"R-peak detected: {processor['all_r_peaks'][-1]}")
    finally:
        ser.close()
```

---

## Understanding the Output

### RMSSD (ms)
- **What it is**: Root Mean Square of Successive Differences
- **Measures**: Heart rate variability
- **Normal**: 20-100 ms
- **Higher values**: More variable heart rate (stress, exercise)
- **Lower values**: More regular heart rate

### Heart Rate (bpm)
- **Calculation**: 60,000 / average_RR_interval (ms)
- **Normal resting**: 60-100 bpm
- **Shown in summary**: Computed from detected R-peaks

### Number of Chunks
- **Depends on**: Window size and signal length
- **Formula**: `(signal_length - window_length) / stride_length + 1`
- **Default**: ~3-second windows = 1-2 chunks for 4-second signal

---

## Troubleshooting

### Issue: Too few peaks detected
**Solution:** Decrease `threshold_factor` (try 1.0 instead of 1.2)

### Issue: Too many false peaks
**Solution:** Increase `threshold_factor` (try 1.5 instead of 1.2)

### Issue: Peaks only at signal start/end
**Solution:** Increase `overlap_sec` (try 1.5 seconds instead of 1.0)

### Issue: Slow performance
**Solution:** Increase batch_size in the loop:
```python
batch_size = 200  # Increase from 50
```

---

## Understanding Streaming vs Batch

### Original (Batch) Processing
```
Load entire signal → Filter entire signal → Detect all peaks
↓
Fast but requires all data in RAM
```

### New (Streaming) Processing
```
Batch 1 → Window 1 → Filter (state update) → Detect peaks
Batch 2 → Window 2 → Filter (state continues) → Detect peaks
Batch 3 → ...
↓
Works with continuous data stream
```

**Key Advantage**: Filter state is preserved between chunks, so filtering remains accurate even as data arrives incrementally.

---

## Files Overview

| File | Purpose |
|------|---------|
| `main.py` | Main implementation (refactored) |
| `REFACTORING_SUMMARY.md` | Overview of changes |
| `STREAMING_REFACTOR.md` | Technical documentation |
| `ADVANCED_USAGE.md` | Real-world examples |
| `QUICK_START.md` | This file |

---

## Next Steps

1. ✅ Run the code: `python main.py`
2. ✅ Adjust window size for your needs
3. ✅ Modify filter parameters if desired
4. ✅ See `ADVANCED_USAGE.md` for real-time integration
5. ✅ Reference `STREAMING_REFACTOR.md` for detailed documentation

---

## Common Questions

**Q: Can I still process entire files like before?**
A: Yes! The streaming code processes all data, just in chunks. The result is identical.

**Q: What if my data stream is irregular or has gaps?**
A: You can reset the filter state:
```python
processor['filter'].reset_state()
```

**Q: How do I get results in real-time without storing all chunks?**
A: Don't store `processed_chunks` and extract results immediately:
```python
r_peaks = sorted(list(set(processor['all_r_peaks'])))
```

**Q: Can I process multiple ECG leads?**
A: Yes! See `ADVANCED_USAGE.md` for the `process_multiple_leads()` example.

---

## Support

For detailed information:
- **Architecture details**: See `STREAMING_REFACTOR.md`
- **Code examples**: See `ADVANCED_USAGE.md`
- **Performance tips**: See `ADVANCED_USAGE.md` "Performance Optimization"
- **Implementation details**: See comments in `main.py`
