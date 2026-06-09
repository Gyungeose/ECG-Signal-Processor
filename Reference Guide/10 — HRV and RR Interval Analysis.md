## Why RR Variability Exists

A healthy heart does **not** beat at a perfectly constant rate. The RR intervals fluctuate — by 10, 20, even 50 milliseconds between consecutive beats. This is not a defect. It's a *feature*.

**Source:** The **autonomic nervous system** (ANS). The parasympathetic branch (vagus nerve) continuously modulates the SA node's firing rate. Inspiration increases sympathetic tone slightly (faster rate). Expiration increases parasympathetic tone slightly (slower rate). Over longer timescales, emotional state, stress, and physical activity shift the balance.

**Clinical principle:** **High variability = high parasympathetic tone = healthy autonomic function.** Low variability (a perfectly regular rhythm) = either parasympathetic withdrawal or a problem with the autonomic nervous system.

---

## Key HRV Metrics

### **RMSSD: Root Mean Square of Successive Differences**

**Definition:** Take the difference between each pair of consecutive RR intervals. Square each difference. Average them. Take the square root.

$$\text{RMSSD} = \sqrt{\frac{1}{N-1} \sum_{i=1}^{N-1} (RR_i - RR_{i+1})^2}$$

**What it measures:** Beat-to-beat *variability* — how much the RR intervals are bouncing around from one beat to the next.

**Interpretation:**
- **High RMSSD (>50 ms):** Healthy variability. Good parasympathetic tone. The vagus nerve is active, modulating the rate constantly.
- **Low RMSSD (<20 ms):** Reduced variability. Suggests parasympathetic withdrawal or autonomic dysfunction.
- **Very low RMSSD (<10 ms):** Concerning. Associated with increased mortality risk after MI, poor prognosis in heart failure.

**Why it matters:** In a healthy person at rest, the vagus nerve is tone *high*, keeping the heart rate down and variable. In acute illness (MI, sepsis), the vagus "lets go" and the rate becomes more fixed. In chronic heart failure or after MI, reduced HRV predicts sudden cardiac death.

> [!tip]- Retrieval Cue
> A patient has RMSSD = 15 ms (low variability). What does this tell you about their parasympathetic nervous system activity?

### **Coefficient of Variation (CV)**

**Definition:** The standard deviation of RR intervals, normalized by the mean:

$$\text{CV} = \frac{\text{SD of RR intervals}}{\text{Mean RR interval}} \times 100\%$$

**Interpretation:**
- **CV < 5%:** Very regular. All RR intervals are nearly identical.
- **CV 5–15%:** Normal sinus arrhythmia.
- **CV > 15%:** Marked irregularity. Possible atrial fibrillation or frequent ectopy.

**Difference from RMSSD:** RMSSD measures *beat-to-beat* changes (high sensitivity to rapid fluctuations). CV measures overall *spread* (includes longer-term trends). Both capture variability, but in different ways.

### **LF/HF Ratio (frequency domain)**

In frequency-domain HRV analysis, you transform the RR interval series into a power spectrum:

- **Low-frequency (LF) power (0.04–0.15 Hz):** Reflects a mix of parasympathetic and sympathetic influence.
- **High-frequency (HF) power (0.15–0.4 Hz):** Reflects *pure* parasympathetic influence (linked to respiration).
- **LF/HF ratio:** A proxy for sympathetic-parasympathetic balance. High ratio = sympathetic dominance. Low ratio = parasympathetic dominance.

**Clinical use:** Less standardized than RMSSD or CV, but useful in research for tracking autonomic state during stressful interventions.

---

## Measuring HRV from a Single Lead

**Advantage of single-lead ECG:** You don't need a full 12-lead. A single continuous rhythm strip gives you all the RR intervals you need to compute HRV metrics.

**Standard protocol:** Record **5 minutes** of continuous ECG in a quiet, controlled setting (patient resting, supine). This ensures enough beats (~300–400 at normal rate) for stable statistics and captures the respiratory modulation cycle.

**From the recorded signal:**
1. Detect all R peaks (using pan-Tompkins or similar).
2. Compute all RR intervals.
3. Calculate RMSSD, CV, or other metrics.

**What you get:** A number (e.g., "RMSSD = 42 ms") that reflects the patient's parasympathetic tone *at that moment*.

> [!example]- Worked Example
> **Two patients, both with normal sinus rhythm at ~70 bpm:**
>
> **Patient A:** 5-minute strip shows RR intervals of 857, 843, 875, 851, 869, 855, 880, ... (bouncing around ±20 ms). RMSSD = 48 ms (healthy).
>
> **Patient B:** 5-minute strip shows RR intervals of 857, 858, 859, 859, 858, 857, 859, ... (almost identical). RMSSD = 2 ms (reduced).
>
> Patient A is healthy. Patient B might have autonomic dysfunction, be acutely ill, or be on a beta-blocker (which suppresses parasympathetic tone).

