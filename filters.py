# Module 1

import numpy as np
from scipy.signal import butter, sosfilt
from dataclasses import dataclass
from typing import Tuple

@dataclass
class FilterState:
    """Stateful Butterworth filter using second-order sections (SOS)."""
    sos: np.ndarray
    zi: np.ndarray
    
    @classmethod
    def create(cls, fs: float, lowcut: float = 5.0, highcut: float = 15.0, order: int = 2):
        """Create a bandpass filter for QRS complex isolation."""
        nyq = 0.5 * fs
        low = lowcut / nyq
        high = highcut / nyq
        sos = butter(order, [low, high], btype='band', output='sos')
        # Initialize state for each second-order section
        zi = np.zeros((sos.shape[0], 2))
        return cls(sos=sos, zi=zi)
    
    @classmethod
    def create_highpass(cls, fs: float, cutoff: float = 0.5, order: int = 2):
        """Create a high-pass filter for baseline wander removal."""
        nyq = 0.5 * fs
        normal_cutoff = cutoff / nyq
        sos = butter(order, normal_cutoff, btype='high', output='sos')
        # Initialize state for each second-order section
        zi = np.zeros((sos.shape[0], 2))
        return cls(sos=sos, zi=zi)
    
    @classmethod
    def create_display(cls, fs: float, lowcut: float = 0.5, highcut: float = 40.0, order: int = 2):
        """Wide-band filter for display — preserves full PQRST morphology."""
        nyq = 0.5 * fs
        sos = butter(order, [lowcut / nyq, highcut / nyq], btype='band', output='sos')
        zi = np.zeros((sos.shape[0], 2))
        return cls(sos=sos, zi=zi)
    
    @classmethod
    def create_notch(cls, fs: float, freq: float = 60.0, quality: float = 30.0):
        """Notch filter to remove powerline interference (60 Hz US, 50 Hz international)."""
        from scipy.signal import iirnotch
        b, a = iirnotch(freq, quality, fs)
        sos = np.array([[b[0], b[1], b[2], 1.0, a[1], a[2]]])
        zi = np.zeros((sos.shape[0], 2))
        return cls(sos=sos, zi=zi)
        
    def apply_chunk(self, chunk: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Apply filter to a chunk while preserving state.
        
        Returns:
            (filtered_chunk, integrator_chunk)
        """
        filtered, self.zi = sosfilt(self.sos, chunk, zi=self.zi)
        return filtered
    
    def reset_state(self):
        """Reset filter state (useful for discontinuities in signal)."""
        self.zi = np.zeros((self.sos.shape[0], 2))