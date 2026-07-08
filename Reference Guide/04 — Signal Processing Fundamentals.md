## Why Filter?

The raw ECG signal is signal + noise. A **filter** is a mathematical operation that attenuates (weakens) unwanted frequencies while preserving the signal you care about.

Think of it like a sieve: a coffee filter lets water through but stops grounds. An ECG filter lets the heart's electrical activity through but stops the 60 Hz hum and respiratory wandering.

There's a trade-off: *every* filter slightly distorts the signal. Remove too much noise and you also remove real cardiac features (like the fine structure of the QRS). Preserve too much detail and noise overwhelms the signal. The art of signal processing is finding the sweet spot.

---

## Frequency Content of the ECG

Different cardiac components live in different frequency bands:

| **Component** | **Frequency** | **Typical Use** |
|---|---|---|
| **P wave** | 0.5–3 Hz | Low frequency; slow rise and fall |
| **PR interval** | (silent) | — |
| **QRS complex** | 5–100 Hz | High frequency; sharp edges |
| **ST segment** | 0.5–1 Hz | Very low frequency; baseline |
| **T wave** | 0.5–3 Hz | Low frequency |
| **Baseline wander** | 0.1–0.5 Hz | Noise; respiration |
| **Muscle artifact** | 5–100 Hz | Noise; motor units firing |
| **60 Hz powerline** | 60 Hz | Noise; building wiring |

**Key insight:** The QRS complex is *high-frequency* (sharp, fast transition from negative to positive). The P and T waves are *low-frequency* (gradual, smooth curves). This frequency separation is why it's possible to detect QRS without being fooled by P or T waves — they literally occupy different parts of the spectrum.

```
Power spectrum of a normal ECG (simplified):

Power
  |     ╱╲  (QRS complex, 5-100 Hz)
  |    ╱  ╲
  |   ╱    ╲_____
  |  ╱           ╲___
  | ╱                ╲
  |__________________ Frequency (Hz)
  0   1    5    50   100  150
      ↑         ↑
    P,T      QRS  (sharp edges)
```

---

## The Display Filter: 0.5–40 Hz

Clinical ECG machines print ECGs after applying a **bandpass filter** that passes frequencies between 0.5 and 40 Hz.

**Why these cutoffs?**

- **0.5 Hz (highpass):** Blocks baseline wander (which is <0.5 Hz). Respiration is 0.1–0.3 Hz, so 0.5 Hz removes it.
- **40 Hz (lowpass):** Keeps the QRS (which is 5–100 Hz). The cutoff at 40 Hz is a compromise: it removes muscle artifact (which extends to 100 Hz) while keeping the bulk of the QRS visible.

**What gets destroyed?**
- The fine, high-frequency detail of the QRS (above 40 Hz).
- The precise morphology of action potential notches and early repolarization features.

**Why is this acceptable?**
- For *clinical diagnosis* (STEMI? Arrhythmia? Axis deviation?), 40 Hz is enough.
- Cardiologists didn't need the frequencies above 40 Hz to make their diagnoses.

**But:** If you're trying to *detect the QRS algorithmically*, the 0.5–40 Hz filter removes *some of the features that make detection easy*. This is why automated QRS detectors often use a different filter.

---

## The Detection Filter: 5–15 Hz

A **narrower bandpass filter** (5–15 Hz) is sometimes used for QRS *detection* algorithms. Here's why:

- **Above 15 Hz:** Muscle artifact and other noise dominate.
- **Below 5 Hz:** P waves, T waves, baseline wander.
- **5–15 Hz:** The "sweet spot" where the QRS energy is concentrated *relative to noise*.

This filter is more aggressive — it destroys clinical details but isolates the QRS. A machine might:
1. Use the 5–15 Hz filtered signal for *detection* (finding where the QRS is).
2. Use the 0.5–40 Hz filtered signal for *measurement* (measuring intervals and amplitudes).

> [!tip]- Retrieval Cue
> Why would you filter the same ECG differently for detection vs. measurement? What are you optimizing for in each case?

---

## The Pan-Tompkins Algorithm: A Worked Example

The **Pan-Tompkins algorithm** is a classic QRS detector published in 1985 and still widely used (including in some of the MIT-BIH dataset tools). It's a cascade of operations, each exploiting a different property of the QRS.

### **Step 1: Bandpass Filter (5–15 Hz)**
Apply the narrow filter. The goal: suppress P waves, T waves, baseline wander, and high-frequency noise. Let only QRS energy through.

### **Step 2: Differentiate**
Take the first derivative: $\frac{dV}{dt}$.

**Why?** The derivative emphasizes *sharp edges*. The QRS is sharp (large $\frac{dV}{dt}$). P and T waves are gentle (small $\frac{dV}{dt}$). Noise is random.

```
Original signal:        Derivative:
  |    ╱╲              |    ╱  ╲╱
  |   ╱  ╲____         |   ╱    ╲
  |  ╱       ╲         |  ╱      ╲
  |___________|        |__________|
  
QRS has steeper slopes → larger derivatives
```

### **Step 3: Square**
Take each sample and square it: $\left(\frac{dV}{dt}\right)^2$.

