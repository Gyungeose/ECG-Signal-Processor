# display.py - Live ECG Rendering
 
'''
Responsible solely for rendering the live ECG sweep display and updating
the metrics panel. Contains no clinical logic — all detection, metric
computation, and arrhythmia classification happen upstream and are passed
in as arguments.
 
WHAT THIS MODULE DOES
---------------------
- Maintains a circular sweep buffer that mimics a real bedside monitor:
  signal writes left to right, wraps, and overwrites old data
- Renders R-peak markers at their correct buffer positions
- Displays HR, RMSSD, and AFib status as pre-computed values
- Manages the void gap (blank region ahead of the write cursor)
- Draws a dual-weight ECG-paper-style grid (small/large squares)
 
WHAT THIS MODULE DOES NOT DO
-----------------------------
- Detect R-peaks                (detection.py)
- Compute HR or RMSSD           (metrics.py)
- Classify arrhythmias          (arrhythmia.py)
 
POSITION IN PIPELINE
--------------------
detection.py  →  processor.py  →  metrics.py  →  display.py
                                                       ↑ YOU ARE HERE
'''
 
import numpy as np
import pyqtgraph as pg
from typing import List, Optional
 
 
# --------------------------------------------------------------------------- #
#  ECG-paper-style grid                                                        #
# --------------------------------------------------------------------------- #
#
# Real ECG paper at standard 25 mm/s speed, 1 mV calibration:
#   small square = 0.04s (40ms) horizontally,  0.1 mV vertically
#   large square = 0.20s (200ms) horizontally, 0.5 mV vertically
#                  (every 5th small square — bolder, darker line)
#
# PyQtGraph's built-in showGrid() only draws a single uniform weight, so the
# grid is built manually here as two layers: light minor lines (small
# squares) and bold major lines (large squares), matching printed ECG paper.
 
SMALL_SQUARE_SEC = 0.04   # 40 ms — not used for X grid lines (see below)
LARGE_SQUARE_SEC = 0.20   # 200 ms — base unit for X-axis grid lines
SMALL_SQUARE_MV  = 0.1    # base unit for Y-axis minor grid lines
LARGE_SQUARE_MV  = 0.5    # base unit for Y-axis major grid lines
 
# X-axis (time): two tiers — every 0.2s (light), every 1s / 5×0.2s (bold)
X_LINE_PEN_004S = pg.mkPen(color="#333333", width=0.5)   # light grey — 0.04s lines
X_LINE_PEN_02S = pg.mkPen(color="#5D5D5D", width=0.7)   # light grey — 0.2s lines
X_LINE_PEN_1S  = pg.mkPen(color="#888888", width=1.2)   # bold white — 1s lines
 
# Y-axis (voltage): two tiers — every 0.1mV (light), every 0.5mV (bold)
Y_LINE_PEN_MINOR = pg.mkPen(color='#333333', width=0.5)   # light grey — 0.1mV lines
Y_LINE_PEN_MAJOR = pg.mkPen(color='#888888', width=0.7)   # bold white — 0.5mV lines
 
 
def _draw_ecg_grid(plot, x_max: float, y_range: tuple):
    '''
    Draw the ECG sweep grid onto `plot`.
 
    X-axis runs on a 0.2s base unit (LARGE_SQUARE_SEC), with every 5th line
    (1 second) drawn bold. Y-axis runs on the original 0.1mV/0.5mV tiers.
    The two axes intentionally use different base units now — X has moved
    to a coarser 0.2s/1s scheme rather than 0.04s/0.2s, per a deliberate
    simplification for on-screen readability.
 
    Lines are placed by INTEGER line-count, not by comparing floating-point
    positions against a modulo threshold — this guarantees every 5th line
    is bold by construction, with no possibility of float-drift misaligning
    which lines get which weight.
    '''
    y_min, y_max = y_range
 
    # ---- Vertical lines (time axis): 0.04s small grid, 0.2s large grid, bold every 1s ---- #
    n_x = int(round(x_max / SMALL_SQUARE_SEC)) + 1
    for i in range(n_x):
        x     = i * SMALL_SQUARE_SEC
       
        bold  = (i % 5 == 0)   # every 5th 0.04s line = 0.2s
        bold1 = (i % 25 == 0)   # every 5th 0.2s line = 1s

        # Select the pen hierarchy from most specific (1s) to least specific (0.04s)
        pen   = X_LINE_PEN_1S if bold1 else X_LINE_PEN_02S if bold else X_LINE_PEN_004S

        line  = pg.InfiniteLine(pos=x, angle=90, pen=pen)

        # Keep the 1s and 0.2s lines grouped ahead of the fine grid lines
        line.setZValue(-19 if bold else -20)
        plot.addItem(line)
 
    # ---- Horizontal lines (voltage axis): 0.1mV base, bold every 0.5mV ---- #
    n_y = int(round((y_max - y_min) / SMALL_SQUARE_MV)) + 1
    for i in range(n_y):
        y    = y_min + i * SMALL_SQUARE_MV
        bold = (i % 5 == 0)   # every 5th 0.1mV line = 0.5mV
        pen  = Y_LINE_PEN_MAJOR if bold else Y_LINE_PEN_MINOR
        line = pg.InfiniteLine(pos=y, angle=0, pen=pen)
        line.setZValue(-19 if bold else -20)
        plot.addItem(line)
 
 
