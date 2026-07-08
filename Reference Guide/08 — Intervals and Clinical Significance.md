## Measuring Intervals on Paper and Digital

**On printed ECG (25 mm/s paper speed):**
- Large square = 5 mm = 0.2 seconds
- Small square = 1 mm = 0.04 seconds

To measure an interval, count the squares from the start to the end.

**Digitally (at 360 Hz sampling):**
- Each sample = 1/360 sec ≈ 2.78 ms
- To convert sample count to milliseconds: (sample count) / 360 × 1000

**Clinical standard:** All intervals are reported in **milliseconds (ms)** in medical records.

---

## PR Interval: AV Node Delay

**Definition:** From the start of the P wave to the start of the QRS.

**Measurement:** Find the first upstroke of the P wave, then find the first deflection of the QRS. Count the interval between them.

**Normal range:** 120–200 ms (0.12–0.20 seconds). Shorter in children, longer in elderly.

### **Prolonged PR Interval (>200 ms)**

**What it means:** The AV node is slow. Depolarization reaches the node, creeps through it at a reduced rate, then enters the ventricles.

**Causes:**
- **Increased parasympathetic tone:** Beta-blockers, calcium channel blockers (diltiazem, verapamil), digoxin.
- **AV node disease:** Myocarditis, infiltrative disease (amyloidosis), age-related degeneration.
- **Hyperkalemia:** High serum potassium slows AV conduction.
- **Hypothermia:** Slows all electrical activity.
- **Rheumatic heart disease, Lyme disease:** Can cause AV node inflammation.

**Clinical significance:** Usually asymptomatic unless accompanied by dropped beats (higher-degree AV block). If PR progressively lengthens, watch for progression to 2nd-degree block.

### **Shortened PR Interval (<120 ms)**

**What it means:** AV node conduction is *faster than normal*. This usually indicates an **accessory pathway** — an abnormal muscle connection that bypasses part of the AV node delay.

**Classic example:** **Wolff-Parkinson-White (WPW) syndrome.** An accessory tract (Bundle of Kent) allows depolarization to bypass the AV node entirely. The ventricle partially depolarizes via this tract (fast), then via the normal His-Purkinje (fast), resulting in a *pre-excited* QRS.

**ECG signs of WPW:**
- Shortened PR (<120 ms)
- **Delta wave:** A slurred upstroke at the beginning of the QRS (the pre-excited portion)
- Widened QRS (>120 ms) because part of the ventricle is depolarized via muscle instead of fast conduction.

**Clinical significance:** WPW patients are at risk for **atrioventricular reentrant tachycardia (AVRT)** — depolarization travels down one pathway and back up the other, creating a circuit. This can cause rapid tachycardia (200+ bpm) and hemodynamic instability. Treatment: avoid AV-nodal slowing drugs (beta-blockers, verapamil) in acute AVRT — they block the slow pathway, forcing conduction entirely through the fast accessory tract, *worsening* the arrhythmia. Use amiodarone or other agents that block the accessory tract directly.

> [!example]- Worked Example
> **19-year-old with palpitations:** ECG shows PR 0.08 sec, QRS 0.14 sec with a subtle slurred upstroke (delta wave). Diagnosis: **WPW syndrome**. The patient is given verapamil for "SVT control." Within minutes, the heart rate accelerates to 240 bpm (the fast pathway conducts unopposed). This is a medical error — verapamil was contraindicated. Correct treatment: amiodarone, or catheter ablation of the accessory tract.

---

## QRS Duration: Conduction Speed

**Definition:** From the first deflection of the QRS to the last deflection of the S wave.

**Measurement:** Find where the QRS first moves away from baseline and where it returns to baseline. Count the interval.

**Normal range:** <120 ms (<0.12 seconds).

### **Narrow QRS (<120 ms)**

Depolarization travels down the normal His-Purkinje system. Fast, synchronized conduction. The ventricles depolarize nearly simultaneously (both left and right).

**Implies:** Normal conduction pathway (or a rhythm originating in the atria or AV node).

### **Wide QRS (≥120 ms)**

Depolarization travels slowly. The ventricles depolarize *sequentially*, not simultaneously. One ventricle is activated first (via the intact bundle branch), then the other ventricle is activated slowly via muscle-to-muscle conduction.

**Common causes:**

