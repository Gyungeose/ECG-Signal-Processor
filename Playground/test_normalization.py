#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(__file__))

from main import stream_from_csv
import numpy as np

print("Testing CSV normalization...")
samples = []
count = 0
for sample in stream_from_csv('large_integer_ecg.csv', fs=360.0):
    samples.append(sample)
    count += 1
    if count >= 10:  # Just check first 10 samples
        break

print(f"First 10 normalized samples: {samples}")
print(f"Min: {min(samples):.3f}, Max: {max(samples):.3f}")
print("Normalization test complete!")