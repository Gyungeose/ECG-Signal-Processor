import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore
import numpy as np

# Create the application

app = QtWidgets.QApplication([])

# Create the main window

win = pg.GraphicsLayoutWidget(show=True, title="PyQtGraph Test")
win.resize(800, 400)
win.show()

# Add a plot to the window

ecg_plot = win.addPlot()
ecg_plot.setYRange(0, 10)
ecg_plot.setLabel('left', 'Amplitude')
ecg_plot.setLabel('bottom', 'Samples')
ecg_plot.showGrid(x=True, y=True, alpha=0.3)


# Create a curve to plot the ECG data

x = np.linspace(0, 4*np.pi, 500)  # X-axis data (time or samples)

curves = []
for i in range(10):
    amplitude = (i+1) * 0.1
    curve = ecg_plot.plot(x, np.sin(x)*amplitude, pen=pg.mkPen(color=pg.intColor(i, hues=10), width=2))
    curves.append(curve)

# Simulate ECG data (for demonstration purposes)

phase = 0.0

# Update the plot in real-time

def update():
    global phase
    phase += 0.05
    for i, curve in enumerate(curves):
        curve.setData(x, np.sin(x + phase)*((i+1)*0.1)) # <-- this single line drives everything

# Start a timer to update the plot

timer = QtCore.QTimer()
timer.timeout.connect(update)
timer.start(33)  # Update every 33 ms

# Start the Qt event loop

QtWidgets.QApplication.instance().exec()
