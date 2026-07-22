# display.py - Live ECG Rendering
 
'''
Renders the live 12-lead ECG display as four column groups plus a rhythm
strip, ALL on one shared PyQtGraph PlotItem — one continuous grid, no seams
anywhere (not between columns, not between the columns and the rhythm
strip).
 
LAYOUT (all one shared canvas, one grid)
-----------------------------------------
    Col 0      Col 1      Col 2      Col 3      | Metrics
    I          aVR        V1         V4         |
    II         aVL        V2         V5         | HR
    III        aVF        V3         V6         | RMSSD
    ──────────── Lead II rhythm strip ────────── | AFib
 
Each column occupies its own x-slice of the canvas:
    [col_idx * CELL_WINDOW_SEC, (col_idx+1) * CELL_WINDOW_SEC)
and sweeps independently (own write_pos, own void gap).
 
The rhythm strip occupies the FULL x-width of the canvas (it is not
sliced — it shows a longer, continuous window) and sits in its own
y-band below the columns. It also sweeps independently.
 
IMPORTANT CONSTRAINT
---------------------
rolling_window_sec MUST equal len(COLUMNS) * CELL_WINDOW_SEC for the
rhythm strip's x-axis to line up with the columns' combined x-axis on the
shared canvas. This is asserted in setup_live_plot().
 
WHY SPAN IS USED ON GAP REGIONS / CURSOR
------------------------------------------
A LinearRegionItem / InfiniteLine defaults to spanning the FULL height of
its parent plot. Since columns and the rhythm strip now share one plot,
a naive gap region would blank across every row it's not meant to touch
(e.g. a column's void gap bleeding down into the rhythm strip at the same
x-position). Each region is restricted to its own row-band using the
`span=(y0_frac, y1_frac)` parameter (fractions of the plot's total
y-range), so it only ever blanks its own row(s).
 
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
 
# 4 columns, each with 3 leads stacked top to bottom
COLUMNS = [
    ['I',   'II',  'III'],
    ['aVR', 'aVL', 'aVF'],
    ['V1',  'V2',  'V3' ],
    ['V4',  'V5',  'V6' ],
]
 
RHYTHM_LEAD      = 'II'
CELL_WINDOW_SEC  = 2.5    # seconds visible in each column cell
TRACE_OFFSET_MV  = 3.0    # vertical separation between traces in a column
TRACE_HALF_MV    = 1.0    # ± amplitude each trace is allowed to occupy
 
N_ROWS = 3   # leads per column
# Y-range for the column section of the shared canvas
_COL_TOP_Y    =  (N_ROWS - 1) * TRACE_OFFSET_MV + TRACE_HALF_MV + 0.3
_COL_BOTTOM_Y = -TRACE_HALF_MV - 0.3
 
# Y-layout for the rhythm-strip section, stacked below the columns
RHYTHM_HALF_MV      = 1.0   # amplitude the rhythm trace is allowed to occupy (was -2..2)
_RHYTHM_SECTION_GAP = 0.6   # visual breathing room between columns and rhythm strip
_RHYTHM_TOP_Y        = _COL_BOTTOM_Y - _RHYTHM_SECTION_GAP
_RHYTHM_BASE_Y        = _RHYTHM_TOP_Y - RHYTHM_HALF_MV        # rhythm trace centreline
_RHYTHM_BOTTOM_Y      = _RHYTHM_BASE_Y - RHYTHM_HALF_MV - 0.3
 
# Combined canvas y-range (used for the single shared grid + span fractions)
_CANVAS_TOP_Y    = _COL_TOP_Y
_CANVAS_BOTTOM_Y = _RHYTHM_BOTTOM_Y
_CANVAS_Y_SPAN    = _CANVAS_TOP_Y - _CANVAS_BOTTOM_Y
 
# Lead name aliases
_LEAD_ALIASES = {
    'MLII': 'II', 'MLI': 'I', 'MLIII': 'III',
    'AVR': 'aVR', 'AVL': 'aVL', 'AVF': 'aVF',
}
 
 
def _normalize_lead(name: str) -> str:
    return _LEAD_ALIASES.get(name.upper(), name)
 
 
def _row_baseline(row_idx: int) -> float:
    '''Y-coordinate of the centreline for row_idx (0=top) within a column.'''
    return (N_ROWS - 1 - row_idx) * TRACE_OFFSET_MV
 
 
def _y_to_span_frac(y0: float, y1: float) -> tuple:
    '''
    Convert an absolute (y0, y1) band on the shared canvas into the
    (0-1, 0-1) fraction-of-plot-height format that LinearRegionItem /
    InfiniteLine's `span` parameter expects. Fractions are measured from
    the BOTTOM of the canvas (span convention), so y0 should be the lower
    bound and y1 the upper bound.
    '''
    lo = (y0 - _CANVAS_BOTTOM_Y) / _CANVAS_Y_SPAN
    hi = (y1 - _CANVAS_BOTTOM_Y) / _CANVAS_Y_SPAN
    return (max(0.0, lo), min(1.0, hi))
 
 
# Precomputed span fractions for the two row-bands
_COL_SPAN_FRAC    = _y_to_span_frac(_COL_BOTTOM_Y, _COL_TOP_Y)
_RHYTHM_SPAN_FRAC = _y_to_span_frac(_CANVAS_BOTTOM_Y, _RHYTHM_TOP_Y)
 
 
# --------------------------------------------------------------------------- #
#  ECG-paper-style grid                                                         #
# --------------------------------------------------------------------------- #
 
LARGE_SQUARE_SEC = 0.20
SMALL_SQUARE_SEC = 0.04
SMALL_SQUARE_MV  = 0.1
 
X_LINE_PEN_004S  = pg.mkPen(color='#555555', width=0.4)
X_LINE_PEN_02S   = pg.mkPen(color="#888888", width=0.6)
X_LINE_PEN_1S    = pg.mkPen(color="#888888", width=1.0)
X_LINE_PEN_25S   = pg.mkPen(color="#888888", width=1.5)
Y_LINE_PEN_MINOR = pg.mkPen(color='#555555', width=0.4)
Y_LINE_PEN_MAJOR = pg.mkPen(color='#888888', width=0.6)
 
def _draw_ecg_grid(plot, x_max: float, y_min: float, y_max: float):
    '''Dual-weight ECG-paper grid. Integer line-count avoids float drift.'''
    n_x = int(round(x_max / SMALL_SQUARE_SEC)) + 1
    for i in range(n_x):
        x    = i * SMALL_SQUARE_SEC
        
        pen = X_LINE_PEN_25S if (i % 62.5 == 0) else (X_LINE_PEN_1S if (i % 25 == 0) else (X_LINE_PEN_02S if (i % 5 == 0) else X_LINE_PEN_004S))
        
        line = pg.InfiniteLine(pos=x, angle=90, pen=pen)
        line.setZValue(-20)
        plot.addItem(line)
 
    n_y = int(round((y_max - y_min) / SMALL_SQUARE_MV)) + 1
    for i in range(n_y):
        y    = y_min + i * SMALL_SQUARE_MV
        bold = (i % 5 == 0)
        line = pg.InfiniteLine(pos=y, angle=0,
                                pen=Y_LINE_PEN_MAJOR if bold else Y_LINE_PEN_MINOR)
        line.setZValue(-20)
        plot.addItem(line)
 
 
# --------------------------------------------------------------------------- #
#  Column trace builder (adds traces to the SHARED plot, doesn't create one)   #
# --------------------------------------------------------------------------- #
 
def _add_column_traces(plot, col_idx: int, lead_names_in_col: list,
                        fs: float, available: set) -> dict:
    '''
    Add one column's worth of traces (up to 3 vertically-offset leads) onto
    the shared canvas plot. Each column occupies its own x-slice:
    [col_idx * CELL_WINDOW_SEC, (col_idx+1) * CELL_WINDOW_SEC).
 
    Sweep/write logic (write_pos, sweep_buffers, void gap, wraparound) is
    fully local and unchanged from the single-column-plot version — only
    the x-offset (baked into x_fixed here) and the gap region's `span`
    (restricted to the column row-band) are new.
    '''
    cell_samples = int(fs * CELL_WINDOW_SEC)
    x_offset     = col_idx * CELL_WINDOW_SEC
    x_fixed      = np.arange(cell_samples, dtype=float) / fs + x_offset
 
    # Void gap — shared across all traces in this column, restricted to
    # this row-band only so it never blanks the rhythm strip below it.
    gap = pg.LinearRegionItem(
        [0, 0], brush=pg.mkBrush('#000000'), movable=False,
        pen=pg.mkPen(None), span=_COL_SPAN_FRAC
    )
    gap.setZValue(-25)
    plot.addItem(gap)
 
    gap_wrap = pg.LinearRegionItem(
        [0, 0], brush=pg.mkBrush('#000000'), movable=False,
        pen=pg.mkPen(None), span=_COL_SPAN_FRAC
    )
    gap_wrap.setZValue(-25)
    plot.addItem(gap_wrap)
 
    traces        = {}   # lead_name → PlotDataItem
    sweep_buffers = {}   # lead_name → np.ndarray
    baselines     = {}   # lead_name → float
 
    for row_idx, lead_name in enumerate(lead_names_in_col):
        base = _row_baseline(row_idx)
        baselines[lead_name] = base
 
        # Lead label — offset into this column's x-slice
        lbl = pg.TextItem(lead_name, color="#00ff88", anchor=(0, 1))
        lbl.setPos(x_offset + 0.02, base + TRACE_HALF_MV)
        plot.addItem(lbl)
 
        sweep_buffers[lead_name] = np.full(cell_samples, np.nan, dtype=float)
 
        if lead_name in available:
            line = plot.plot(pen=pg.mkPen(color='#00ff88', width=1.0))
            traces[lead_name] = line
        else:
            # N/A placeholder — offset into this column's x-slice
            na = pg.TextItem('N/A', color='#444444', anchor=(0.5, 0.5))
            na.setPos(x_offset + CELL_WINDOW_SEC / 2.0, base)
            plot.addItem(na)
 
    return {
        'plot':            plot,          # shared plot, kept for reference
        'traces':          traces,
        'sweep_buffers':   sweep_buffers,
        'baselines':       baselines,
        'gap':             gap,
        'gap_wrap':        gap_wrap,
        'cell_samples':    cell_samples,
        'x_fixed':         x_fixed,        # offset already baked in
        'x_offset':        x_offset,       # needed for gap region placement
        'void_gap_length': 20,
        'write_pos':       0,
        'first_sweep_done': False,
    }
 
 
# --------------------------------------------------------------------------- #
#  Setup                                                                        #
# --------------------------------------------------------------------------- #
 
def setup_live_plot(app, fs: float, lead_names: list,
                    rolling_window_sec: float = 10.0) -> dict:
    '''
    Initialise the 12-lead sweep display.
 
    Args:
        app:               QApplication instance.
        fs:                Sampling frequency in Hz.
        lead_names:        Raw lead names from the data source.
        rolling_window_sec: Width of the rhythm strip in seconds. MUST equal
                            len(COLUMNS) * CELL_WINDOW_SEC (default 10.0)
                            so the rhythm strip's x-axis aligns with the
                            columns' combined x-axis on the shared canvas.
 
    Returns:
        plot_state dict passed to every subsequent display call.
    '''
    n_cols_total = len(COLUMNS)
    canvas_x_max = n_cols_total * CELL_WINDOW_SEC
 
    assert abs(rolling_window_sec - canvas_x_max) < 1e-9, (
        f'rolling_window_sec ({rolling_window_sec}) must equal '
        f'len(COLUMNS) * CELL_WINDOW_SEC ({canvas_x_max}) for the rhythm '
        f'strip to align with the column grid on the shared canvas.'
    )
 
    normalised  = [_normalize_lead(n) for n in lead_names]
    available   = set(normalised)
    lead_to_idx = {_normalize_lead(n): i for i, n in enumerate(lead_names)}
    rhythm_lead = RHYTHM_LEAD if RHYTHM_LEAD in available else normalised[0]
 
    win = pg.GraphicsLayoutWidget(show=True, title='ECG Continuous Sweep Monitor')
    win.resize(1600, 900)
    win.setWindowTitle('ECG Continuous Sweep Monitor')
    win.setBackground('#000000')
    win.show()
    app.processEvents()
 
    # 1 shared ECG canvas column (spanning what used to be 4+1 stretch slots)
    # + 1 metrics column
    win.ci.layout.setColumnStretchFactor(0, 4)
    win.ci.layout.setColumnStretchFactor(4, 1)
 
    # ---- Metrics panel (col 4) ---- #
    metrics_layout = win.addLayout(row=0, col=4)
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
 
    # ---- Single shared canvas: columns + rhythm strip, one grid ---- #
    shared_plot = win.addPlot(row=0, col=0, colspan=4)
    shared_plot.setMouseEnabled(x=False, y=False)
    shared_plot.setXRange(0, canvas_x_max)
    shared_plot.setYRange(_CANVAS_BOTTOM_Y, _CANVAS_TOP_Y)
    shared_plot.hideAxis('left')
    shared_plot.showAxis('bottom')
    shared_plot.setLabel('bottom', 'Time (seconds)')
    shared_plot.setContentsMargins(1, 1, 1, 1)
 
    x_labels = np.arange(0, canvas_x_max + 1.0, 1.0)
    shared_plot.getAxis('bottom').setTicks(
        [[(pos, f'{int(pos)}') for pos in x_labels]]
    )
 
    # One grid across the FULL combined y-range — columns and rhythm strip
    # share every gridline, so there is no seam anywhere on the canvas.
    _draw_ecg_grid(shared_plot, canvas_x_max, _CANVAS_BOTTOM_Y, _CANVAS_TOP_Y)
 
    # Faint vertical separators between column groups (cosmetic only)
    for col_idx in range(1, n_cols_total):
        sep = pg.InfiniteLine(pos=col_idx * CELL_WINDOW_SEC, angle=90,
                               pen=pg.mkPen(color="#000000", width=0.6),
                               span=_COL_SPAN_FRAC)
        sep.setZValue(-15)
        shared_plot.addItem(sep)
 
    # Horizontal separator marking the boundary between columns and the
    # rhythm strip section (cosmetic only — the grid itself is continuous).
    section_line = pg.InfiniteLine(
        pos=(_COL_BOTTOM_Y + _RHYTHM_TOP_Y) / 2.0, angle=0,
        pen=pg.mkPen(color="#000000", width=0.6)
    )
    section_line.setZValue(-15)
    shared_plot.addItem(section_line)
 
    columns = []
    for col_idx, col_leads in enumerate(COLUMNS):
        col_state = _add_column_traces(shared_plot, col_idx, col_leads, fs, available)
        columns.append(col_state)
 
    # ---- Rhythm strip — same shared plot, own row-band, full-width sweep --- #
    rhythm_samples = int(fs * rolling_window_sec)
    x_fixed_rhythm = np.arange(rhythm_samples, dtype=float) / fs   # full width, no offset
 
    rlabel = pg.TextItem(f'{rhythm_lead}  (rhythm)', color='#00ff88', anchor=(0, 1))
    rlabel.setPos(0.1, _RHYTHM_TOP_Y - 0.05)
    shared_plot.addItem(rlabel)
 
    rhythm_line = shared_plot.plot(pen=pg.mkPen(color='#00ff88', width=1.5))
 
    scatter_r = pg.ScatterPlotItem(
        size=10, pen=pg.mkPen(None), brush=pg.mkBrush('#ff4444')
    )
    shared_plot.addItem(scatter_r)
 
    cursor_line = pg.InfiniteLine(
        pos=0, angle=90, pen=pg.mkPen(color="#000000", width=0.01),
        span=_RHYTHM_SPAN_FRAC
    )
    shared_plot.addItem(cursor_line)
 
    rhythm_gap = pg.LinearRegionItem(
        [0, 0], brush=pg.mkBrush('#000000'), movable=False,
        pen=pg.mkPen(None), span=_RHYTHM_SPAN_FRAC
    )
    rhythm_gap.setZValue(-25)
    shared_plot.addItem(rhythm_gap)
 
    rhythm_gap_wrap = pg.LinearRegionItem(
        [0, 0], brush=pg.mkBrush('#000000'), movable=False,
        pen=pg.mkPen(None), span=_RHYTHM_SPAN_FRAC
    )
    rhythm_gap_wrap.setZValue(-25)
    shared_plot.addItem(rhythm_gap_wrap)
 
    return {
        'win':                win,
        'shared_plot':        shared_plot,
        'columns':            columns,
        'rhythm_line':        rhythm_line,
        'rhythm_buffer':      np.full(rhythm_samples, np.nan, dtype=float),
        'rhythm_write_pos':   0,
        'rhythm_samples':     rhythm_samples,
        'x_fixed_rhythm':     x_fixed_rhythm,
        'rhythm_void_length': 80,
        'rhythm_first_done':  False,
        'scatter_r':          scatter_r,
        'cursor_line':        cursor_line,
        'rhythm_gap':         rhythm_gap,
        'rhythm_gap_wrap':    rhythm_gap_wrap,
        'rolling_window_sec': rolling_window_sec,
        'available':          available,
        'lead_to_idx':        lead_to_idx,
        'rhythm_lead':        rhythm_lead,
        'first_sweep_done':   False,
        'hr_value':           hr_value,
        'rmssd_value':        rmssd_value,
        'afib_label':         afib_label,
        'fs':                 fs,
    }
 
 
# --------------------------------------------------------------------------- #
#  Buffer management                                                            #
# --------------------------------------------------------------------------- #
 
def append_plot_sample(plot_state: dict, sample_row: np.ndarray):
    '''
    Write one sample row into all column sweep buffers and the rhythm buffer.
 
    Buffers still store RAW (un-offset) amplitude — the y-offset that
    places each row/strip in its band on the shared canvas is applied at
    render time in update_live_plot(), not here. This keeps the buffers
    reusable/inspectable in their natural units.
 
    Args:
        sample_row: Shape (n_leads,) — simultaneous voltages in mV.
    '''
    lead_to_idx = plot_state['lead_to_idx']
    available   = plot_state['available']
    rhythm_lead = plot_state['rhythm_lead']
 
    # ---- Write to each column ---- #
    for col_state in plot_state['columns']:
        pos  = col_state['write_pos']
        n    = col_state['cell_samples']
        void = col_state['void_gap_length']
 
        for lead_name, buf in col_state['sweep_buffers'].items():
            if lead_name not in available:
                continue
            idx = lead_to_idx.get(lead_name)
            if idx is None or idx >= len(sample_row):
                continue
            val  = float(sample_row[idx]) + col_state['baselines'][lead_name]
            buf[pos] = val
            for j in range(1, void + 1):
                buf[(pos + j) % n] = np.nan
 
        old = pos
        col_state['write_pos'] = (pos + 1) % n
        if col_state['write_pos'] < old and not col_state['first_sweep_done']:
            col_state['first_sweep_done'] = True
 
    # ---- Write to rhythm strip (raw, offset applied at render time) ---- #
    rpos  = plot_state['rhythm_write_pos']
    rn    = plot_state['rhythm_samples']
    rvoid = plot_state['rhythm_void_length']
    rbuf  = plot_state['rhythm_buffer']
 
    if rhythm_lead in lead_to_idx:
        idx = lead_to_idx[rhythm_lead]
        if idx < len(sample_row):
            rbuf[rpos] = float(sample_row[idx])
            for j in range(1, rvoid + 1):
                rbuf[(rpos + j) % rn] = np.nan
 
    old_rpos = rpos
    plot_state['rhythm_write_pos'] = (rpos + 1) % rn
    if (plot_state['rhythm_write_pos'] < old_rpos
            and not plot_state['rhythm_first_done']):
        plot_state['rhythm_first_done'] = True
        plot_state['first_sweep_done']  = True
 
 
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
    Render one display frame — updates the shared canvas (columns + rhythm
    strip together) in one pass.
 
    All clinical values are pre-computed upstream and passed in.
    '''
    # ---- Update each column ---- #
    for col_state in plot_state['columns']:
        for lead_name, line in col_state['traces'].items():
            line.setData(col_state['x_fixed'],
                         col_state['sweep_buffers'][lead_name])
 
        # Void gap per column — local cursor math unchanged; x_offset is
        # added only when placing the gap on the shared canvas. Vertical
        # extent is already fixed at construction time via `span`.
        x_off     = col_state['x_offset']
        cursor_x  = col_state['write_pos'] / fs
        gap_width = col_state['void_gap_length'] / fs
        gap_end   = cursor_x + gap_width
        x_max     = CELL_WINDOW_SEC
 
        if gap_end <= x_max:
            col_state['gap'].setRegion((x_off + cursor_x, x_off + gap_end))
            col_state['gap_wrap'].setRegion((x_off, x_off))
        else:
            col_state['gap'].setRegion((x_off + cursor_x, x_off + x_max))
            col_state['gap_wrap'].setRegion((x_off, x_off + (gap_end - x_max)))
 
    # ---- Rhythm strip — y-offset applied here at render time ---- #
    rhythm_buf = plot_state['rhythm_buffer'] + _RHYTHM_BASE_Y
    plot_state['rhythm_line'].setData(plot_state['x_fixed_rhythm'], rhythm_buf)
 
    cursor_x  = plot_state['rhythm_write_pos'] / fs
    gap_width = plot_state['rhythm_void_length'] / fs
    gap_end   = cursor_x + gap_width
    x_max     = plot_state['rolling_window_sec']
 
    plot_state['cursor_line'].setValue(cursor_x)
 
    if gap_end <= x_max:
        plot_state['rhythm_gap'].setRegion((cursor_x, gap_end))
        plot_state['rhythm_gap_wrap'].setRegion((0, 0))
    else:
        plot_state['rhythm_gap'].setRegion((cursor_x, x_max))
        plot_state['rhythm_gap_wrap'].setRegion((0, gap_end - x_max))
 
    # ---- Suppress markers during calibration ---- #
    if not plot_state['first_sweep_done']:
        plot_state['scatter_r'].setData([], [])
        plot_state['afib_label'].setText(
            'CALIBRATING...', color='#888888', size='12pt', bold=False
        )
        return
 
    # ---- R-peak markers on rhythm strip only ---- #
    rhythm_samples = plot_state['rhythm_samples']
    window_start   = total_samples - rhythm_samples
    visible        = [p for p in r_peaks if p >= window_start]
 
    r_x, r_y = [], []
    snap_radius = int(0.040 * fs)  # ±40ms snap window
    for p in visible[-15:]:
        buf_idx = p % rhythm_samples
        lo = max(0, buf_idx - snap_radius)
        hi = min(rhythm_samples, buf_idx + snap_radius + 1)
        window = rhythm_buf[lo:hi]
        if np.all(np.isnan(window)):
            continue
        local_max = lo + int(np.nanargmax(window))
        val = rhythm_buf[local_max]
        if not np.isnan(val):
            r_x.append(local_max / fs)
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
 