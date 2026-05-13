import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore
import numpy as np

app = QtWidgets.QApplication([])

win = pg.GraphicsLayoutWidget(show=True, title="Sweep Test")
win.resize(1000, 400)
win.show()

plot = win.addPlot()
plot.setYRange(-1.5, 1.5)
plot.setXRange(0, 10)
plot.setLabel('left', 'mV')
plot.setLabel('bottom', 'Time (s)')
plot.showGrid(x=True, y=True, alpha=0.3)
plot.setMouseEnabled(x=False, y=False)

FS = 360  # Sampling frequency
WINDOW = 10  # Window size in seconds
n_samples = FS * WINDOW  # Number of samples in the window 

x = np.linspace(0, WINDOW, n_samples)  # Time axis
buffer = np.full(n_samples, np.nan)  # Data buffer initialized with zeros
write_pos = 0  # Write position in the buffer
phase = 0 # Phase variable for simulating incoming data (sine wave)
sample_counter = 0  # Counter to keep track of the number of samples processed

peak_x = [] # List to store x-coordinates of detected peaks (time)
peak_y = [] # List to store y-coordinates of detected peaks (amplitude)

CHUNK = int(FS * 0.033)  # Number of samples to add in each update  

curve = plot.plot(x, buffer, pen=pg.mkPen(color='#00ff88', width=2))
cursor = plot.addLine(x=0, pen=pg.mkPen(color='#4488ff', width=1))

scatter = pg.ScatterPlotItem(
    size=10, 
    pen=pg.mkPen(None), # No border for the scatter points
    brush=pg.mkBrush('#ff4444') # Red color fill for the scatter points
)    
plot.addItem(scatter) 

def update():
    global write_pos, phase, buffer, sample_counter

    phase += 0.1  # Increment phase for the next update

    # Simulate incoming data (sine wave with noise)
    new_samples = np.sin(np.linspace(phase, phase + 0.3, CHUNK))

    for sample in new_samples:
        buffer[write_pos] = sample

        void_end = (write_pos + int(FS*0.3)) % n_samples  # Position to clear old data
        buffer[void_end] = np.nan  # Clear old data to create a "sweep" effect

        write_pos = (write_pos + 1) % n_samples  # Move write position (wrap around if necessary
        sample_counter += 1

    curve.setData(x, buffer)  # Update the curve with new data
    cursor.setValue(x[write_pos])  # Move the cursor to the current write position

    if sample_counter % FS == 0:  # Check for peaks every second
        peak_x.append(x[write_pos])  # Store the time of the detected peak
        peak_y.append(sample)  # Store the amplitude of the detected peak
        
    scatter.setData(peak_x, peak_y)  # Update scatter plot with detected peaks

timer = QtCore.QTimer()
timer.timeout.connect(update)
timer.start(33)  # Update every 33 ms

QtWidgets.QApplication.instance().exec()