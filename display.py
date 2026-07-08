# display.py - Live ECG Rendering
 
'''
Renders the live 12-lead ECG display and metrics panel.
 
LAYOUT
------
Four columns × three rows of per-lead sweep plots, with a full-width
Lead II rhythm strip underneath, and a metrics panel on the right:
 
    Col:  0       1       2       3       | 4 (metrics, rowspan=4)
    Row 0: I      aVR     V1      V4      |
    Row 1: II     aVL     V2      V5      |
    Row 2: III    aVF     V3      V6      |
    Row 3: [    Lead II rhythm strip    ] |
 
Each of the 12 cells shows 2.5 seconds of that lead's sweep.
The rhythm strip shows the full rolling_window_sec (default 10s).
All sweeps advance in lockstep — one sample per tick.
 
Missing leads (e.g. MIT-BIH 2-lead records) show an "N/A" placeholder
in the relevant cell instead of a trace.
 
WHAT THIS MODULE DOES NOT DO
-----------------------------
- Detect R-peaks                (detection.py)
- Compute HR or RMSSD           (metrics.py)
- Classify arrhythmias          (arrhythmia.py)
 
POSITION IN PIPELINE
--------------------
detection.py → processor.py → metrics.py → arrhythmia.py → display.py
                                                                ↑ YOU ARE HERE
'''
 
import numpy as np
import pyqtgraph as pg
from typing import List, Optional
 
 
# --------------------------------------------------------------------------- #
#  Layout constants                                                             #
# --------------------------------------------------------------------------- #
 
GRID_LAYOUT = [
    ['I',   'aVR', 'V1', 'V4'],
    ['II',  'aVL', 'V2', 'V5'],
    ['III', 'aVF', 'V3', 'V6'],
]
RHYTHM_LEAD     = 'II'
CELL_WINDOW_SEC = 2.5
Y_RANGE         = (-2.0, 2.0)
 
# Lead name aliases — maps database-specific names to standard grid names
_LEAD_ALIASES = {
    'MLII': 'II', 'MLI': 'I', 'MLIII': 'III',
    'AVR': 'aVR', 'AVL': 'aVL', 'AVF': 'aVF',
}
 
 
def _normalize_lead(name: str) -> str:
    '''Map database-specific lead names to standard 12-lead names.'''
    return _LEAD_ALIASES.get(name.upper(), name)
 
 
# --------------------------------------------------------------------------- #
#  ECG-paper-style grid                                                         #
# --------------------------------------------------------------------------- #
 
SMALL_SQUARE_SEC = 0.04
LARGE_SQUARE_SEC = 0.20
SMALL_SQUARE_MV  = 0.1
LARGE_SQUARE_MV  = 0.5
 
X_LINE_PEN_02S = pg.mkPen(color='#999999', width=0.5)
X_LINE_PEN_1S  = pg.mkPen(color='#ffffff', width=1.4)
Y_LINE_PEN_MINOR = pg.mkPen(color='#999999', width=0.5)
Y_LINE_PEN_MAJOR = pg.mkPen(color='#ffffff', width=1.4)
 
 
def _draw_ecg_grid(plot, x_max: float, y_range: tuple):
    '''Draw dual-weight ECG-paper grid. Integer line-count avoids float drift.'''
    y_min, y_max = y_range
 
    n_x = int(round(x_max / LARGE_SQUARE_SEC)) + 1
    for i in range(n_x):
        x    = i * LARGE_SQUARE_SEC
        bold = (i % 5 == 0)
        pen  = X_LINE_PEN_1S if bold else X_LINE_PEN_02S
        line = pg.InfiniteLine(pos=x, angle=90, pen=pen)
        line.setZValue(-19 if bold else -20)
        plot.addItem(line)
 
    n_y = int(round((y_max - y_min) / SMALL_SQUARE_MV)) + 1
    for i in range(n_y):
        y    = y_min + i * SMALL_SQUARE_MV
        bold = (i % 5 == 0)
        pen  = Y_LINE_PEN_MAJOR if bold else Y_LINE_PEN_MINOR
        line = pg.InfiniteLine(pos=y, angle=0, pen=pen)
        line.setZValue(-19 if bold else -20)
        plot.addItem(line)
 
 
