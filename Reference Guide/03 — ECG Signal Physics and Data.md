## From Analog to Digital

The heart's electrical activity is **continuous and analog** — a smooth, unbroken voltage signal flowing from the electrodes into the ECG machine. But the moment you want to store it, transmit it, or run an algorithm on it, you have to **digitize** it: convert the analog voltage into discrete numbers (samples) that a computer can manipulate.

This conversion is lossy. You cannot capture *infinite* detail. You have to make choices:
1. **How often do you sample?** (sampling rate)
2. **How precisely do you measure each sample?** (quantization / bit depth)
3. **What noise do you accept, and what do you attenuate?** (filtering)

Get these decisions wrong and your data is either too coarse (you miss the fine features of the QRS) or too expensive (storing gigabytes of data when kilobytes would do).

---

## Sampling Rate: Timing Resolution

**Definition:** Sampling rate is the number of times per second you measure the voltage. The MIT-BIH Arrhythmia Database uses **360 Hz** — meaning the ECG is sampled 360 times per second, or once every 2.78 milliseconds.

**Why 360 Hz?** 

The Nyquist-Shannon theorem says: to accurately capture a signal that contains frequencies up to *f*, you need to sample at least at *2f*. The QRS complex contains energy up to roughly 100–150 Hz (the sharp edges of the QRS are high-frequency). So you need to sample at least at 200–300 Hz.

360 Hz was chosen because:
1. It's fast enough to capture the QRS detail (it exceeds the Nyquist requirement).
2. It's a "nice" number for computing (divisors of 360 are 1, 2, 3, 4, 5, 6, 8, 9, 10, 12, 15, 18, 20, 24, 30, 36, 40, 45, 60, 90, 120, 180 — useful for downsampling).
3. It was computationally feasible in the 1970s when MIT-BIH was created.

**Temporal resolution:** At 360 Hz, each sample spans $\frac{1}{360} = 2.78$ milliseconds. If you want to know the *exact* moment a peak occurs, you're accurate to ±1.4 ms. This is fine for most clinical purposes but might miss the nanosecond-level precision that some research applications need.

> [!tip]- Retrieval Cue
> If you sample at 360 Hz and you're trying to detect the peak of the QRS (which might span only 5–10 ms), how many samples will you capture during the QRS? Is that enough to locate the peak precisely?

---

## Quantization: Amplitude Resolution

**Definition:** Each sample isn't just a number — it's a *discrete* number with limited precision. The MIT-BIH database stores samples as **16-bit signed integers**, meaning each sample is a whole number between -32,768 and +32,767.

**The catch:** The actual analog voltage (from the ECG machine) is a fraction of a millivolt, but you're storing it as an integer. How do you convert 0.123 mV into an integer?

**Answer:** The ADC (analog-to-digital converter) multiplies the voltage by a *scale factor*, then rounds.

$$\text{Integer sample} = \text{Voltage (mV)} \times \text{ADC Gain}$$

For MIT-BIH, the ADC gain is **200**, meaning:
$$\text{Integer sample} = \text{Voltage (mV)} \times 200$$

So 0.123 mV becomes 24.6 → rounds to 25. Conversely, to convert back to mV:

$$\text{Voltage (mV)} = \frac{\text{Integer sample}}{200}$$

**The unit:** A single "integer unit" in the stored signal corresponds to $\frac{1}{200} = 0.005$ mV = **5 microvolts**. This is the **amplitude resolution** — the smallest voltage change the data can represent.

**Is 5 microvolts fine enough?** For clinical ECG, yes. The smallest clinically significant deflection (like a pathological Q wave) is on the order of 0.1 mV = 100 microvolts, which is 20 units at our 5-microvolt resolution. For research-grade analysis, you might want higher resolution, but this is standard.

```
Example conversion:
Analog: 0.125 mV  →  0.125 × 200 = 25 units  →  25 / 200 = 0.125 mV ✓
Analog: 0.123 mV  →  0.123 × 200 = 24.6 → 25 units  →  25 / 200 = 0.125 mV (loss of 0.002 mV)
```

> [!question]- Feynman Check
> If you're storing an ECG at 16-bit quantization with a gain of 200, and you're trying to measure a T wave that's 0.3 mV tall, how many units tall will it be in the stored data? Is that tall enough to distinguish from noise?

---

## Noise: The Adversary

The ECG signal you capture is **signal + noise**. The signal is the cardiac electrical activity. The noise is everything else:

### **Baseline Wander (0.1–1 Hz)**
**Source:** Respiration. As the patient breathes, their chest expands and contracts. The electrode-skin impedance changes. The baseline voltage drifts up and down.

