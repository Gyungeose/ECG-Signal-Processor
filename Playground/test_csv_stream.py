#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(__file__))

from main import stream_from_csv

print("Testing CSV streaming function...")
try:
    count = 0
    for sample in stream_from_csv('simple_ecg.csv', fs=360.0):
        if count < 10:
            print(f"Sample {count}: {sample}")
            count += 1
        else:
            break
    print("CSV streaming works successfully!")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()