# --------------------------------------------------------------------------- #
#  Setup                                                                      #
# --------------------------------------------------------------------------- #
 
def setup_live_plot(app, fs: float, rolling_window_sec: float = 6.0) -> dict:
    '''
    Initialise the PyQtGraph window, ECG sweep plot, and metrics panel.

    Returns a plot_state dict that is passed to every subsequent display call.
    All mutable display state lives here — nothing is stored as a global.
    '''
    win = pg.GraphicsLayoutWidget(show=True, title="ECG Continuous Sweep Monitor")
    # The ECG plot must be a WIDE, SHORT strip to show mm-accurate square
    # grid cells: at 10s width and 4mV height, true-scale squares require a
    # plot aspect of ~6.25:1 (width:height) — see SMALL_SQUARE_SEC/MV above.
    # A roughly-square window forces the aspect lock to expand the y-range
    # far beyond ±2mV to keep squares square, shrinking the visible grid to
    # a tiny strip surrounded by blank space. Sizing the window to match
    # this proportion up front keeps squares both correctly-scaled AND
    # clearly visible.
    win.resize(1900, 360)
    win.setWindowTitle("ECG Continuous Sweep Monitor")
    win.show()
    app.processEvents()
 
    # Column proportions: ECG trace takes 4x the width of the metrics panel
    win.ci.layout.setColumnStretchFactor(0, 4)
    win.ci.layout.setColumnStretchFactor(1, 1)
 
    # ---- Metrics panel (right column) ---- #
    metrics_layout = win.addLayout(row=0, col=1)
 
    metrics_layout.addLabel('HR', row=0, col=0, color='#888888', size='12pt')
    hr_value = metrics_layout.addLabel('--', row=1, col=0, color='#00ff00', size='42pt', bold=True)
    metrics_layout.addLabel('bpm', row=2, col=0, color='#888888', size='10pt')
 
    metrics_layout.addLabel('', row=3, col=0)  # spacer
 
    metrics_layout.addLabel('RMSSD', row=4, col=0, color='#888888', size='12pt')
    rmssd_value = metrics_layout.addLabel('--', row=5, col=0, color='#00aaff', size='32pt', bold=True)
    metrics_layout.addLabel('ms', row=6, col=0, color='#888888', size='10pt')
 
    metrics_layout.addLabel('', row=7, col=0)  # spacer
 
    afib_label = metrics_layout.addLabel('', row=8, col=0, color='#ff4444', size='16pt', bold=True)
 
    # ---- ECG plot (left column) ---- #
    plot = win.addPlot(row=0, col=0)
    plot.setYRange(-5.0, 5.0)
    plot.setXRange(0, rolling_window_sec)
    plot.setLabel('left', 'Voltage (mV)')
    plot.setLabel('bottom', 'Time (seconds)')
    plot.setMouseEnabled(x=False, y=False)
 
    # ---- Axis tick labels ---- #
    # Major labels only — small-square labels would clutter the axis just
    # like they do on real ECG paper, where only the large squares are
    # implicitly counted (5 small = 1 large = 0.2s; 5 large = 1s).
    x_labels = np.arange(0, rolling_window_sec + 1.0, 1.0)
    y_labels = np.arange(-5.0, 5.5, 0.5)
 
    plot.getAxis('bottom').setTicks([[(pos, f'{int(pos)}') for pos in x_labels]])
    plot.getAxis('left').setTicks([[(pos, f'{pos:.1f}') for pos in y_labels]])
 
        # ---- Lock aspect ratio so grid squares render as true squares ---- #
    # On real ECG paper, 1mm = 0.04s horizontally AND 1mm = 0.1mV vertically —
    # same physical unit, so squares are square regardless of paper size.
    # On screen, x is seconds and y is mV, which are different units with no
    # natural pixel relationship — without locking, a small square's pixel
    # width and height drift apart as the window is resized, producing
    # rectangles instead of squares. Locking the ratio enforces:
    #   (pixels per second) / (pixels per mV) = SMALL_SQUARE_MV / SMALL_SQUARE_SEC
    # which keeps every square square no matter the widget size.
    plot.setAspectLocked(True, ratio=SMALL_SQUARE_MV / SMALL_SQUARE_SEC)
 
    # ---- ECG-paper-style dual-weight grid ---- #
    _draw_ecg_grid(plot, rolling_window_sec, y_range=(-5.0, 5.0))
 
    window_samples = int(fs * rolling_window_sec)
 
    # ECG trace
    line_ecg = plot.plot(pen=pg.mkPen(color='#00ff88', width=1.5))
 
    # R-peak scatter markers
    scatter_r = pg.ScatterPlotItem(
        size=10,
        pen=pg.mkPen(None),
        brush=pg.mkBrush('#ff4444')
    )
    plot.addItem(scatter_r)
 
    # Write-cursor line
    cursor_line = plot.addLine(x=0, pen=pg.mkPen(color='#00ff88', width=1.5))
    cursor_line.setVisible(False)
 
    # Void gap: black region ahead of the cursor obscuring stale data.
    # zValue is set BELOW the grid (-19/-20) so the grid remains visible
    # within the gap — the gap should only blank the waveform trace (which
    # already happens naturally via NaN values in the sweep buffer), not
    # paint over the grid underneath it.
    gap_region = pg.LinearRegionItem(
        [0, 0], brush=pg.mkBrush('#000000'), movable=False, pen=pg.mkPen(None)
    )
    gap_region.setZValue(-25)
    plot.addItem(gap_region)
 
    # Wrap-around portion of the void gap (when it crosses the right edge)
    gap_region_wrap = pg.LinearRegionItem(
        [0, 0], brush=pg.mkBrush('#000000'), movable=False, pen=pg.mkPen(None)
    )
    gap_region_wrap.setZValue(-25)
    plot.addItem(gap_region_wrap)
 
    return {
        'win':                win,
        'plot':               plot,
        'line_ecg':           line_ecg,
        'scatter_r':          scatter_r,
        'cursor_line':        cursor_line,
        'gap_region':         gap_region,
        'gap_region_wrap':    gap_region_wrap,
        'rolling_window_sec': rolling_window_sec,
        'window_samples':     window_samples,
        'x_fixed':            np.arange(window_samples, dtype=float) / fs,
        'sweep_buffer':       np.full(window_samples, np.nan, dtype=float),
        'write_pos':          0,
        'void_gap_length':    60,
        'first_sweep_done':   False,
        'hr_value':           hr_value,
        'rmssd_value':        rmssd_value,
        'afib_label':         afib_label,
    }
 
 
