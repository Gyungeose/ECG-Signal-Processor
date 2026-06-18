# ECG Signal Processor

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)
![PyQt6](https://img.shields.io/badge/GUI-PyQt6-41CD52?style=flat&logo=qt&logoColor=white)
![PyQtGraph](https://img.shields.io/badge/Visualisation-PyQtGraph-FF6B35?style=flat)
![NumPy](https://img.shields.io/badge/Numerics-NumPy-013243?style=flat&logo=numpy&logoColor=white)
![SciPy](https://img.shields.io/badge/DSP-SciPy-8CAAE6?style=flat&logo=scipy&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat)
![Status](https://img.shields.io/badge/Status-Active_Development-blue?style=flat)
![Database](https://img.shields.io/badge/Validated_On-MIT--BIH_Arrhythmia_Database-red?style=flat)
![PhysioNet](https://img.shields.io/badge/Data-PhysioNet-005A9C?style=flat)

A real-time ECG signal processing and arrhythmia detection system built in Python. The pipeline implements a dual-band Butterworth filter architecture, a full Pan-Tompkins QRS detector with dual adaptive thresholds and searchback logic, continuous RMSSD-based heart rate variability analysis, and a hysteresis-gated atrial fibrillation detector — rendered live in a clinical sweep display at 25 mm/s via PyQt6 and PyQtGraph.

The system is designed explicitly as a **clinical decision-support tool**: it surfaces arrhythmic signatures and autonomic indicators to assist practitioners, not to replace clinical judgement.

---

## Rationale

Cardiac events — arrhythmias, autonomic dysfunction, elevated stroke risk — often produce detectable signatures in ECG morphology and heart rate variability **before** a patient becomes symptomatic. Standard clinical workflows are largely reactive: a 12-lead ECG is reviewed after symptoms appear, rather than continuously monitored for early pattern drift.

This project addresses that gap. By combining rigorous DSP methodology with a real-time streaming architecture, validated HRV analytics, and prospective arrhythmia detection, the goal is a system that can:

- Firstly, **prospectively detect** arrhythmic and autonomic patterns from continuous ECG streams,
- then **flag early warning indicators** — RR interval irregularity, elevated HRV variability, anomalous QRS morphology — in real time,
- and **present findings clearly** to clinical staff without requiring DSP expertise to operate.

The long-term vision is a tool deployable at the bedside or integrated with ambulatory ECG devices, capable of surfacing cardiac risk indicators before a clinical event occurs.

---

## Module Architecture

The codebase is organised into discrete, single-responsibility modules:

```
ecg_signal_processor/
│
├── filters.py          # Butterworth filter design and stateful SOS application
├── buffer.py           # StreamingBuffer — sliding window with configurable overlap
├── metrics.py          # RMSSD, CV, mean RR, heart rate computation
├── detection.py        # Pan-Tompkins QRS detection and peak deduplication
├── arrhythmia.py       # Hysteresis-gated AFib detector
├── processor.py        # Central pipeline — coordinates all DSP stages per chunk
├── data_sources.py     # MIT-BIH, CSV, serial, network, and synthetic ingestion
├── display.py          # PyQt6/PyQtGraph clinical sweep display at 25 mm/s
└── main.py             # Entry point — initialises pipeline and launches UI
```

Each module has a single clear responsibility and can be tested, replaced, or extended independently. The modular structure reflects the separation of concerns inherent in the pipeline itself: signal conditioning, feature extraction, clinical analytics, and presentation are distinct stages.

---

## Pipeline Architecture

```
Raw ECG Signal
      │
      ▼
┌─────────────────────┐
│   Data Ingestion     │  MIT-BIH / CSV / Serial / Network / Synthetic
│   (data_sources.py)  │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Streaming Buffer    │  Sliding window: 3-sec chunks, 1-sec overlap
│  (buffer.py)         │  Prevents edge artifacts at chunk boundaries
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  DC Offset Removal   │  Centres signal at 0 mV before filtering
└────────┬────────────┘
         │
         ├─────────────────────────────────────┐
         ▼                                     ▼
┌─────────────────────┐            ┌──────────────────────┐
│  Detection Filter    │            │   Display Filter      │
│  Butterworth 5–15 Hz │            │   Butterworth 0.5–40Hz│
│  (filters.py)        │            │   (filters.py)        │
└────────┬────────────┘            └──────────────────────┘
         │                                     │
         ▼                                     ▼
┌─────────────────────┐            ┌──────────────────────┐
│  Pan-Tompkins QRS    │            │  Clinical Sweep       │
│  Detection           │            │  Display at 25 mm/s   │
│  (detection.py)      │            │  (display.py)         │
│                      │            │                       │
│  · Differentiation   │            │  · Full PQRST         │
│  · Squaring          │            │    morphology         │
│  · MWI (150 ms)      │            │  · R-peak markers     │
│  · Dual adaptive     │            │  · Live HRV readout   │
│    thresholds        │            │  · AFib alert panel   │
│  · 250 ms refractory │            └──────────────────────┘
│  · Searchback logic  │
│  · First-sweep guard │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Peak Deduplication  │  Global index conversion, cross-chunk suppression
│  (detection.py)      │  R-peak marker offset correction (±15 sample search)
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  HRV Analytics       │  RMSSD, Coefficient of Variation, mean RR, HR
│  (metrics.py)        │  Validated autonomic and arrhythmia risk markers
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  AFib Detection      │  Hysteresis-gated detector
│  (arrhythmia.py)     │  CV > 15% ∧ RMSSD > 50 ms
│                      │  3 consecutive positive detections required
└────────┬────────────┘
         │
         ▼
   Clinical Alerts + HRV Metrics + Annotated Sweep Display
```

---

## Clinical Significance

### Why Rigorous Signal Conditioning Matters

Raw ECG signals are routinely degraded by noise before any clinical interpretation occurs:

- **Electromyographic (EMG) interference** from nearby muscle activity contaminates the signal baseline
- **Baseline wander** caused by respiratory movement shifts the isoelectric line, distorting ST-segment morphology
- **Powerline interference** (60 Hz in North America, 50 Hz internationally) can mask or mimic arrhythmic activity

Without filtering, automated rhythm analysis produces false positives and false negatives with obvious patient safety implications. This project partially reproduces the signal conditioning standards used in clinical-grade ECG devices.

### Heart Rate Variability as a Prospective Biomarker

RMSSD — Root Mean Square of Successive Differences of RR intervals — is a validated, non-invasive measure of autonomic nervous system function and cardiac risk:

| Metric | Clinical Interpretation |
|--------|------------------------|
| Low RMSSD | Reduced vagal tone; associated with increased risk of sudden cardiac death |
| Elevated RMSSD variability | May indicate autonomic instability or evolving arrhythmia |
| Irregular RR series (high CV) | Primary diagnostic signature of atrial fibrillation |

RMSSD is the primary HRV metric recommended by the Task Force of the European Society of Cardiology for short-term recordings. By computing it continuously in a streaming context, the system can surface autonomic deterioration prospectively, before the patient or clinician is aware of a change.

### Atrial Fibrillation Detection

AFib is the most common sustained cardiac arrhythmia and the leading cardioembolic cause of ischaemic stroke. It is characterised in the RR interval domain by chaotic AV nodal conduction producing an irregularly irregular rhythm — detectable without morphological analysis, and therefore within reach of a single-lead streaming pipeline.

The detector uses a hysteresis gate requiring three consecutive positive detections before issuing an alert. This design suppresses transient false positives from motion artifact or ectopic beats without delaying detection of sustained AFib episodes.

---

## The Physics

Standard ECG signals occupy a narrow physiological band:

| Component | Frequency Band | Handling |
|-----------|---------------|---------|
| Respiratory baseline wander | < 0.5 Hz | Removed by high-pass filter |
| P and T wave energy | 0.5–5 Hz | Preserved in display filter |
| QRS complex energy | 5–40 Hz | Isolated by detection filter (5–15 Hz) |
| Powerline interference | 50/60 Hz | Targeted by planned notch filter |

### Dual-Band Filter Design

The pipeline uses two deliberately separate filter paths:

| Filter | Band | Purpose |
|--------|------|---------|
| Bandpass Butterworth | 5–15 Hz | QRS detection — Pan-Tompkins optimal band |
| Bandpass Butterworth | 0.5–40 Hz | Display — full PQRST morphology |

The detection and display paths are separate by design. The 5–15 Hz detection filter maximises R-peak sensitivity; the 0.5–40 Hz display filter ensures clinicians see a morphologically complete waveform. Collapsing these into a single path would force a tradeoff between detection accuracy and clinical display quality — this architecture avoids that tradeoff entirely.

---

## Methodology

### 1. Data Ingestion (`data_sources.py`)

The pipeline streams records from PhysioNet's MIT-BIH Arrhythmia Database via `wfdb`, and supports live hardware and synthetic inputs:

| Source | Description |
|--------|-------------|
| MIT-BIH / PhysioNet | Clinical ECG records via `wfdb` |
| CSV file | Single-column or labelled ECG data |
| Serial port | Live ECG sensor (e.g. Arduino + AD8232) |
| Network socket | Wireless or cloud-streamed ECG data |
| Synthetic | Simulated signal for development and testing |

### 2. Streaming Buffer (`buffer.py`)

A `StreamingBuffer` class implements a sliding window with configurable overlap:

- **Window:** 3-second chunks (1,080 samples at 360 Hz)
- **Overlap:** 1 second (360 samples) — prevents edge artifacts at chunk boundaries
- **Stride:** 2 seconds per advance — ensures continuity across transitions
- Filter state (`zi` — second-order section delay state) is carried between chunks, eliminating phase discontinuities at boundaries

### 3. Signal Conditioning (`filters.py`)

A two-stage stateful Butterworth filter chain processes each chunk:

1. **DC offset removal** — subtracts the chunk mean to centre the signal at 0 mV
2. **Bandpass at 5–15 Hz** — isolates QRS energy for detection
3. **Bandpass at 0.5–40 Hz** — parallel path preserving full waveform morphology for display

### 4. QRS Detection — Pan-Tompkins (`detection.py`)

A full implementation of Pan-Tompkins (1985) with dual adaptive thresholds:

1. **Differentiation** — emphasises the steep slope of the R-wave
2. **Squaring** — makes all values positive; amplifies large slopes nonlinearly
3. **Moving-window integration** — 150 ms window highlights QRS energy peaks
4. **Dual adaptive thresholds:**
   - `THRESHOLD1` — primary detection; higher threshold, fewer false positives
   - `THRESHOLD2` — searchback detection; lower threshold, recovers missed beats
   - Both update continuously from the last 8 detected peaks
5. **Refractory period** — 250 ms minimum between detections prevents double-counting within a single beat
6. **Searchback logic** — if no peak is found within 1.5× the expected RR interval, the algorithm searches backward using `THRESHOLD2`
7. **First-sweep calibration guard** — suppresses markers and alerts during the initial buffer revolution while adaptive thresholds stabilise

### 5. Peak Deduplication & Marker Correction (`detection.py`)

Detected peaks are converted from local chunk indices to global signal indices. Near-duplicate detections across overlapping windows (within ±3 samples) are suppressed. Because the detection filter and display filter differ in phase, a local maximum search of ±15 samples corrects R-peak marker placement onto the display signal.

### 6. HRV Analytics (`metrics.py`)

```
RR intervals (ms)       = diff(R-peak times in ms)
Successive differences  = diff(RR intervals)
RMSSD                   = sqrt(mean(successive_differences²))
CV                      = std(RR intervals) / mean(RR intervals)
```

Both RMSSD and CV are computed continuously from the rolling R-peak record and updated each chunk.

### 7. AFib Detection (`arrhythmia.py`)

The detector evaluates two criteria against validated clinical thresholds:

- **CV > 15%** — RR interval irregularity exceeding the threshold associated with chaotic AV conduction
- **RMSSD > 50 ms** — beat-to-beat variability consistent with fibrillatory conduction

A hysteresis gate requires **3 consecutive positive detections** before issuing an alert, and **3 consecutive negative detections** before clearing it. This design suppresses transient false positives without delaying detection of sustained episodes.

### 8. Clinical Sweep Display (`display.py`)

The display is implemented in PyQt6 and PyQtGraph, rendering a real-time clinical sweep at 25 mm/s — the standard paper speed used in clinical ECG interpretation. PyQtGraph's `curve.setData()` updates only changed data per frame, making continuous rendering viable without frame-rate degradation.

Display components:
- Wideband filtered ECG sweep with R-peak markers
- Live HRV panel (RMSSD, CV, mean HR)
- AFib alert indicator with hysteresis state
- First-sweep suppression — no markers or alerts until the buffer has completed its initial revolution

---

## Validation

The pipeline has been validated against three records from the MIT-BIH Arrhythmia Database:

| Record | Description | Validation Focus |
|--------|-------------|-----------------|
| 100 | Normal sinus rhythm | Baseline QRS detection accuracy |
| 217 | Mixed arrhythmias; inverted polarity | Polarity handling; detection robustness |
| 221 | AFib from beat zero | AFib detector sensitivity; early detection |

MIT-BIH is a clinical-grade, peer-reviewed dataset used as the standard benchmark in published QRS detection literature. Validation against these records constitutes a credible, reproducible performance baseline without requiring physical hardware.

**Polarity note:** Some MIT-BIH records (e.g. 217) exhibit signal polarity inversion. The pipeline includes a pre-detection polarity check — comparing signal minimum and maximum extremity — and inverts the signal if necessary before Pan-Tompkins runs.

---

## Development Roadmap

### Phase 1 — Signal Quality *(In Progress)*

- [x] Dual-band filter pipeline (detection + display)
- [x] Streaming architecture with sliding window buffer
- [x] Modular refactor (`filters`, `buffer`, `metrics`, `detection`, `arrhythmia`, `processor`, `data_sources`, `display`)
- [ ] **50/60 Hz notch filter** — powerline interference removal (critical for physical hardware)
- [ ] **Signal Quality Index (SQI)** — distinguish genuine flatline from lead-off artifact

### Phase 2 — Arrhythmia Detection *(Partially Complete)*

- [x] AFib detection (CV + RMSSD, hysteresis-gated)
- [ ] **Tier 1 — Immediately life-threatening:** VFib, VTach, complete heart block
- [ ] **Tier 2 — Clinically urgent:** STEMI morphology (ST elevation), long QT syndrome
- [ ] **Tier 3 — Clinically significant:** PVCs, bundle branch blocks, second-degree heart blocks

### Phase 3 — Extended Analytics

- **Full HRV suite:** SDNN, pNN50, LF/HF frequency-domain ratio via FFT on the RR interval series
- **ST segment morphology analysis** — elevation and depression detection as a future pipeline stage
- **Hardware integration** — patient simulator acquisition via simulation lab as the most accessible validation pathway

### Phase 4 — Usability *(Non-Technical Operators)*

- **Refined GUI** — large waveform display, clear metric readouts, alert indicators requiring no DSP knowledge
- **Clinical report export** — PDF summaries with waveform snapshots, HRV metrics, and plain-language findings
- **Automatic device setup** — plug-and-play serial/USB detection

### Phase 5 — Clinical Compliance *(Regulatory)*

- **IEC 60601** medical electrical equipment safety certification
- **Alarm system** conforming to IEC 62133 alert thresholds for life-critical events
- **Data logging** — HIPAA-compliant audit trail with HL7/FHIR format compatibility
- Regulatory approval pathway (FDA 510(k) or CE marking depending on jurisdiction)

---

## Installation

```bash
git clone https://github.com/Gyungeose/ECG-Signal-Processor.git
cd ECG-Signal-Processor
pip install -r requirements.txt
```

### Dependencies

```
wfdb
numpy
scipy
PyQt6
pyqtgraph
```

Optional (for live hardware streaming):

```bash
pip install pyserial   # Serial port / physical ECG sensor support
```

---

## Usage

```bash
python main.py
```

The pipeline prompts for a data source at startup:

```
ECG STREAMING DATA SOURCE SELECTOR
====================================
1. Synthetic   — simulated signal for testing
2. MIT-BIH     — PhysioNet clinical record via wfdb
3. CSV File    — pre-recorded ECG data
4. Serial Port — live sensor connection (AD8232, Arduino, etc.)
5. Network     — wireless or cloud-streamed ECG
```

Source-specific configuration (record number, file path, port) is handled interactively. The clinical sweep display launches automatically on source selection.

---

## References

- Pan, J. & Tompkins, W.J. (1985). *A Real-Time QRS Detection Algorithm.* IEEE Transactions on Biomedical Engineering, 32(3), 230–236.
- Task Force of the European Society of Cardiology (1996). *Heart Rate Variability: Standards of Measurement, Physiological Interpretation, and Clinical Use.* Circulation, 93(5), 1043–1065.
- Goldberger, A.L. et al. (2000). *PhysioBank, PhysioToolkit, and PhysioNet: Components of a New Research Resource for Complex Physiologic Signals.* Circulation, 101(23), e215–e220.
- Malik, M. (1996). *Heart Rate Variability.* Annals of Noninvasive Electrocardiology.
- MIT-BIH Arrhythmia Database — PhysioNet: https://physionet.org/content/mitdb/

---

## License

MIT License — see [LICENSE](LICENSE) for details.