# --------------------------------------------------------------------------- #
#  Cell helpers                                                                 #
# --------------------------------------------------------------------------- #
 
def _make_cell(win, row: int, col: int, lead_name: str, fs: float,
               available_leads: set, cell_window_sec: float) -> Optional[dict]:
    '''
    Add one ECG cell to the layout grid.
 
    Returns a cell-state dict for active leads, or None for missing leads
    (which still get a labelled placeholder plot).
    '''
    plot = win.addPlot(row=row, col=col)
    plot.setMouseEnabled(x=False, y=False)
    plot.setYRange(*Y_RANGE)
    plot.setXRange(0, cell_window_sec)
    plot.hideAxis('bottom')
    plot.hideAxis('left')
    plot.setContentsMargins(0, 0, 0, 0)
 
    # Lead label — top-left corner
    label = pg.TextItem(lead_name, color='#aaaaaa', anchor=(0, 1))
    label.setPos(0.02, Y_RANGE[1])
    plot.addItem(label)
 
    if lead_name not in available_leads:
        na = pg.TextItem('N/A', color='#444444', anchor=(0.5, 0.5))
        na.setPos(cell_window_sec / 2.0, 0.0)
        plot.addItem(na)
        return None
 
    _draw_ecg_grid(plot, cell_window_sec, Y_RANGE)
    plot.setAspectLocked(True, ratio=SMALL_SQUARE_MV / SMALL_SQUARE_SEC)
 
    window_samples = int(fs * cell_window_sec)
    line = plot.plot(pen=pg.mkPen(color='#00ff88', width=1.0))
 
    gap = pg.LinearRegionItem(
        [0, 0], brush=pg.mkBrush('#000000'), movable=False, pen=pg.mkPen(None)
    )
    gap.setZValue(-25)
    plot.addItem(gap)
 
    gap_wrap = pg.LinearRegionItem(
        [0, 0], brush=pg.mkBrush('#000000'), movable=False, pen=pg.mkPen(None)
    )
    gap_wrap.setZValue(-25)
    plot.addItem(gap_wrap)
 
    return {
        'plot':            plot,
        'line':            line,
        'gap_region':      gap,
        'gap_region_wrap': gap_wrap,
        'sweep_buffer':    np.full(window_samples, np.nan, dtype=float),
        'write_pos':       0,
        'window_samples':  window_samples,
        'x_fixed':         np.arange(window_samples, dtype=float) / fs,
        'void_gap_length': 20,
        'first_sweep_done': False,
        'cell_window_sec': cell_window_sec,
    }
 
 
def _write_sample(cell: dict, sample: float):
    '''Write one sample into a cell's circular sweep buffer.'''
    pos    = cell['write_pos']
    n      = cell['window_samples']
    void   = cell['void_gap_length']
 
    cell['sweep_buffer'][pos] = sample
    for i in range(1, void + 1):
        cell['sweep_buffer'][(pos + i) % n] = np.nan
 
    old = pos
    cell['write_pos'] = (pos + 1) % n
    if cell['write_pos'] < old and not cell['first_sweep_done']:
        cell['first_sweep_done'] = True
 
 
def _update_cell(cell: dict, fs: float):
    '''Redraw one cell's trace and void gap.'''
    buf = cell['sweep_buffer'].copy()
    cell['line'].setData(cell['x_fixed'], buf)
 
    cursor_x  = cell['write_pos'] / fs
    gap_width = cell['void_gap_length'] / fs
    gap_end   = cursor_x + gap_width
    x_max     = cell['cell_window_sec']
 
    if gap_end <= x_max:
        cell['gap_region'].setRegion((cursor_x, gap_end))
        cell['gap_region_wrap'].setRegion((0, 0))
    else:
        cell['gap_region'].setRegion((cursor_x, x_max))
        cell['gap_region_wrap'].setRegion((0, gap_end - x_max))
 
 
