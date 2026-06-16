# Module 2

import numpy as np
from collections import deque
from dataclasses import dataclass
from typing import List, Optional, Tuple

@dataclass
class StreamingBuffer:
    """Sliding window buffer for streaming ECG data processing."""
    window_duration_sec: float
    overlap_duration_sec: float
    fs: float
    global_sample_idx: int = 0
    
    def __post_init__(self):
        """Initialize buffer dimensions."""
        self.window_samples = int(self.window_duration_sec * self.fs)
        self.overlap_samples = int(self.overlap_duration_sec * self.fs)
        self.stride_samples = self.window_samples - self.overlap_samples
        self.buffer = deque(maxlen=self.window_samples)
    
    def add_sample(self, value: float) -> Optional[np.ndarray]:
        """
        Add a single sample to the buffer.
        Returns a complete window chunk if ready, None otherwise.
        """
        self.buffer.append(value)
        self.global_sample_idx += 1
        
        if len(self.buffer) == self.window_samples:
            chunk = np.array(list(self.buffer), dtype=float)
            # Advance by stride (remove overlap for next chunk)
            for _ in range(self.stride_samples):
                self.buffer.popleft()
            return chunk
        return None
    
    def add_samples(self, samples: np.ndarray) -> List[np.ndarray]:
        """
        Add multiple samples and return all complete chunks.
        """
        chunks = []
        for sample in samples:
            chunk = self.add_sample(sample)
            if chunk is not None:
                chunks.append(chunk)
        return chunks
    
    def get_current_buffer(self) -> np.ndarray:
        """Get the current buffer contents (for incomplete windows)."""
        return np.array(list(self.buffer), dtype=float)
    
    def current_time_range(self) -> Tuple[float, float]:
        """Get time range (start, end) in seconds for current buffer."""
        start_idx = self.global_sample_idx - len(self.buffer)
        end_idx = self.global_sample_idx
        return start_idx / self.fs, end_idx / self.fs
    