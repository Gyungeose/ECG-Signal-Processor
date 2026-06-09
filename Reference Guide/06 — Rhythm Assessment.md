## The Central Question

The rhythm section of an ECG interpretation answers: **Is the heartbeat originating from the right place, and is the electrical activity moving through the heart in the right way?**

It's not asking "Is the heart fast or slow?" (that's rate). It's asking "Is this normal sinus rhythm, or is something *initiating* the heartbeat abnormally, or is something *blocking* electrical conduction?"

---

## Step 1: Is the Rhythm Regular?

**March out the R peaks.**

Take a piece of paper and mark the position of each R wave on the edge. Slide the paper along the ECG. Do the marks align perfectly with the next R waves? If yes, the rhythm is **regular**. If the spacing jumps around, it's **irregular**.

In automated systems, this is quantified as the **coefficient of variation (CV)** of the RR intervals:

$$\text{CV} = \frac{\text{Standard Deviation of RR}}{\text{Mean RR}} \times 100\%$$

- **CV < 5%:** Regular rhythm (all RR intervals nearly identical).
- **CV 5–15%:** Slightly irregular (normal sinus arrhythmia or occasional ectopy).
- **CV > 15%:** Markedly irregular (atrial fibrillation or frequent ectopy).

> [!tip]- Retrieval Cue
> If the RR intervals are 800, 810, 795, 820, 805 ms (all clustered around 810), is this rhythm regular or irregular? How would you quantify it?

---

## Step 2: P Waves — Is There One P Before Every QRS?

Look at the ECG strip and ask:

1. **Can you see P waves at all?** Some rhythms (like atrial fibrillation) have no organized P waves — just chaotic baseline.

2. **If you can see P waves, is there exactly one P for every QRS?** Normal sinus rhythm: yes. Atrial flutter with 2:1 conduction: no (2 P waves for every 1 QRS). Heart block: no (P waves present but not conducting).

3. **Is the P wave *before* the QRS (where it should be)?** Or is it *after* the QRS? If it's after, depolarization originated in the ventricles (ectopic) or the AV node (junctional).

**P wave morphology in normal sinus rhythm:**
- **Lead II:** Upright and smooth (depolarization moving from RA toward LV).
- **Lead aVR:** Inverted (looking away from the wavefront).
- **Lead V1:** Often biphasic (the RA component is close, the LA component is far).

If the P wave morphology is abnormal in these leads, suspect an ectopic atrial rhythm.

> [!example]- Worked Example
> **Patient with palpitations:** ECG shows:
> - Regular rhythm, rate 140 bpm.
> - QRS narrower than 0.12 seconds.
> - P wave is *inverted* in lead II and *upright* in lead aVR.
>
> What's happening? The P wave is backward from normal (should be upright in II, inverted in aVR). This means depolarization is moving *away from* lead II and *toward* lead aVR — opposite of normal. **Conclusion: ectopic atrial rhythm** (probably originating from the left atrium or inferior right atrium). This is an **atrial tachycardia**, not sinus tachycardia.

---

## Step 3: Is There a QRS After Every P Wave?

**Conduction**, not just *initiation*, matters.

In normal sinus rhythm, every P wave conducts to the ventricles. The AV node passes the signal through, and a QRS follows after a fixed PR interval.

But if the AV node is slow or blocked:
- Some P waves conduct (followed by QRS).
- Some P waves don't (no QRS follows — you see a P wave stranded in the ST segment or T wave).

This is **AV block**.

### **AV Block Grades**

| **Degree** | **Definition** | **ECG Finding** |
|---|---|---|
| **1st degree** | All P waves conduct, but slowly. | PR interval >0.2 sec. Every P followed by QRS, but delayed. |
| **2nd degree, Type I** | Some P waves fail to conduct; progressive PR prolongation before the failure. | PR gets longer and longer, then a beat is dropped. Then it repeats. |
| **2nd degree, Type II** | Some P waves fail to conduct without PR prolongation warning. | A P wave is suddenly *not* followed by QRS. PR interval stays constant. |
| **3rd degree (complete)** | No P waves conduct. P and QRS are entirely dissociated. | P waves visible but completely independent of QRS timing. |

> [!question]- Feynman Check
> In a complete AV block (3rd degree), the ventricles are still contracting and the patient's heart is still beating. Where is the rhythm *originating* if not from the SA node?

---

## Sinus Rhythm: The Gold Standard

**Definition:** Normal sinus rhythm (NSR) has all of:

1. **Regular rate:** RR intervals constant (CV < 5%).
2. **Rate 60–100 bpm** (in adults at rest).
3. **Upright P waves in lead II** (depolarization moving down and left, toward the electrode).
4. **One P before each QRS** (1:1 conduction).
5. **Constant PR interval** (AV node delay is consistent).
6. **Narrow QRS** (<0.12 sec; depolarization travels via normal His-Purkinje system).
7. **Normal QRS axis** (typically between -30° and +90°; covered in LN07).