# --------------------------------------------------------------------------- #
#  Setup                                                                        #
# --------------------------------------------------------------------------- #
 
def setup_live_plot(app, fs: float, lead_names: list,
                    rolling_window_sec: float = 10.0) -> dict:
    '''
    Initialise the 12-lead sweep display window.
 
    Args:
        app:               QApplication instance.
        fs:                Sampling frequency in Hz.
        lead_names:        Lead names from the data source (raw, un-normalised).
        rolling_window_sec: Width of the rhythm strip in seconds.
 
    Returns:
        plot_state dict passed to every subsequent display call.
    '''
    # Normalise incoming lead names so 'MLII' maps to 'II' etc.
    normalised      = [_normalize_lead(n) for n in lead_names]
    available_leads = set(normalised)
    # lead_to_idx maps normalised lead name → index in sample_row
    lead_to_idx     = {_normalize_lead(n): i for i, n in enumerate(lead_names)}
 
    # Resolve rhythm lead
    rhythm_lead = RHYTHM_LEAD if RHYTHM_LEAD in available_leads else normalised[0]
 
    win = pg.GraphicsLayoutWidget(show=True, title='ECG Continuous Sweep Monitor')
    win.resize(1800, 700)
    win.setWindowTitle('ECG Continuous Sweep Monitor')
    win.setBackground('#000000')
    win.show()
    app.processEvents()
 
    # Stretch: ECG columns share space equally; metrics column is narrower
    for col in range(4):
        win.ci.layout.setColumnStretchFactor(col, 4)
    win.ci.layout.setColumnStretchFactor(4, 1)
 
    # ---- Metrics panel — right column, spans all 4 rows ---- #
    metrics_layout = win.addLayout(row=0, col=4, rowspan=4)
    metrics_layout.addLabel('HR', row=0, col=0, color='#888888', size='12pt')
    hr_value = metrics_layout.addLabel('--', row=1, col=0,
                                        color='#00ff00', size='42pt', bold=True)
    metrics_layout.addLabel('bpm', row=2, col=0, color='#888888', size='10pt')
    metrics_layout.addLabel('', row=3, col=0)
    metrics_layout.addLabel('RMSSD', row=4, col=0, color='#888888', size='12pt')
    rmssd_value = metrics_layout.addLabel('--', row=5, col=0,
                                           color='#00aaff', size='32pt', bold=True)
    metrics_layout.addLabel('ms', row=6, col=0, color='#888888', size='10pt')
    metrics_layout.addLabel('', row=7, col=0)
    afib_label = metrics_layout.addLabel('', row=8, col=0,
                                          color='#ff4444', size='14pt', bold=True)
 
    # ---- 12-lead grid (rows 0–2, cols 0–3) ---- #
    cells = {}
    for row_idx, row_leads in enumerate(GRID_LAYOUT):
        for col_idx, lead_name in enumerate(row_leads):
            cell = _make_cell(
                win, row_idx, col_idx, lead_name,
                fs, available_leads, CELL_WINDOW_SEC
            )
            cells[lead_name] = cell   # None if lead not present
 
    # ---- Rhythm strip (row 3, spanning cols 0–3) ---- #
    rhythm_plot = win.addPlot(row=3, col=0, colspan=4)
    rhythm_plot.setMouseEnabled(x=False, y=False)
    rhythm_plot.setYRange(*Y_RANGE)
    rhythm_plot.setXRange(0, rolling_window_sec)
    rhythm_plot.setLabel('bottom', 'Time (seconds)')
    rhythm_plot.hideAxis('left')
    rhythm_plot.setContentsMargins(0, 0, 0, 0)
 
    _draw_ecg_grid(rhythm_plot, rolling_window_sec, Y_RANGE)
    rhythm_plot.setAspectLocked(True, ratio=SMALL_SQUARE_MV / SMALL_SQUARE_SEC)
 
    # Rhythm lead label
    rlabel = pg.TextItem(f'{rhythm_lead}  (rhythm)', color='#aaaaaa', anchor=(0, 1))
    rlabel.setPos(0.1, Y_RANGE[1])
    rhythm_plot.addItem(rlabel)
 
    x_labels = np.arange(0, rolling_window_sec + 1.0, 1.0)
    rhythm_plot.getAxis('bottom').setTicks(
        [[(pos, f'{int(pos)}') for pos in x_labels]]
    )
 
    rhythm_samples = int(fs * rolling_window_sec)
    rhythm_line    = rhythm_plot.plot(pen=pg.mkPen(color='#00ff88', width=1.5))
 
    scatter_r = pg.ScatterPlotItem(
        size=10, pen=pg.mkPen(None), brush=pg.mkBrush('#ff4444')
    )
    rhythm_plot.addItem(scatter_r)
 
    cursor_line = rhythm_plot.addLine(
        x=0, pen=pg.mkPen(color='#00aaff', width=2)
    )
    cursor_line.setVisible(True)
 
    rhythm_gap = pg.LinearRegionItem(
        [0, 0], brush=pg.mkBrush('#000000'), movable=False, pen=pg.mkPen(None)
    )
    rhythm_gap.setZValue(-25)
    rhythm_plot.addItem(rhythm_gap)
 
    rhythm_gap_wrap = pg.LinearRegionItem(
        [0, 0], brush=pg.mkBrush('#000000'), movable=False, pen=pg.mkPen(None)
    )
    rhythm_gap_wrap.setZValue(-25)
    rhythm_plot.addItem(rhythm_gap_wrap)
 
    rhythm_state = {
        'plot':            rhythm_plot,
        'line':            rhythm_line,
        'scatter_r':       scatter_r,
        'cursor_line':     cursor_line,
        'gap_region':      rhythm_gap,
        'gap_region_wrap': rhythm_gap_wrap,
        'sweep_buffer':    np.full(rhythm_samples, np.nan, dtype=float),
        'write_pos':       0,
        'window_samples':  rhythm_samples,
        'x_fixed':         np.arange(rhythm_samples, dtype=float) / fs,
        'void_gap_length': 80,
        'first_sweep_done': False,
        'cell_window_sec': rolling_window_sec,
    }
 
    return {
        'win':              win,
        'cells':            cells,
        'rhythm':           rhythm_state,
        'available_leads':  available_leads,
        'lead_to_idx':      lead_to_idx,
        'rhythm_lead':      rhythm_lead,
        'rolling_window_sec': rolling_window_sec,
        'first_sweep_done': False,
        'hr_value':         hr_value,
        'rmssd_value':      rmssd_value,
        'afib_label':       afib_label,
        'fs':               fs,
    }
 
 