1. **Bundle branch block:**
   - **Right bundle branch block (RBBB):** Right ventricle conducts via slow muscle. The left ventricle depolarizes first (via intact left bundle), then electrical activity slowly spreads rightward. ECG shows an **"RSR' pattern in V1"** (R, then S, then R' — a distinctive notch).
   - **Left bundle branch block (LBBB):** Left ventricle depolarizes slowly via muscle, then the right ventricle. ECG shows a **"broad, notched R wave in V5–V6"** with ST segment changes.

2. **Ventricular ectopy:** A depolarization originates in the ventricle, bypassing the rapid His-Purkinje system. It spreads slowly, muscle to muscle. Wide QRS.

3. **Hyperkalemia:** High serum potassium slows all conduction, including ventricular. The QRS widens.

4. **Medication effects:** Some antiarrhythmics (quinidine, flecainide) slow conduction across the board. Wide QRS.

**Clinical significance:** A *new* wide QRS in a patient with chest pain is **ventricular tachycardia until proven otherwise**. A *chronic* wide QRS with stable rate/rhythm is likely bundle branch block. The context matters enormously.

> [!tip]- Retrieval Cue
> A patient presents with wide-complex tachycardia at 180 bpm. How do you determine whether this is sinus tachycardia with a bundle branch block vs. ventricular tachycardia? (Hint: look at something other than the QRS width.)

---

## QT Interval: Ventricular Repolarization Time

**Definition:** From the start of the QRS to the end of the T wave.

**Measurement:** Find the start of the QRS and the point where the T wave returns to baseline. Count the interval.

**Normal range:** Depends on heart rate. At 60 bpm, ~400 ms. At 100 bpm, ~350 ms.

**Rate correction:** Use **Bazett's formula**:

$$\text{QTc} = \frac{\text{QT (ms)}}{\sqrt{\text{RR interval (sec)}}}$$

**Normal QTc:** <440 ms (men), <450 ms (women).

### **Prolonged QT (QTc >450–500 ms)**

Repolarization is delayed. The ventricles remain in a partially repolarized state longer than normal, creating a "vulnerable window" where a premature stimulus can trigger an arrhythmia.

**Specific arrhythmia risk:** **Torsades de pointes** — a polymorphic ventricular tachycardia where the QRS axis shifts from positive to negative, creating a "twisting around the baseline" appearance. It can degenerate to V-fib and sudden cardiac death.

**Causes:**

- **Congenital long QT syndrome:** Genetic ion channel disorders (LQT1, LQT2, LQT3). Different types are triggered by different stimuli (exercise, auditory startle, sleep).
- **Drug-induced:** Antiarrhythmics (sotalol, quinidine, dofetilide), antipsychotics (haloperidol, ziprasidone), antibiotics (azithromycin, fluoroquinolones), antihistamines.
- **Electrolyte abnormalities:** Hypokalemia, hypomagnesemia, hypocalcemia. These ions regulate repolarization.
- **Bradycardia:** Slower heart rate = longer repolarization time = longer QT.
- **Female sex:** Women have longer QTc than men (hormonal effect on repolarization).

**Management:** Identify and remove the cause. If drug-induced, discontinue the offending agent. If electrolyte, correct it. If congenital, beta-blockers and sometimes implantable cardioverter-defibrillator (ICD).

### **Shortened QT (QTc <380 ms)**

Repolarization is accelerated. Risk of sudden cardiac death, but much less common than long QT.

**Causes:**
- **Hyperkalemia:** High serum potassium accelerates repolarization.
- **Hypercalcemia:** High serum calcium shortens QT.
- **Digoxin toxicity:** Can shorten QT.
- **Congenital short QT syndrome:** Rare genetic condition.

> [!question]- Feynman Check
> A patient on sotalol (an antiarrhythmic) for AFib develops QTc prolongation to 520 ms. They're prescribed azithromycin for a respiratory infection. Two weeks later, they have a syncopal episode with polymorphic VT on the monitor. Explain the mechanism step-by-step: how did QT prolongation lead to torsades, and why was the drug combination dangerous?

---

## ST Segment: The Isoelectric Baseline

**Definition:** From the end of the QRS to the start of the T wave.

**Measurement:** Measure the voltage at the J point (junction of QRS and ST segment) relative to the PR baseline (the flat segment between the end of the P wave and the start of the QRS). Normal ST segment is at or very close to baseline.

**Normal ST:** At baseline (0 mV), ±1 mm elevation or depression is acceptable variation.

### **ST Elevation (>1–2 mm depending on the lead)**

Indicates acute **transmural ischemia** (full thickness of the ventricular wall is dying).

**Clinical significance:** **Acute myocardial infarction (MI).** This is an **emergency.** The patient needs immediate reperfusion (thrombolysis or catheterization).

**Localization by affected leads:**
- **Inferior MI:** ST elevation in II, III, aVF
- **Anterior MI:** ST elevation in V1–V4 (septal/anterior)
- **Lateral MI:** ST elevation in I, aVL, V5–V6
- **Posterior MI:** ST *depression* in V1–V2 (reciprocal to posterior wall)

### **ST Depression (>1–2 mm)**

Indicates **subendocardial ischemia** (the inner layer of the ventricle is undersupplied, but the outer layer is still OK).

**Clinical significance:** Ongoing ischemia, but not yet transmural. Could progress to MI if not treated.

**Context matters:** ST depression can also appear as a *reciprocal change* in leads opposite to the infarcted territory. In an inferior MI, anterior leads (V1–V2) show ST depression.

> [!example]- Worked Example
> **55-year-old man with 30 minutes of substernal chest pain:**
> - ECG shows ST elevation in II, III, aVF (≥2 mm).
> - Reciprocal ST depression in V1–V2.
> - Diagnosis: **Acute inferior STEMI**.
> - Action: Activate catheterization lab. Patient needs urgent coronary angiography and percutaneous coronary intervention (PCI) to restore blood flow to the right coronary artery.

---

## Summary

ECG intervals encode *timing*. PR reflects AV node function (slow = block, fast = bypass). QRS reflects ventricular conduction (narrow = normal, wide = block or ectopy). QT reflects repolarization (prolonged = torsades risk, shortened = less common but still pathologic). ST reflects myocardial perfusion (elevation = acute transmural ischemia, depression = subendocardial ischemia). Abnormal intervals point to specific pathophysiology — and often demand immediate action (STEMI) or medication changes (long QT drug interactions).

---

## Cross-Field Connections
- **Electrophysiology:** Ion channels, action potential duration, repolarization (PHYS 200)
- **Ischemia:** Myocardial blood supply, metabolic injury, ST changes in real time (pathology/A&P)
- **Pharmacology:** Drug effects on conduction and repolarization, drug interactions (pharmacology)
- **Clinical:** Acute MI recognition, treatment urgency, medication safety (clinical medicine)
