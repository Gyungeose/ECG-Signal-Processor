#So essentially, we're trying to fix the laggy antics (It takes half a minute to update adn does so in batches rather than continuously like I hoped) by isolating the update function. It works in the sweep_test.py file, but not with the main.py. For why? God alone knows.

import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore
import numpy as np

app = QtWidgets.QApplication([])

win = pg.GraphicsLayoutWidget(show=True, title="ECG Monitor")
win.resize(800, 600)
win.show()

plot = win.addPlot()
plot.setYRange(-1.5, 1.5)
plot.setXRange(0, 10)
plot.setLabel('left', 'Voltage (mV)')
plot.setLabel('bottom', 'Time (seconds)')
plot.showGrid(x=True, y=True, alpha=0.3)
plot.setMouseEnabled(x=False, y=False)

fs = 360  # Sampling frequency
WINDOW = 10  # Window size in seconds
n_samples = fs * WINDOW  # Number of samples in the window 

line_ecg = plot.plot(pen=pg.mkPen(color='#00ff88', width=2))
cursor_line = plot.addLine(x=0, pen=pg.mkPen(color="#2057ab", width=1)) # Vertical cursor line (dark gray)

x = np.linspace(0, WINDOW, n_samples)  # Time axis
buffer = np.full(n_samples, np.nan)  # Data buffer initialized with zeros
write_pos = 0  # Write position in the buffer
phase = 0 # Phase variable for simulating incoming data (sine wave)
sample_counter = 0  # Counter to keep track of the number of samples processed

CHUNK = int(fs * 0.033)  # Number of samples to add in each update  

curve = plot.plot(x, buffer, pen=pg.mkPen(color='#00ff88', width=2))
cursor = plot.addLine(x=0, pen=pg.mkPen(color='#4488ff', width=1))

def update():
    global write_pos, phase, buffer, sample_counter

    phase += 0.1  # Increment phase for the next update

    # Simulate incoming data (sine wave with noise)
    new_samples = np.sin(np.linspace(phase, phase + 0.3, CHUNK))

    for sample in new_samples:
        buffer[write_pos] = sample

        void_end = (write_pos + int(fs*0.3)) % n_samples  # Position to clear old data
        buffer[void_end] = np.nan  # Clear old data to create a "sweep" effect

        write_pos = (write_pos + 1) % n_samples  # Move write position (wrap around if necessary
        sample_counter += 1

    curve.setData(x, buffer)  # Update the curve with new data
    cursor.setValue(x[write_pos])  # Move the cursor to the current write position

timer = QtCore.QTimer()
timer.timeout.connect(update)
timer.start(33)  # Update every 33 ms

QtWidgets.QApplication.instance().exec()