# --------------------------------------------------------------------------- #
#  Buffer management                                                           #
# --------------------------------------------------------------------------- #
 
def append_plot_sample(plot_state: dict, sample: float):
    '''
    Write one sample into the circular sweep buffer and advance the cursor.
 
    A void gap of `void_gap_length` NaN values is maintained ahead of the
    write position so the display always has a clean blank region separating
    new data from the old data about to be overwritten.
    '''
    pos            = plot_state['write_pos']
    window_samples = plot_state['window_samples']
    void_length    = plot_state['void_gap_length']
 
    plot_state['sweep_buffer'][pos] = sample
 
    for i in range(1, void_length + 1):
        plot_state['sweep_buffer'][(pos + i) % window_samples] = np.nan
 
    old_pos = pos
    plot_state['write_pos'] = (pos + 1) % window_samples
 
    if plot_state['write_pos'] < old_pos and not plot_state['first_sweep_done']:
        plot_state['first_sweep_done'] = True
 
 
# --------------------------------------------------------------------------- #
#  Frame update                                                                #
# --------------------------------------------------------------------------- #
 
def update_live_plot(plot_state: dict,
                     fs: float,
                     total_samples: int,
                     r_peaks: List[int],
                     hr: Optional[int]             = None,
                     rmssd: Optional[float]         = None,
                     afib_status: Optional[str]     = None,
                     afib_confidence: Optional[str] = None):
    '''
    Render one display frame.
 
    All clinical values are computed upstream and passed in — this function
    only draws. Keeping rendering separate from computation means a display
    bug can never corrupt a clinical result.
 
    Args:
        plot_state:      State dict from setup_live_plot
        fs:              Sampling frequency (Hz)
        total_samples:   Total samples written so far (monotonically increasing)
        r_peaks:         Global R-peak indices (from processor.all_r_peaks)
        hr:              Heart rate in bpm, or None if not yet available
        rmssd:           RMSSD in ms, or None if not yet available
        afib_status:     'detected' | 'possible' | 'suspected' | 'normal' | None
        afib_confidence: 'high' | 'medium' | 'low' | None
    '''
    display_seg    = plot_state['sweep_buffer'].copy()
    window_samples = plot_state['window_samples']
 
    # ---- ECG trace ---- #
    plot_state['line_ecg'].setData(plot_state['x_fixed'], display_seg)
 
    # ---- Cursor ---- #
    cursor_x = plot_state['write_pos'] / fs
    plot_state['cursor_line'].setValue(cursor_x)
 
    # ---- Void gap ---- #
    gap_width = plot_state['void_gap_length'] / fs
    gap_end   = cursor_x + gap_width
    x_max     = plot_state['rolling_window_sec']
 
    if gap_end <= x_max:
        plot_state['gap_region'].setRegion((cursor_x, gap_end))
        plot_state['gap_region_wrap'].setRegion((0, 0))
    else:
        plot_state['gap_region'].setRegion((cursor_x, x_max))
        plot_state['gap_region_wrap'].setRegion((0, gap_end - x_max))
 
    # ---- Suppress markers during calibration ---- #
    if not plot_state['first_sweep_done']:
        plot_state['scatter_r'].setData([], [])
        plot_state['afib_label'].setText('CALIBRATING...', color='#888888', size='12pt', bold=False)
        return
 
    # ---- R-peak markers ---- #
    window_start_idx = total_samples - window_samples
    visible_peaks    = [p for p in r_peaks if p >= window_start_idx]
 
    r_x, r_y = [], []
    for p in visible_peaks[-15:]:
        buf_idx = p % window_samples
        val     = display_seg[buf_idx]
        if not np.isnan(val):
            r_x.append(buf_idx / fs)
            r_y.append(val)
 
    plot_state['scatter_r'].setData(r_x, r_y)
 
    # ---- HR ---- #
    if hr is not None:
        if 60 <= hr <= 100:
            hr_color = '#00ff00'
        elif 40 <= hr < 60 or 100 < hr <= 130:
            hr_color = '#ffff00'
        else:
            hr_color = '#ff4444'
        plot_state['hr_value'].setText(str(hr), color=hr_color, size='42pt', bold=True)
 
    # ---- RMSSD ---- #
    if rmssd is not None and not np.isnan(rmssd):
        plot_state['rmssd_value'].setText(f'{rmssd:.1f}', color='#00aaff', size='32pt', bold=True)
 
    # ---- AFib status ---- #
    if afib_status == 'detected':
        color = '#ff4444' if afib_confidence == 'high' else '#ffaa00'
        plot_state['afib_label'].setText('⚠ AFIB DETECTED', color=color, size='16pt', bold=True)
    elif afib_status == 'possible':
        plot_state['afib_label'].setText('⚠ POSSIBLE AFIB', color='#ffaa00', size='16pt', bold=True)
    elif afib_status == 'suspected':
        plot_state['afib_label'].setText('? AFIB SUSPECTED', color='#ffff00', size='14pt', bold=True)
    elif afib_status == 'normal':
        plot_state['afib_label'].setText('✓ NSR', color='#00ff00', size='14pt', bold=True)
 