# --------------------------------------------------------------------------- #
#  Buffer management                                                            #
# --------------------------------------------------------------------------- #
 
def append_plot_sample(plot_state: dict, sample_row: np.ndarray):
    '''
    Write one sample row into all active cell buffers and the rhythm buffer.
 
    Args:
        plot_state:  State dict from setup_live_plot.
        sample_row:  Shape (n_leads,) — simultaneous voltages for all leads.
    '''
    lead_to_idx = plot_state['lead_to_idx']
 
    # Write to each active grid cell
    for lead_name, cell in plot_state['cells'].items():
        if cell is None:
            continue
        if lead_name not in lead_to_idx:
            continue
        _write_sample(cell, float(sample_row[lead_to_idx[lead_name]]))
 
    # Write to rhythm strip
    rhythm_lead = plot_state['rhythm_lead']
    if rhythm_lead in lead_to_idx:
        rhythm = plot_state['rhythm']
        _write_sample(rhythm, float(sample_row[lead_to_idx[rhythm_lead]]))
        if rhythm['first_sweep_done'] and not plot_state['first_sweep_done']:
            plot_state['first_sweep_done'] = True
 
 
# --------------------------------------------------------------------------- #
#  Frame update                                                                 #
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
    Render one display frame — updates all 12 cells and the rhythm strip.
 
    All clinical values are pre-computed upstream and passed in.
    This function only draws.
 
    Args:
        plot_state:      State dict from setup_live_plot.
        fs:              Sampling frequency in Hz.
        total_samples:   Total samples written so far (monotonically increasing).
        r_peaks:         Global R-peak indices (from processor.all_r_peaks).
        hr:              Heart rate in bpm, or None.
        rmssd:           RMSSD in ms, or None.
        afib_status:     'detected' | 'possible' | 'suspected' | 'normal' | None
        afib_confidence: 'high' | 'medium' | 'low' | None
    '''
    # ---- Update all 12 grid cells ---- #
    for cell in plot_state['cells'].values():
        if cell is not None:
            _update_cell(cell, fs)
 
    # ---- Rhythm strip ---- #
    rhythm         = plot_state['rhythm']
    rhythm_buf     = rhythm['sweep_buffer'].copy()
    rhythm_samples = rhythm['window_samples']
 
    rhythm['line'].setData(rhythm['x_fixed'], rhythm_buf)
 
    cursor_x  = rhythm['write_pos'] / fs
    gap_width = rhythm['void_gap_length'] / fs
    gap_end   = cursor_x + gap_width
    x_max     = plot_state['rolling_window_sec']
 
    rhythm['cursor_line'].setValue(cursor_x)
 
    if gap_end <= x_max:
        rhythm['gap_region'].setRegion((cursor_x, gap_end))
        rhythm['gap_region_wrap'].setRegion((0, 0))
    else:
        rhythm['gap_region'].setRegion((cursor_x, x_max))
        rhythm['gap_region_wrap'].setRegion((0, gap_end - x_max))
 
    # ---- Suppress markers before first full sweep ---- #
    if not plot_state['first_sweep_done']:
        rhythm['scatter_r'].setData([], [])
        plot_state['afib_label'].setText(
            'CALIBRATING...', color='#888888', size='12pt', bold=False
        )
        return
 
    # ---- R-peak markers on rhythm strip only ---- #
    window_start = total_samples - rhythm_samples
    visible      = [p for p in r_peaks if p >= window_start]
 
    r_x, r_y = [], []
    for p in visible[-15:]:
        buf_idx = p % rhythm_samples
        val     = rhythm_buf[buf_idx]
        if not np.isnan(val):
            r_x.append(buf_idx / fs)
            r_y.append(val)
 
    rhythm['scatter_r'].setData(r_x, r_y)
 
    # ---- HR ---- #
    if hr is not None:
        if 60 <= hr <= 100:
            hr_color = '#00ff00'
        elif 40 <= hr < 60 or 100 < hr <= 130:
            hr_color = '#ffff00'
        else:
            hr_color = '#ff4444'
        plot_state['hr_value'].setText(
            str(hr), color=hr_color, size='42pt', bold=True
        )
 
    # ---- RMSSD ---- #
    if rmssd is not None and not np.isnan(rmssd):
        plot_state['rmssd_value'].setText(
            f'{rmssd:.1f}', color='#00aaff', size='32pt', bold=True
        )
 
    # ---- AFib status ---- #
    if afib_status == 'detected':
        color = '#ff4444' if afib_confidence == 'high' else '#ffaa00'
        plot_state['afib_label'].setText(
            '⚠ AFIB DETECTED', color=color, size='14pt', bold=True
        )
    elif afib_status == 'possible':
        plot_state['afib_label'].setText(
            '⚠ POSSIBLE AFIB', color='#ffaa00', size='14pt', bold=True
        )
    elif afib_status == 'suspected':
        plot_state['afib_label'].setText(
            '? AFIB SUSPECTED', color='#ffff00', size='12pt', bold=True
        )
    elif afib_status == 'normal':
        plot_state['afib_label'].setText(
            '✓ NSR', color='#00ff00', size='14pt', bold=True
        )
 