**On the recording:** A slow wandering up and down that makes the entire tracing rise and fall like breathing itself.

**Impact:** Can mimic ST elevation. A rising baseline + positive T wave can look like ST elevation; a falling baseline can hide ST depression.

**Frequency content:** Low frequency, 0.1–0.5 Hz typically.

### **Muscle Artifact (10–100 Hz)**
**Source:** The patient tenses a muscle. Motor units in the skeletal muscle fire. Thousands of action potentials create a chaotic, high-amplitude voltage spike.

**On the recording:** A ragged, irregular, high-amplitude deflection that makes the baseline look like static.

**Impact:** Can completely obscure the ECG. If the patient clenches their fists, if they shiver from cold, if they have Parkinson's disease — the ECG becomes uninterpretable.

**Frequency content:** Higher frequency, 5–100 Hz.

### **60 Hz Powerline Interference (50–60 Hz)**
**Source:** Electrical fields from the building wiring, transformers, motors. The AC current cycles at 60 Hz in North America (50 Hz in Europe). This electromagnetic field couples into the patient and the ECG leads.

**On the recording:** A fine, regular oscillation superimposed on the ECG. Looks like the signal is vibrating at 60 Hz.

**Impact:** Subtle but persistent. It doesn't usually obscure the QRS, but it can disrupt automatic QT interval measurement.

**Frequency content:** Narrow-band at exactly 60 Hz.

### **Electrode Motion Artifact (0.5–10 Hz)**
**Source:** The electrode isn't making good contact with the skin, or it's moving (patient moving, external vibration). The contact impedance fluctuates.

**On the recording:** Low-frequency wandering (similar to baseline wander) or occasional spikes.

**Impact:** Can mimic arrhythmias.

### **SNR: Signal-to-Noise Ratio**

A useful metric: the ratio of the signal *power* to the noise *power*.

$$\text{SNR} = \frac{P_{\text{signal}}}{P_{\text{noise}}}$$

In clinical ECGs, typical SNR is 10–30 dB (10:1 to 1000:1 power ratio). A "clean" ECG in a quiet setting might have SNR > 30 dB. A noisy ECG (muscular patient, poor electrode contact) might drop to 5 dB (3:1 power ratio).

The **QRS complex is your friend here.** The QRS is high-amplitude and high-frequency (100+ Hz), which makes it stand out from baseline wander (0.1–1 Hz) and even muscle artifact (if it's rhythmic). This is why QRS detection — the foundation of all rhythm analysis — is actually pretty robust even in noisy data.

> [!example]- Worked Example
> **Patient in the ED with chest pain:** ECG is attached. First tracing shows visible 60 Hz oscillation superimposed on the signal. QRS is visible, but ST segments are hard to measure precisely. Technique: reposition the patient's arms (they were flexed, causing muscle artifact + electrode motion). Ensure all electrodes have good contact. Re-run the ECG. The 60 Hz persists (it's from the building) but baseline wander is gone, and muscle artifact is gone. ST segments are now readable. Diagnosis becomes clear: ST elevation in V1–V3 (anterior STEMI). Same patient, same heart, different data quality — different diagnostic capability.

---

## ADC and You

When you work with ECG data programmatically:

1. **Know your ADC gain.** MIT-BIH has gain 200. Other databases or devices might differ (sometimes 100, sometimes 500). If you don't convert properly, you'll have voltages that are off by orders of magnitude.

2. **Know your sampling rate.** MIT-BIH is 360 Hz. Some devices sample at 250 Hz or 500 Hz. This changes how you compute time intervals.

3. **Handle quantization appropriately.** Integer samples contain ~5 microvolts of discretization error. For features >0.1 mV, this is negligible. For tiny features (like early repolarization notches), it matters.

4. **Plan filtering *before* downsampling.** If you want to resample from 360 Hz to 100 Hz, you must first apply a lowpass filter at 50 Hz (Nyquist frequency for 100 Hz sampling). Otherwise you'll alias high-frequency noise into the lower frequencies.

---

## Summary

An ECG signal lives at the intersection of **physics** (the heart), **analog electronics** (the amplifier and ADC), and **digital data** (samples and bits). The 360 Hz sampling rate captures QRS detail; the 200× ADC gain ensures 5-microvolt precision. Noise — from respiration, muscle, power lines, and electrode motion — is ever-present. Understanding what your data *actually represents* (integers in a file, not pure voltages) is the first step to analyzing it correctly.

---

## Cross-Field Connections
- **Signal processing:** Nyquist theorem, aliasing, sampling (core DSP theory)
- **Noise sources:** Biomedical signal acquisition, electrode physiology
- **Practical:** Data standards, format conversion, quality assurance in ECG databases
