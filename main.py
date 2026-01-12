import wfdb
import numpy as np
import matplotlib.pyplot as plt

# Connect to the PhysioNet MIT-BIH database

def load_cardiology_data():
    print("Connecting to PhysioNet MIT-BIH Database...")
    
    # Download record '100' (a pre-recorded ECG sample) with 1500 samples (~4 seconds at 360Hz)
    record = wfdb.rdrecord('100', pn_dir='mitdb', sampto=1500)
    
    v_signal = record.p_signal[:, 0] # Extract the voltage signal from Lead II (standard cardiac rhythm strip)
    fs = record.fs # Get the sampling frequency (360 Hz = 360 measurements per second)

    # Converts sample indices to actual time in seconds using: Time = Sample Index / Sampling Frequency
    time = np.arange(len(v_signal)) / fs
    
    return time, v_signal, record.record_name

# Visualization of the ECG Signal
time, voltage, name = load_cardiology_data() # Call the function to get the ECG data

plt.figure(figsize=(12, 5))
plt.plot(time, voltage, color='#d62728', linewidth=1.5) # Creates a 12×5 inch figure and plots the voltage over time in red

# Add title, axis labels, and a grid for readability
plt.title(f"Raw ECG Waveform - Patient {name} (Lead II)", fontsize=14)
plt.xlabel("Time (seconds)", fontsize=12)
plt.ylabel("Voltage (mV)", fontsize=12)
plt.grid(True, linestyle='--', alpha=0.7)

# Annotate an R-peak (the highest point in the QRS complex, a key cardiac feature)
plt.annotate('R-Peak', xy=(1.1, 1.2), xytext=(1.5, 1.5),
             arrowprops=dict(facecolor='black', shrink=0.05))

plt.tight_layout()
plt.show()