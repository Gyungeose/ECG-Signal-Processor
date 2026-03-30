#!/usr/bin/env python3
import csv

print("Testing CSV file reading...")
with open('simple_ecg.csv', 'r') as f:
    reader = csv.reader(f)
    count = 0
    for row in reader:
        if count < 5:
            print(f'Row {count}: {row}')
            count += 1
        else:
            break

print('CSV file can be read successfully!')