**If any of these are violated, it's *not* normal sinus rhythm.**

---

## Regular vs. Irregularly Irregular

### **Regularly Irregular**
The rhythm follows a *pattern*. Examples:

- **Sinus arrhythmia:** The RR intervals change with respiration. Faster on inspiration, slower on expiration. The pattern repeats with each breath cycle.
- **Second-degree AV block (Type I):** Every 3rd beat is dropped. The RR intervals repeat: short, short, long, short, short, long...
- **Atrial flutter with variable conduction:** Organized atrial rate (flutter waves at 300 bpm) but variable number of flutter waves conducting to the ventricles. Often 2:1 (two flutter waves per QRS), sometimes 3:1, sometimes 4:1 — the pattern varies but might have a recurring sequence.

### **Irregularly Irregular**
No pattern. Every RR interval is different. This is the **hallmark of atrial fibrillation (AFib)**.

**Why?** In AFib, the atrial tissue is firing chaotically at 400–600 bpm. The AV node is bombarded with irregular stimuli and conducts a *random subset* — some early, some late, some not at all. The result: completely unpredictable RR intervals.

```
AFib:        R____R_R____R___R_R_____R____R_R
             └──┘└┘└───┘└──┘└┘└────┘└──┘└┘
             
Every interval is different.
```

> [!example]- Worked Example
> **Patient on telemetry:** Strip shows HR 80–120, varying beat to beat. No P waves visible. Baseline is chaotic. This is **atrial fibrillation with rapid ventricular response**. The AV node is conducting maybe 40–50% of the atrial impulses, resulting in a mean rate around 100 bpm, but each RR interval is unpredictable. The chaotic baseline is **fibrillation waves** — the electrical noise of the disorganized atrium.

---

## Systematic Rhythm Assessment Algorithm

1. **Can you identify R peaks?** If not, noise or V-fib. Move to emergency interventions.

2. **Calculate RR intervals.** Are they regular (CV < 5%) or irregular?

3. **Look for P waves.**
   - If no organized P waves (chaotic baseline): AFib or V-fib. Look at QRS width to distinguish.
   - If organized P waves: proceed to step 4.

4. **Count P waves vs. QRS complexes.**
   - 1 P per QRS, PR constant: likely sinus rhythm. Confirm rate 60–100 and QRS narrow.
   - Multiple P per QRS (e.g., 2 P per QRS in atrial flutter): flutter or other organized atrial arrhythmia.
   - P not followed by QRS: AV block (degree depends on pattern).

5. **Check QRS width.**
   - Narrow (<0.12 sec): conduction down normal His-Purkinje.
   - Wide (≥0.12 sec): either bundle branch block or ectopic (ventricular or aberrant conduction).

6. **Clinical context:** Is the patient symptomatic? Hemodynamically stable? This guides urgency of treatment.

---

## Clinically Critical Rhythms

| **Rhythm** | **Key ECG Signs** | **Urgency** |
|---|---|---|
| **Sinus tachycardia** | Regular, upright P in II, 100–150 bpm. | Find underlying cause (fever, pain, hypoxia). |
| **Atrial fibrillation** | Irregular, no P waves, chaotic baseline. | Rate control; stroke prevention (anticoagulation). |
| **Atrial flutter** | Regular or regularly irregular, flutter waves at ~300/min, often 2:1 conduction. | Rate control; consider cardioversion. |
| **Ventricular tachycardia** | Wide QRS (>0.12), regular or slightly irregular, rate 140–250. | Immediately life-threatening; needs defibrillation or pacing. |
| **Ventricular fibrillation** | Chaotic, no organized complexes. | Cardiac arrest; CPR + defibrillation. |
| **Complete AV block** | P and QRS completely dissociated, P rate faster than QRS rate. | Symptomatic: pacing required. |

---

## Summary

Rhythm assessment is about understanding *where* the heartbeat originates and *how* it propagates through the heart. A systematic approach — checking regularity, P-wave morphology, P-QRS relationships, conduction patterns — reveals pathology. Normal sinus rhythm is the gold standard: regular, 60–100 bpm, with organized P waves, 1:1 conduction, and narrow QRS. Deviations point to specific pathologies: ectopy, block, fibrillation, or flutter.

---

## Cross-Field Connections
- **Physiology:** SA node firing, AV node conduction, His-Purkinje propagation (A&P/PHYS)
- **Pathophysiology:** Arrhythmia mechanisms, reentry, automaticity (pathology)
- **Clinical:** Symptoms, hemodynamics, treatment options (clinical medicine)
