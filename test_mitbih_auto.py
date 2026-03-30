#!/usr/bin/env python3
"""
Test script to run ECG processor with MIT-BIH data automatically
without requiring interactive user input.
"""

import sys
import os

# Temporarily patch the select_data_source and input functions
original_input = __builtins__.input

def mock_input(prompt=""):
    """Mock input that returns CSV file selection."""
    if "Select data source" in prompt:
        return "2"  # CSV option
    elif "CSV filename" in prompt:
        return "MIT-BIH Database/100_ekg.csv"
    return ""

# Patch input function
__builtins__.input = mock_input

# Now import and run the main script
print("=" * 70)
print("ECG PROCESSOR TEST - MIT-BIH DATA (100_ekg.csv)")
print("=" * 70)
print("\nUsing MIT-BIH record 100 with enhanced filtering pipeline:")
print("  - High-pass filter: 0.5 Hz (baseline wander removal)")
print("  - Bandpass filter: 5-15 Hz (QRS complex isolation)")
print("  - DC offset removal: Per-chunk mean subtraction")
print("=" * 70 + "\n")

# Run main.py
try:
    exec(open('main.py').read())
except Exception as e:
    print(f"\nError during execution: {e}")
    import traceback
    traceback.print_exc()
finally:
    # Restore original input function
    __builtins__.input = original_input