**Why?** Squaring is nonlinear. It amplifies large values disproportionately. A derivative of 2 becomes 4. A derivative of 10 becomes 100. This *further* separates QRS (large values) from noise (small values).

### **Step 4: Moving Window Integration**
For each sample, sum the squared values in a window (e.g., 150 ms window). This creates a smooth, peaked signal.

```
Squared derivatives:   Moving window integral:
|  ___               |     ╱╲
| |_|_|__|            |    ╱  ╲    ╱╲
| |_|_|__|_|__       |   ╱    ╲  ╱  ╲
|_|_|__|_|__|         |__╱      ╲╱
```

**Why?** The QRS extends ~100 ms. A 150 ms window integrates the entire QRS peak into a single high value. This "smears" the noise (random, uncorrelated) into a low value. Signal-to-noise ratio improves.

### **Step 5: Threshold and Peak Detection**
Set a threshold (e.g., 50% of the maximum moving-window integral). When the integral crosses above the threshold, you've found a QRS. Find the exact peak by searching within the threshold-crossing region in the original signal.

---

## QRS Polarity and Lead Orientation

Here's a subtlety: **the QRS polarity depends on the lead orientation.**

In a lead looking directly at the source of depolarization, the QRS is **upright** (positive). In a lead looking away from it, the QRS is **inverted** (negative). In a lead looking perpendicular, the QRS is **biphasic** (both up and down).

This matters for QRS detection:

```
Lead II (inferior):    Lead aVR (opposite):   Lead I (lateral):
Sees depolarization   Sees depolarization    Sees it sideways
moving toward you     moving away            (mixed)

    ╱╲                     ╱╲
   ╱  ╲                   ╱  ╲
  ╱____╲____            ╱    ╱╲                ╱╲_
 (positive QRS)     ____╱____╱__\           __╱   ╲
                   (negative QRS)           (biphasic)
```

An algorithm must be **polarity-agnostic**: it should detect the QRS regardless of whether it's up or down. The Pan-Tompkins algorithm handles this because:
- The *derivative* is directional (positive slope vs. negative slope).
- *Squaring* makes it magnitude-only (negative slope squared is positive).

So whether the QRS goes up or down, the squared derivative is large.

> [!example]- Worked Example
> **Lead V1:** QRS is biphasic (part negative from the septum, part positive from the left ventricle). Pan-Tompkins derivatives will be both positive and negative, but squaring makes them both large. The algorithm detects it correctly.
>
> **Hypothetical broken algorithm:** Naively thresholds the derivative: "if $\frac{dV}{dt} > 5$ mV/ms, it's a QRS." In lead V1, the negative component has $\frac{dV}{dt} < -5$ mV/ms, so it's missed. This algorithm would fail in V1 (and aVR, which also has inverted QRS in normal sinus rhythm).

---

## Trade-offs: Sensitivity vs. Specificity

The threshold in step 5 controls the trade-off:

- **Lower threshold:** Detect more peaks, including some noise peaks. **High sensitivity** (catch all real QRS), **low specificity** (false positives).
- **Higher threshold:** Detect only strong peaks. **Low sensitivity** (miss some real QRS, especially in noisy data), **high specificity** (fewer false positives).

Real algorithms add **hysteresis**: set two thresholds (lower and upper). Once you cross the lower threshold, keep searching until you exceed the upper threshold, then lock in the peak. This reduces false detections from noise oscillations.

> [!question]- Feynman Check
> Explain why squaring the derivative helps distinguish QRS from noise, in terms of the magnitude of slopes and the effect of nonlinearity.

---

## Limitations of Frequency-Domain Filtering

Not all filtering is as simple as "pass 5–15 Hz." Some issues:

1. **The QRS is *broadband*.** It contains energy from 5 Hz all the way to 100 Hz. A 5–15 Hz filter destroys the high-frequency detail, losing information. Real algorithms sometimes use *multiple* filters at different frequencies, process them in parallel, and combine the results.

2. **Ectopic rhythms change the spectrum.** A premature ventricular contraction (PVC) might have different frequency content than normal QRS. A filter optimized for one might not work well for the other.

3. **Baseline wander is time-varying.** Respiration rate changes. A fixed 0.5 Hz highpass filter works on average but can fail if the patient takes a deep breath at exactly the wrong moment.

Modern algorithms often use **adaptive filtering** — the filter parameters adjust based on signal characteristics detected in real-time.

---

## Summary

Filtering is the foundation of automated ECG analysis. The ECG signal separates nicely into frequency bands (QRS high-frequency, P/T low-frequency, baseline wander very low-frequency), making frequency filtering effective. The Pan-Tompkins algorithm chains differentiation, squaring, and moving-window integration to isolate the QRS morphologically and statistically. But every filter is a compromise: preserve too much detail and noise wins; remove too much and you lose clinical information. Real systems use multiple filters for different purposes (detection vs. measurement, clinical display vs. algorithmic processing).

---

## Cross-Field Connections
- **Signal processing theory:** Fourier analysis, filtering, convolution (PHYS 200 if DSP covered; core to engineering)
- **Physiology:** Why the QRS is high-frequency (fast depolarization rate), why P/T are low-frequency (slow repolarization)
- **Clinical:** Different ECG machines use different filters; this is why a printed ECG looks slightly different from a digital one from the same patient
