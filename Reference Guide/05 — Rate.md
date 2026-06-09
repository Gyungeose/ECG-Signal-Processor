## The RR Interval

**Definition:** The interval between two consecutive R waves, measured in **milliseconds** (or sometimes as a ratio against normal).

On the raw ECG, R peaks are the tallest, sharpest deflections. They're easy to spot. Once you've located the R peaks, the RR interval is just *distance between peaks*.

$$\text{RR interval (ms)} = \text{Time between R}_i \text{ and R}_{i+1}$$

**Why care about R peaks specifically?** They're the most reliably detected feature in automated algorithms. P and T waves are variable in amplitude and morphology. The QRS is consistent and high-amplitude. The R is the apex of the QRS — the single best landmark.

---

## Heart Rate from RR Interval

**Method 1: The 300 Method (from printed ECG)**

Standard ECG paper runs at **25 mm/s**. Each **large square** (5 mm) represents **0.2 seconds**. Each small square (1 mm) represents **0.04 seconds**.

If you count the number of large squares between consecutive R waves, you can calculate rate directly:

$$\text{HR (bpm)} = \frac{300}{\text{Number of large squares}}$$

**Why 300?** Because there are 300 large squares in 60 seconds (5 mm/sec × 60 sec = 300 mm = 60 large squares... wait, let me recalculate. 25 mm/sec × 60 sec = 1500 mm / 5 mm per large square = 300 large squares. So if one RR interval spans 5 large squares, HR = 300/5 = 60 bpm. If it spans 3 large squares, HR = 300/3 = 100 bpm.

**Method 2: The 1500 Method (in milliseconds)**

$$\text{HR (bpm)} = \frac{60{,}000 \text{ ms/min}}{RR \text{ interval (ms)}} = \frac{1500 \text{ mm/min}}{RR \text{ interval (mm)}}$$

For RR = 600 ms (typical for 100 bpm): HR = 60,000 / 600 = 100 bpm.

> [!example]- Worked Example
> **Printed ECG:** You count 4 large squares between consecutive R peaks. Using 300 method: HR = 300/4 = 75 bpm.
>
> **Digital ECG at 360 Hz:** You measure RR = 720 samples. Time in seconds = 720 / 360 = 2 seconds. HR = 60 sec / 2 sec = 30 beats per minute... wait, that's too slow. Let me reconsider: if RR = 720 samples and sample interval = 1/360 seconds, then RR in seconds = 720/360 = 2 seconds. That's one beat every 2 seconds, which is 30 bpm — markedly bradycardic. More typical: RR = 360 samples = 1 second interval = 60 bpm.

---

## Normal, Slow, Fast

| **Category** | **Rate (bpm)** | **Clinical Significance** |
|---|---|---|
| **Bradycardia** | <60 | Slow. Can be normal in athletes (high vagal tone) or pathological (AV block, sick sinus syndrome). |
| **Normal** | 60–100 | Sinus rhythm, healthy adult. |
| **Tachycardia** | >100 | Fast. Can be normal (exercise, fever, anxiety) or pathological (atrial fibrillation, ventricular tachycardia). |
| **Severe bradycardia** | <40 | Risk of syncope, requires pacing consideration. |
| **Severe tachycardia** | >150 | Risk of hemodynamic instability; may require intervention. |

**Key point:** Rate alone doesn't diagnose. A 50 bpm heart rate is *normal* in a marathon runner at rest. A 100 bpm heart rate is *expected* in a patient with sepsis. Context is everything.

---

## Regular vs. Irregular Rate

**Regular rhythm:** All RR intervals are approximately equal (within 10–20 ms variation). You can predict when the next R wave will occur.

```
Regular:     R___R___R___R___R___R
             └─┘ └─┘ └─┘ └─┘ └─┘
             (equal intervals)
```

**Irregular rhythm:** RR intervals vary. Some beats are close; some are far. You can't predict timing.

```
Irregular:   R__R_____R_R___R__R_R
             └┘ └────┘└┘└──┘└┘└┘
             (unequal intervals)
```

**How irregular?**

- **Regularly irregular:** The variation follows a pattern (e.g., every 3rd beat is early). Example: second-degree AV block (every 2nd or 3rd P wave fails to conduct).
- **Irregularly irregular:** No pattern. Example: atrial fibrillation — the AV node is bombarded with random atrial depolarizations and conducts a random subset. Each RR interval is different from all others.

> [!tip]- Retrieval Cue
> If you see a rhythm where some RR intervals are 800 ms, some are 500 ms, some are 900 ms, with no repeating pattern — what's the physiologic basis for this? (Hint: what must be failing to time the heartbeat regularly?)

---

## Rate Calculation in Automated Systems

A computer doesn't count squares. It:

1. **Detects all R peaks** (using QRS detection like Pan-Tompkins).
2. **Calculates all RR intervals** (time between consecutive peaks).
3. **Computes mean RR** over a window (e.g., last 10 beats, or last 30 seconds).
4. **Converts to HR:** $\text{HR} = \frac{60{,}000}{\text{mean RR (ms)}}$ or $\frac{60}{\text{mean RR (seconds)}}$.

**Advantages of this approach:**
- Precise: millisecond-level accuracy.
- Automatic: no manual counting.
- Adaptable: can use sliding windows to detect trend (is HR increasing? decreasing?).

**Disadvantages:**
- Depends on reliable R-peak detection. A missed R peak skews RR intervals.
- Assumes R peaks correspond to heartbeats. Ectopic beats, noise false-positives, and T-wave over-sensing can corrupt the result.

---

## Rate Variability: A Preview

**Heart rate variability (HRV)** is the variation in RR intervals — a window into autonomic nervous system function. High HRV (RR intervals varying by 50–100 ms) suggests high parasympathetic tone (healthy, relaxed state). Low HRV (all RR intervals nearly identical) suggests sympathetic dominance or autonomic dysfunction.

This is covered in detail in LN10.

---

## Clinical Context Matters

**Same rate, different meanings:**

- **100 bpm in a resting patient:** Tachycardia. Investigate (fever? anxiety? compensation for low blood pressure?).
- **100 bpm in a patient running a marathon:** Expected and normal.
- **60 bpm in a resting athlete:** Bradycardia by number, but normal and desired (athletic conditioning).
- **60 bpm in an elderly patient on beta-blockers:** Expected (medication effect).
- **60 bpm in an acute MI patient:** Concerning if accompanied by hypotension (indicates poor cardiac output).

**Rate also changes instantly with clinical events:**
- Acute pain → tachycardia (sympathetic surge).
- Vagal maneuvers (ice to face, Valsalva) → brief bradycardia.
- Arrhythmia onset → sudden change in rate.

---

## Summary

Heart rate is the simplest ECG measurement, but it's information-rich when interpreted correctly. The RR interval is the foundation; rate is just its reciprocal. Regular rates have clinical meaning different from irregular rates. Automated systems calculate rate from detected R peaks; this is fast and precise but vulnerable to detection errors. Always consider clinical context — the "normal" rate depends on the patient, their activity, and their condition.

---

## Cross-Field Connections
- **Autonomic physiology:** Parasympathetic (vagal) slowing, sympathetic acceleration (A&P/PHYS)
- **Pathophysiology:** Tachycardia as compensation, bradycardia as conduction disease (pathology)
- **Clinical:** Vital signs integration, shock assessment (clinical medicine)