---

## HRV and Clinical States

### **Healthy, Resting State**
- High RMSSD (>40 ms)
- CV ~10%
- Predominantly high-frequency HRV (respiratory-linked)
- Meaning: Vagal tone is high; the vagus nerve is "in control" of the heart rate.

### **Acute Stress, Pain, Fever**
- RMSSD drops (sympathetic surge)
- CV stays normal or drops slightly
- Low HF, high LF
- Meaning: Fight-or-flight response. The sympathetic nervous system overrides parasympathetic tone.

### **Acute MI**
- RMSSD drops acutely (within hours of infarction)
- Remains low for days to weeks
- Depressed HRV is a **predictor of arrhythmia and sudden cardiac death** in the post-MI period
- Meaning: The infarcted tissue and surrounding inflammation suppress parasympathetic tone.

### **Heart Failure**
- Chronically low RMSSD
- High LF/HF ratio (sympathetic dominance)
- Poor prognosis (strong predictor of mortality)
- Meaning: The failing heart has lost normal autonomic regulation.

### **Sleep and Rest**
- RMSSD increases during deep sleep (very high parasympathetic tone)
- Drops during REM sleep and waking
- Meaning: Sleep is a time of parasympathetic dominance.

### **Athletic Conditioning**
- Higher baseline RMSSD than sedentary controls
- Can be 50–100+ ms in endurance athletes
- Meaning: Training increases vagal tone (parasympathetic adaptation).

---

## Why Single-Lead HRV Analysis Is Powerful

Traditional HRV requires **24-hour Holter monitoring** or **5-minute controlled recordings**. But:

1. **Minimal equipment:** A single-lead ECG (even a wearable) is enough.
2. **Computation is simple:** You only need R-peak times, not the full signal morphology.
3. **Early warning:** Acutely depressed HRV can flag patients at risk (post-MI, heart failure exacerbation).
4. **Non-invasive:** No special procedures or patient burden.

**Limitation:** HRV is a *surrogate marker* of autonomic function, not a diagnosis. Low HRV is associated with poor outcomes, but it doesn't tell you *why* it's low. The cause could be acute illness, medication, autonomic neuropathy, or heart failure.

> [!question]- Feynman Check
> A patient has acutely low RMSSD after an MI. What physiologic change in the heart and ANS is occurring to cause this suppression of HRV?

---

## Practical Measurement: The Window Approach

For long continuous recordings (like telemetry strips or 24-hour Holter), HRV varies over time. A useful approach is **sliding windows**:

1. Take the first 5 minutes of the recording. Calculate RMSSD.
2. Slide 1 minute forward. Take the next 5 minutes. Calculate new RMSSD.
3. Repeat across the entire 24 hours.

**Result:** A time series of RMSSD values, showing how autonomic state changes throughout the day. You'll see:
- Higher RMSSD during sleep
- Drops in HRV upon waking and stress
- Changes during arrhythmia episodes

This **dynamic HRV** tracking can detect deterioration (HRV dropping over days) — an early sign of decompensation in heart failure.

---

## Confounding Factors

Not all variation in HRV is autonomic:

1. **Respiratory rate:** Faster breathing increases HF power (respiratory-linked variability). Slower breathing decreases it. For standardized HRV, control respiration or record at rest.

2. **Posture:** Supine recordings show different HRV than standing. Upright position increases sympathetic tone (HRV drops).

3. **Medications:** Beta-blockers, ACE inhibitors, some antiarrhythmics suppress HRV. This is not necessarily bad — in heart failure, beta-blockers improve outcomes *despite* lowering HRV.

4. **Ectopy:** If the patient has frequent premature beats, the RR intervals are chaotic (high CV). This mimics "high variability" but isn't truly autonomic; it's arrhythmia. Remove ectopic beats before calculating RMSSD.

---

## Summary

Heart rate variability — the beat-to-beat fluctuation in RR intervals — reflects parasympathetic nervous system tone. **RMSSD** (>50 ms = healthy, <20 ms = reduced) and **CV** (<5% = regular, >15% = irregular) are simple metrics computable from a single ECG lead. High HRV is healthy; low HRV predicts poor outcomes in MI and heart failure. The key insight: a *perfect* heart rate (completely constant) is not healthy — it suggests loss of normal autonomic regulation.

---

## Cross-Field Connections
- **Autonomic physiology:** Vagal tone, sympathetic-parasympathetic balance (A&P/PHYS)
- **Pathophysiology:** Autonomic dysfunction in disease states (pathology)
- **Signal processing:** Frequency-domain analysis, power spectral density (signal processing/DSP)
- **Clinical:** Prognosis, risk stratification in MI and heart failure (clinical medicine)
