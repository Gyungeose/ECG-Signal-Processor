# buffer.py - Streaming Buffer
 
'''
Sliding window buffer for streaming multi-lead ECG data.
 
Collects incoming sample rows (one voltage per lead per tick) into a
fixed-length window. When the window fills, a complete chunk is returned
and the buffer slides forward by one stride, retaining the overlap region
for the next chunk.
 
The buffer is lead-agnostic — it stores whatever shape arrives and returns
it in the same shape. A single-lead stream (n_leads=1) and a 12-lead stream
(n_leads=12) are handled identically.
 
POSITION IN PIPELINE
--------------------
data_sources.py  →  buffer.py  →  processor.py
                         ↑ YOU ARE HERE
'''
 
import numpy as np
from collections import deque
from dataclasses import dataclass, field
from typing import Optional
from dataclasses import dataclass
 
 
@dataclass
class StreamingBuffer:
    '''
    Sliding window buffer for streaming multi-lead ECG data.
 
    Accepts one sample row at a time (shape: (n_leads,)) and returns a
    complete chunk (shape: (window_samples, n_leads)) once the window fills.
    After each chunk, the buffer retains `overlap_samples` rows so that
    detection algorithms always have context across chunk boundaries.
 
    Attributes:
        window_duration_sec:  Length of each chunk in seconds.
        overlap_duration_sec: Overlap between consecutive chunks in seconds.
        fs:                   Sampling frequency in Hz.
        n_leads:              Number of leads (columns per sample row).
    '''
    window_duration_sec:  float
    overlap_duration_sec: float
    fs:                   float
    n_leads:              int = 1
    global_sample_idx:    int = 0
 
    def __post_init__(self):
        self.window_samples  = int(self.window_duration_sec  * self.fs)
        self.overlap_samples = int(self.overlap_duration_sec * self.fs)
        self.stride_samples  = self.window_samples - self.overlap_samples
 
        # Each element is a (n_leads,) array — one row per sample
        self.buffer: deque = deque(maxlen=self.window_samples)
 
    def add_sample(self, sample: np.ndarray) -> Optional[np.ndarray]:
        '''
        Add one sample row to the buffer and advance the global index.
 
        Args:
            sample: Shape (n_leads,) — simultaneous voltages for all leads.
 
        Returns:
            A complete chunk of shape (window_samples, n_leads) when the
            window is full, otherwise None.
        '''
        self.buffer.append(np.asarray(sample, dtype=float))
        self.global_sample_idx += 1
 
        if len(self.buffer) == self.window_samples:
            chunk = np.stack(list(self.buffer), axis=0)  # (window_samples, n_leads)
 
            # Slide forward by stride — discard non-overlap samples
            for _ in range(self.stride_samples):
                self.buffer.popleft()
 
            return chunk
        return None
 
    def add_samples(self, samples: np.ndarray) -> list:
        '''
        Add multiple sample rows and return all complete chunks.
 
        Args:
            samples: Shape (N, n_leads) — a batch of sample rows.
 
        Returns:
            List of chunks, each of shape (window_samples, n_leads).
        '''
        chunks = []
        for row in samples:
            chunk = self.add_sample(row)
            if chunk is not None:
                chunks.append(chunk)
        return chunks
 
    def get_current_buffer(self) -> np.ndarray:
        '''
        Return the current buffer contents as an array.
 
        Returns:
            Shape (current_len, n_leads) — may be less than window_samples
            if the buffer has not yet filled.
        '''
        if not self.buffer:
            return np.zeros((0, self.n_leads), dtype=float)
        return np.stack(list(self.buffer), axis=0)
 
    def current_time_range(self) -> tuple:
        '''
        Return the (start, end) time in seconds for the current buffer.
        '''
        start_idx = self.global_sample_idx - len(self.buffer)
        end_idx   = self.global_sample_idx
        return start_idx / self.fs, end_idx / self.fs
 