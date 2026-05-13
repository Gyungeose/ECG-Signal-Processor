## Chapter 1: The Heart as an Electrical Machine

Most people think of the heart as a pump — and it is — but what _drives_ the pump is electricity. Your heart beats because of an electrical signal that travels through it in a very specific, predictable path. Every single beat follows the same route.

Here's that path visualised:

Here's the electrical highway the signal travels through your heart with every single beat:

![[Pasted image 20260331152924.png]]

---
### **What you're looking at**

Your heart has four chambers. The top two are called **atria** — they receive blood. The bottom two are called **ventricles** — they pump it out. The right side handles blood going to the lungs; the left side handles blood going to the body.

Every heartbeat starts with an electrical signal that travels through all four chambers in a very specific order. Here's the journey, step by step:

**Step 1 — The SA Node fires** Deep in your right atrium sits a tiny cluster of cells called the **sinoatrial node** (SA node). This is your heart's natural pacemaker. Without any input from your brain, it spontaneously generates an electrical impulse about 60–100 times per minute. That spark travels outward like a ripple across a pond — spreading across both atria and causing them to squeeze and push blood down into the ventricles.

**Step 2 — The AV Node acts as a gate** The signal can't just rush straight into the ventricles — there's a deliberate pause built in. The **atrioventricular node** (AV node) sits at the junction between the atria and ventricles and holds the signal for about 120–200 milliseconds. This delay is critical — it gives the atria time to finish squeezing and fully empty blood into the ventricles before the ventricles contract.

**Step 3 — The Bundle of His carries the signal down** Once through the AV node, the signal travels down a highway called the **Bundle of His** — a bundle of specialized conductive fibers that splits into a left branch and a right branch, one for each ventricle.

**Step 4 — The Purkinje Fibers spread the signal** The branches fan out into a web called the **Purkinje fibers**, which deliver the electrical impulse simultaneously to the bottom of both ventricles. This causes them to contract from the bottom up — squeezing blood upward and out into the arteries.

---
### **Why does any of this produce a signal you can measure on the skin?**

When millions of heart muscle cells fire electrically all at once, they create a detectable electrical field — strong enough that it radiates all the way through your chest and can be picked up by electrodes on your skin. That is what an ECG is measuring. It's not measuring the mechanical pumping. It's measuring the **electrical waves** that cause the pumping.

Which brings us to the most important shape in your entire codebase — the ECG waveform. Let's look at it next:

![[Pasted image 20260331153035.png]]

---
### **Meet the PQRST waveform — the fingerprint of a heartbeat**

Every heartbeat produces this exact shape on an ECG. Each letter represents a different electrical event:

**The P wave** is a small, gentle bump. It represents the electrical signal spreading across the atria (Step 1 from above). When you see a P wave, the atria are contracting and pushing blood into the ventricles. It's small because the atria are small muscles.

**The PR interval** is the flat line between the P wave and the QRS. This is the AV node doing its job — the deliberate pause (Step 2). Clinically, if this interval is too long, it suggests the AV node is struggling to conduct the signal (a condition called a "heart block").

**The QRS complex** is the dramatic spike — a quick dip down (Q), a tall sharp peak (R), then another dip (S). This is the electrical signal exploding through the ventricles via the Purkinje fibers (Steps 3 and 4). The ventricles are huge, powerful muscles, which is why this deflection is so much larger than the P wave. **This is the event your code is entirely built around detecting.** The sharp peak — the R — is called the R-peak.

**The ST segment** is the flat pause after the QRS. The ventricles are in the middle of contracting. Clinically, this segment is extremely important — a raised or depressed ST segment can indicate a heart attack. Your project doesn't analyze this yet, but it's on the roadmap.

**The T wave** is the final rounded bump. It represents the ventricles electrically "resetting" — recovering and preparing for the next beat. This is called repolarization.

---
### **The two numbers that matter most to your project**

**RR interval** — the time from one R-peak to the next R-peak. This tells you how long one complete heartbeat took. From this single measurement you can calculate:

- Heart rate (beats per minute)
- Whether the rhythm is regular or irregular

**RMSSD** — what happens when you measure many consecutive RR intervals and calculate how much they vary from each other. A healthy heart doesn't beat like a metronome — it speeds up slightly when you inhale and slows down when you exhale. This variation is healthy. It's controlled by the autonomic nervous system (the part of your nervous system that works automatically). Low variability can be a sign of cardiac risk.

---

## Chapter 2: The Noise Problem

Here's the brutal reality of measuring electricity through skin — your body is a terrible conductor surrounded by a world full of competing electrical signals. The ECG machine is trying to listen to a whisper (your heart) in a very loud room.

There are three main villains, and your code fights all of them.

---

![[Pasted image 20260331154249.png]]

---
### **The three enemies**

**Baseline wander** is the slowest and most predictable noise. Every time you breathe, your chest wall moves, and the electrodes sitting on your skin shift ever so slightly. This changes the electrical contact, causing the entire ECG signal to slowly drift up and down like a wave — at the same frequency as your breathing, roughly 0.2–0.5 Hz (that means less than once per second). The heartbeat signal is still there, but it's riding on top of a slow rolling hill instead of a flat road. This makes it very hard to measure precise voltages.

**Powerline interference** is the most recognisable noise if you've ever seen a raw ECG. Every electrical wire in the building carries alternating current at 60 Hz in North America (50 Hz in most other countries, which is why your code mentions both). This creates an invisible electromagnetic field that your electrode wires act as antennas for — picking up a 60-cycle-per-second buzz and layering it over the heartbeat signal. On a screen it looks like the ECG waveform has grown fur. Your code has a notch filter planned for Phase 1 of the roadmap specifically to kill this.

**Muscle noise (EMG)** is the most chaotic. Every muscle in your body produces small electrical signals when it contracts — that includes the muscles right under the electrodes. A patient who is anxious, shivering, has tremors, or is simply tense will contaminate the ECG with broadband electrical noise across a wide range of frequencies (20–500 Hz). This one is the hardest to remove cleanly because its frequency range partially overlaps with the heart signal itself.

---
### **The key insight that makes filtering possible**

Here's the beautiful thing — and this is the entire conceptual foundation of your filtering code:

> **Each type of noise lives at a different frequency than the signal you actually care about.**

Frequency, in this context, just means _how fast something repeats per second_. Measured in **Hertz (Hz)**.

- Baseline wander: very slow — below **0.5 Hz**
- The useful cardiac signal (PQRST): **0.5 to 40 Hz**
- The QRS complex specifically (the sharp spike): **5 to 15 Hz** — it's steep and fast
- Powerline noise: exactly **60 Hz**
- Muscle noise: **20 Hz and above**

Visualise it like this:

![[Pasted image 20260331155339.png]]

---
### **What a filter actually is**

A filter is simply a tool that **lets some frequencies through and blocks others** — exactly like a physical filter. A coffee filter lets water through but blocks coffee grounds. A sunscreen filter lets visible light through but blocks UV.

Your code uses three conceptual types:

A **high-pass filter** lets everything _above_ a certain frequency through, and blocks everything below. Your code uses one set at **0.5 Hz** — it lets all the fast heart signal through, but blocks the slow baseline wander crawling underneath it.

A **bandpass filter** lets only a specific _range_ of frequencies through — blocking both below and above. Your code uses one set to **5–15 Hz** specifically to isolate the QRS complex for detection. Everything outside that band — the wander, the 60 Hz buzz, most of the muscle noise — gets blocked.

A **notch filter** is a very narrow bandpass _blocker_ — it removes one precise frequency and lets everything else through. Your roadmap mentions adding one at 60 Hz to surgically cut the powerline interference without disturbing any of the cardiac signal around it.

---
### **Before we go further — one concept you need to understand: sampling rate**

Your code works with **digital** signals, not analog ones. Real ECG machines convert the continuous electrical signal from the body into a series of numbers by taking a measurement — a **sample** — thousands of times per second.

Your code uses the MIT-BIH database which was recorded at **360 Hz**, meaning 360 measurements per second. This number appears constantly in your code — it's stored in the variable `fs` (for _frequency of sampling_). Every time you see `fs` in your code, just think: _"360 snapshots per second."_

Why does that matter? Because when you want to say "the filter cuts off at 0.5 Hz," the computer doesn't work in Hz directly — it works in fractions of the sampling rate. You'll see this exact conversion in your code:

```python
nyq = 0.5 * fs       # Nyquist frequency = 180 Hz (the maximum frequency you can represent)
normal_cutoff = cutoff / nyq   # Convert 0.5 Hz → 0.00278 (a fraction the filter understands)
```

That line `nyq = 0.5 * fs` is not magic — it's just physics. You can only represent frequencies up to half your sampling rate. At 360 Hz sampling, the highest frequency you can meaningfully capture is 180 Hz. This limit has a name — the **Nyquist frequency** — and your code calculates it every single time it builds a filter.

---

## Chapter 3: The Butterworth Filter — How Your Code Actually Cleans the Signal

Before we touch the code, you need a mental model of what a Butterworth filter _is_. Because once you have it, every single line of the filter code will make immediate sense.

---
### **The ideal filter vs. the real filter**

Imagine you wanted a perfect high-pass filter at 0.5 Hz. Ideally it would work like a light switch — signals below 0.5 Hz get _completely_ blocked, signals above 0.5 Hz pass through _completely unchanged_. A perfectly vertical wall.

That filter does not exist in reality. Every real filter has a **slope** — a gradual transition zone where it starts cutting frequencies. The question is: how steep can you make that slope?

![[Pasted image 20260403094139.png]]

The **Butterworth filter** was designed in 1930 specifically to have the flattest possible response in the passband — meaning the frequencies you _want_ pass through with as little distortion as possible, and then it rolls off as steeply as it can toward the cutoff point.

The steepness of that rolloff is controlled by one number: the **order**. Your code uses **order 2** everywhere — a reasonable balance between sharpness and computational stability. A higher order is steeper but more likely to introduce distortions called _ringing artifacts_ in a clinical signal.

---
### **Now let's read the code — line by line**

Here is the `FilterState` class from your code. We'll go through it in pieces. First, the skeleton:

```python
@dataclass
class FilterState:
    sos: np.ndarray
    zi: np.ndarray
```

The `@dataclass` decorator just means Python will automatically handle storing these two values for you. But what _are_ they?

**`sos`** stands for **Second-Order Sections**. This is how Butterworth filters are stored mathematically — as a series of small, simple filter stages chained together. Think of it like a water purification system with multiple filter cartridges in sequence. Each cartridge (each "section") removes a specific band of impurity. `sos` is the array of those cartridge specifications.

**`zi`** stands for **filter state** (initial conditions). This is the memory of the filter — what values were at the filter's "edges" at the end of the last chunk. This is critical for streaming. Without it, each new chunk of data would start filtering from scratch, causing a glitch at every boundary. `zi` carries the context forward so the filtered signal is continuous.

---

Now the method that actually _builds_ the high-pass filter:

```python
@classmethod
def create_highpass(cls, fs: float, cutoff: float = 0.5, order: int = 2):
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    sos = butter(order, normal_cutoff, btype='high', output='sos')
    zi = np.zeros((sos.shape[0], 2))
    return cls(sos=sos, zi=zi)
```

**Line 1: `nyq = 0.5 * fs`** The Nyquist frequency. At 360 Hz sampling, this is 180. It represents the absolute maximum frequency your digital system can represent. All frequency specifications must be expressed as a _fraction_ of this number — that's the language the `butter()` function speaks.

**Line 2: `normal_cutoff = cutoff / nyq`** Converting 0.5 Hz into the filter's language. `0.5 / 180 = 0.00278`. This means: "cut off everything below 0.28% of the maximum possible frequency." This tiny number is why baseline wander — which is so slow — gets completely eliminated.

**Line 3: `sos = butter(order, normal_cutoff, btype='high', output='sos')`** This is the scipy library doing the heavy mathematics. You're telling it: build me a Butterworth filter of order 2, high-pass type, with the cutoff at `normal_cutoff`, and store it as second-order sections. What comes back is a matrix of numbers — the mathematical recipe for your filter.

**Line 4: `zi = np.zeros((sos.shape[0], 2))`** Creating the filter's memory, initialized to zero. The shape `(sos.shape[0], 2)` means: one memory slot for each filter section, with 2 values per slot. At the very start, there's no history, so all zeros.

---

Now the bandpass filter — same idea, but with two cutoffs instead of one:

```python
@classmethod
def create(cls, fs: float, lowcut: float = 5.0, highcut: float = 15.0, order: int = 2):
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    sos = butter(order, [low, high], btype='band', output='sos')
    zi = np.zeros((sos.shape[0], 2))
    return cls(sos=sos, zi=zi)
```

Identical logic — but now you pass _two_ normalized frequencies `[low, high]` and say `btype='band'`. You're telling the filter: let only the band _between_ 5 Hz and 15 Hz through. Everything outside gets blocked. This is what isolates the QRS complex for detection.

And here's the display filter — a wider band so you see the full waveform shape on screen:

```python
@classmethod
def create_display(cls, fs: float, lowcut: float = 0.5, highcut: float = 40.0, order: int = 2):
    nyq = 0.5 * fs
    sos = butter(order, [lowcut / nyq, highcut / nyq], btype='band', output='sos')
    zi = np.zeros((sos.shape[0], 2))
    return cls(sos=sos, zi=zi)
```

Same filter, wider window (0.5–40 Hz). This preserves P waves, T waves, and the ST segment — everything a clinician needs to _see_ — while still removing baseline wander below 0.5 Hz.

---

Finally, the method that _applies_ a filter to a chunk of data:


```python
def apply_chunk(self, chunk: np.ndarray) -> np.ndarray:
    filtered, self.zi = sosfilt(self.sos, chunk, zi=self.zi)
    return filtered
```

This is deceptively short for how much it does. `sosfilt` takes three things: the filter recipe (`sos`), the raw data chunk, and the current filter memory (`zi`). It returns two things: the filtered chunk, and the _updated_ memory state. That updated `zi` immediately overwrites the old one — `self.zi = ...` — so the next chunk picks up exactly where this one left off. No seam, no glitch. This is what makes real-time streaming work.

---
### **The two-stage pipeline in plain English**

When a chunk of ECG data arrives, here's what actually happens to it, in order:

```python
# Step 0 — center the signal at zero
chunk_centered = chunk - np.mean(chunk)

# Step 1 — strip baseline wander (high-pass at 0.5 Hz)
highpass_filtered = processor['highpass_filter'].apply_chunk(chunk_centered)

# Step 2a — widen for display (0.5–40 Hz, shows full PQRST)
display_filtered = processor['display_filter'].apply_chunk(highpass_filtered)

# Step 2b — narrow for detection (5–15 Hz, isolates QRS only)
filtered = processor['bandpass_filter'].apply_chunk(highpass_filtered)
```

Notice the design decision here: `display_filter` and `bandpass_filter` both receive `highpass_filtered` as input — they branch from the same point. They run in _parallel_, not in sequence. This is intentional. You don't want to display the narrow 5–15 Hz signal because it looks ugly — it strips out the P and T waves. But you don't want to detect peaks on the wide display signal either — it's noisier. Two outputs from the same pipeline, each optimized for a different purpose.

---

That's the entire filtering system demystified. You now understand:

- What a Butterworth filter is and what "order" means
- What `sos` and `zi` represent and why `zi` is essential for streaming
- What every parameter in every `butter()` call means
- Why your code has two parallel filter paths

---

## Chapter 4: The Pan-Tompkins Algorithm — Finding the Heartbeat

This is the most important chapter. Everything before this — all the filtering — was just preparation. Pan-Tompkins is the algorithm that looks at the cleaned signal and answers the one question your entire project exists to answer:

> _"Where exactly is each heartbeat?"_

It was published in 1985 by Jiapu Pan and Willis Tompkins in the IEEE journal of Biomedical Engineering. Forty years later it is still the gold standard used in real cardiac monitors. Your code implements the full version.

---
### **Why not just look for the tallest spike?**

Before we get into the algorithm, let's understand why something simple wouldn't work.

Your first instinct might be — the R-peak is the tallest point on the ECG, so just find the highest values in the signal. Done.

The problem is that after filtering, the signal still has variation. A T-wave can sometimes be nearly as tall as an R-peak. Muscle noise spikes can momentarily exceed the R-peak height. And crucially — different patients have wildly different ECG amplitudes. A signal that's "tall" for one patient might be "short" for another. A fixed threshold would miss beats in some patients and falsely detect noise in others.

Pan-Tompkins solves this by not looking at height alone — it looks at **shape**. The R-peak has a unique combination of properties that nothing else in the signal shares: it is simultaneously **tall, steep, and brief**. The algorithm is designed to amplify exactly that combination and ignore everything else.

---
### **The five stages**

Think of Pan-Tompkins as an assembly line that transforms the signal through five stages, each one making the R-peaks easier to find:

The Pan-Tompkins pipeline is a perfect candidate for a stepper — each stage transforms the signal into something new:

![[Pasted image 20260403093631.png]]
![[Pasted image 20260403093644.png]]
![[Pasted image 20260403093654.png]]
![[Pasted image 20260403093701.png|637]]
![[Pasted image 20260403093708.png]]

Now let's read the code for each stage.

---
### **Stage 1 — Differentiation**

```python
deriv = np.ediff1d(filtered_chunk, to_end=0)
```

`np.ediff1d` calculates the difference between every consecutive pair of samples. If sample 5 has a value of 0.3 mV and sample 6 has a value of 0.8 mV, the derivative at that point is 0.5. If the signal is flat — two samples with the same value — the derivative is 0.

The `to_end=0` just pads the last position with a zero since there's no "next sample" after the final one.

Why does this help? The R-peak is defined by an extremely steep slope — the signal shoots almost vertically upward in a matter of milliseconds. Differentiation makes that steepness into a giant number. Gradual slopes like T-waves produce much smaller numbers. You've just mathematically separated "things that happen fast" from "things that happen slowly."

---
### **Stage 2 — Squaring**

```python
squared = deriv ** 2
```

The simplest line in the algorithm. Every value gets multiplied by itself. This does two things at once. First, it makes every value positive — negative slopes (the signal dropping back down after the peak) were producing negative derivative values, which would cancel out the positive ones. Squaring fixes that. Second, it dramatically amplifies large values relative to small ones. If one sample has a derivative of 2 and another has 0.5, after squaring they become 4 and 0.25. The ratio went from 4:1 to 16:1. The R-peak just got much louder compared to background noise.

---
### **Stage 3 — Moving Window Integration**

```python
win_len = max(1, int((integrator_window_ms / 1000.0) * fs))
integrator = np.convolve(squared, np.ones(win_len) / win_len, mode='same')
```

This is the most elegant step. `integrator_window_ms` is 150 milliseconds, which at 360 Hz means `int(0.150 × 360) = 54 samples`. So `win_len = 54`.

`np.convolve` with `np.ones(54) / 54` is just a sliding average — at every point in the signal, replace that value with the average of the 54 samples surrounding it. Think of it like smearing the signal — a sharp isolated spike gets spread out and reduced, but a cluster of high energy samples (like the QRS complex, which lasts about 80–120 ms) stays tall because all those samples are contributing to each other's average.

The result is the smooth humped curve you saw in Stage 4 of the stepper. Those humps are easy to find the peaks of — much easier than the jagged squared signal. This output is what your code calls the **integrator**, and it gets its own plot track in your visualization.

---
### **Stage 4 — Dual Adaptive Thresholds**

This is the most medically sophisticated part of the whole algorithm. Let's read the `AdaptiveThresholdState` class carefully.

```python
@dataclass
class AdaptiveThresholdState:
    peak_values: deque = field(default_factory=lambda: deque(maxlen=8))
    noise_level: float = 0.0
    signal_level: float = 0.0
    signal_threshold1: float = 0.0
    signal_threshold2: float = 0.0
```

`deque(maxlen=8)` is a sliding list that only ever remembers the last 8 items. When a 9th item is added, the oldest one is automatically dropped. This is how the algorithm "remembers" recent peaks — not all peaks ever, just the most recent 8. This is what makes it adaptive.

Now the threshold formula:

```python
def update_thresholds(self):
    self.signal_threshold1 = self.noise_level + 0.25 * (self.signal_level - self.noise_level)
    self.signal_threshold2 = 0.5 * self.signal_threshold1
```

Read `signal_threshold1` in plain English: start at the estimated noise floor, then add 25% of the gap between the noise floor and the average signal peak. This puts T1 one quarter of the way up from noise toward the typical peak height. Not too high (would miss real beats), not too low (would trigger on noise).

T2 is simply half of T1 — a softer fallback.

Both of these values update after every detected beat, meaning if your heart rate changes, or you move and create muscle noise, the thresholds quietly adjust to follow you. This is what separates Pan-Tompkins from a naive "find values above 0.5 mV" approach — it works on every patient, in every condition, automatically.

---
### **Stage 5 — The Refractory Period and Searchback**

Two final protective mechanisms:

```python
distance = max(1, int((refractory_ms / 1000.0) * fs))
```

`refractory_ms` is 250 milliseconds. This translates to `int(0.250 × 360) = 90 samples`. Once a peak is detected, the algorithm ignores the next 90 samples entirely. Why? Because a real human heart physically cannot beat twice within 250 ms — that would be 240 beats per minute, which is essentially impossible under normal conditions. Any peak found within that window after a detection is either the tail of the same QRS complex or noise. The refractory period prevents double-counting a single heartbeat.

The searchback mechanism works in the opposite direction — if no peak has been found for longer than expected (based on the patient's recent rhythm), the algorithm drops down to T2 and looks back through the signal for anything it might have been too strict about. This is the safety net for patients with weak or irregular signals.

---
### **Deduplication — the final step**

```python
for idx in r_peaks_local:
    global_idx = start_global_idx + int(idx)
    if not any(abs(global_idx - existing) <= 3 for existing in processor['dedup_r_peaks']):
        processor['dedup_r_peaks'].append(global_idx)
        processor['all_r_peaks'].append(global_idx)
```

Remember from Chapter 3 that windows overlap by 1 second. That means the same R-peak can get detected in two consecutive chunks — once near the end of chunk 1, and again near the start of chunk 2. This loop converts every local chunk index into a global signal index, then checks whether a peak within 3 samples of it has already been recorded. If so, it's a duplicate and gets skipped. This is what `dedup_r_peaks` is for — it's the running list of all globally confirmed unique beats.

That's Pan-Tompkins completely demystified. You now understand every single line of `detect_qrs_chunk` — not just what it does but _why_ each transformation was designed that way.

---
## Chapter 5: RMSSD and the Streaming Architecture

Two topics left. The first is short but clinically deep — it's the metric that gives your project its medical value. The second is the engineering backbone that makes everything run in real time.

---
### **Part A: RMSSD — What Your Project Actually Measures**

You've filtered the signal, found the R-peaks, and recorded when each one occurred. Now what?

The end goal was never just to _find_ heartbeats. It was to learn something meaningful about the person's health from the pattern of those heartbeats. That's where RMSSD comes in.

Let's build up the concept in three steps.

---

**Step 1 — RR intervals**

Once you have a list of R-peak positions (in samples), you convert them to times in milliseconds and subtract consecutive ones:

```python
times_ms = (r_peak_indices / float(fs)) * 1000.0
rr_ms = np.diff(times_ms)
```

`np.diff` just subtracts each value from the next one. If your R-peaks occurred at 0 ms, 860 ms, 1710 ms, 2580 ms — your RR intervals are [860, 850, 870] ms. From those you can calculate heart rate instantly: 60,000 ÷ 860 ≈ 70 bpm.

But heart rate alone is a blunt instrument. A heart beating at exactly 70 bpm every single beat, with robotic regularity, would actually be a _clinical warning sign_. A healthy heart is slightly irregular — and that irregularity is the signal.

---

**Step 2 — Successive differences**

```python
successive_diffs = np.diff(rr_ms)
```

Another `np.diff` — but this time on the RR intervals themselves, not the peak times. You're calculating how much each beat-to-beat gap _changed_ from one beat to the next.

Using our example: RR intervals [860, 850, 870] → successive differences [−10, +20] ms.

This captures the moment-to-moment variation in your heart rhythm. A healthy autonomic nervous system constantly makes tiny adjustments — speeding up the heart when you inhale, slowing it down when you exhale. This is called **respiratory sinus arrhythmia**, and it's normal and healthy. The successive differences capture exactly this micro-variation.

---

**Step 3 — The RMSSD formula**

```python
rmssd = np.sqrt(np.mean(successive_diffs ** 2))
```

Square every successive difference → take the mean → take the square root. This is the exact same mathematical structure as a standard deviation, but applied to beat-to-beat changes rather than raw values.

Why square before averaging? The same reason as in Pan-Tompkins — squaring makes negative differences (heart slowing down) and positive ones (heart speeding up) both contribute positively to the total. You care about the _magnitude_ of variation, not the direction.

Here's the full function from your code — it's beautifully concise:

```python
def compute_rmssd(r_peak_indices, fs):
    if len(r_peak_indices) < 3:
        return float('nan')
    times_ms = (r_peak_indices / float(fs)) * 1000.0
    rr_ms = np.diff(times_ms)
    successive_diffs = np.diff(rr_ms)
    rmssd = np.sqrt(np.mean(successive_diffs ** 2))
    return float(rmssd)
```

The guard `if len(r_peak_indices) < 3` is important — you need at least 3 peaks to produce 2 RR intervals, and at least 2 RR intervals to produce 1 successive difference. Below that, the calculation is mathematically meaningless, so it returns `nan` (not a number) rather than a misleading value.

---

**What RMSSD actually tells you clinically**

RMSSD is measured in milliseconds. Here's how to read it:
![[Pasted image 20260403094548.png]]

The autonomic nervous system has two branches — the sympathetic (fight or flight) and the parasympathetic (rest and digest). RMSSD primarily reflects **parasympathetic activity**, specifically the vagus nerve's influence on the heart. High vagal tone keeps the heart flexible, responsive, and variable. Low vagal tone correlates with cardiovascular disease, diabetes, and increased risk of sudden cardiac death.

This is why RMSSD is a validated clinical marker — it's not just a mathematical curiosity. It's a window into a system you can't directly observe.

And critically for your project: your pipeline already collects every piece of data needed to calculate it. The R-peaks are detected in real time. RMSSD follows naturally.

---
### **Part B: The Streaming Architecture**

Now for the engineering backbone. This is what separates your project from a simple offline signal processor — it's designed to run _forever_, on data arriving _continuously_, without needing to wait for a recording to finish.

The central idea is the `StreamingBuffer`. Let's understand it visually first:
![[Pasted image 20260403094607.png]]
![[Pasted image 20260403094620.png]]
![[Pasted image 20260403094627.png]]
![[Pasted image 20260403094634.png]]

Now let's read the `StreamingBuffer` code with that picture in your head:

```python
@dataclass
class StreamingBuffer:
    window_duration_sec: float   # 3.0 seconds
    overlap_duration_sec: float  # 1.0 second
    fs: float                    # 360 Hz

    def __post_init__(self):
        self.window_samples = int(self.window_duration_sec * self.fs)   # 1080 samples
        self.overlap_samples = int(self.overlap_duration_sec * self.fs) # 360 samples
        self.stride_samples = self.window_samples - self.overlap_samples # 720 samples
        self.buffer = deque(maxlen=self.window_samples)
```

`__post_init__` runs automatically right after the dataclass is created — it's where the real setup happens. Everything gets converted from seconds into samples by multiplying by `fs`. The `stride_samples` is the key number: 720 samples = 2 seconds. That's how far the window moves forward each time.

`deque(maxlen=1080)` is the buffer itself — a sliding list that never grows beyond 1080 items. When new samples push it past that limit, old ones fall off the left side automatically.

```python
def add_sample(self, value: float):
    self.buffer.append(value)
    self.global_sample_idx += 1

    if len(self.buffer) == self.window_samples:
        chunk = np.array(list(self.buffer), dtype=float)
        for _ in range(self.stride_samples):
            self.buffer.popleft()
        return chunk
    return None
```

This is the heartbeat of the whole pipeline. One sample arrives. It gets appended to the buffer. The global counter ticks up. Then — is the buffer full? If not, return `None` (not ready yet). If yes, snap a copy of the full 1080-sample window as a numpy array, then manually remove the 720 oldest samples (the stride), leaving 360 samples still in the buffer (the overlap). Return the chunk for processing.

---
### **How the whole pipeline flows together**

Here's the main loop that orchestrates everything:

```python
for sample in data_generator:
    chunk = processor['buffer'].add_sample(sample)

    if chunk is not None:
        process_streaming_chunk(processor, chunk, chunk_count)
        chunk_count += 1
```

`data_generator` is whichever source was selected — synthetic, CSV, serial port, or network. It yields one sample at a time. Each sample goes into the buffer. When the buffer produces a complete chunk, `process_streaming_chunk` fires. That function runs the entire pipeline: DC removal → high-pass filter → display filter → bandpass filter → Pan-Tompkins → deduplication → history update.

Then after all chunks are processed, RMSSD is computed once over all confirmed R-peaks:

```python
unique_r_peaks = sorted(processor['all_r_peaks'])
rmssd_val = compute_rmssd(np.array(unique_r_peaks), fs)
```

---
### **Why the architecture is clinically significant**

When you sit down with the sim lab director, this is the piece that matters most for real-world deployment. Offline analysis — process a recording, then report results — is easy. Real-time streaming is hard, and your code does it correctly.

Three specific design choices make it production-worthy:

The stateful filters with `zi` carry across chunks — there are no discontinuities in the filtered signal at chunk boundaries. A naive implementation would reset the filter every chunk, producing visible glitches in the waveform every 3 seconds.

The overlapping windows mean no heartbeat ever falls in a crack between chunks. A beat that happens to land right at the 3-second boundary is seen in both the current chunk and the next one, then deduplicated — so it's always detected, never lost.

The adaptive thresholds update continuously as the signal changes. If the patient moves, or the electrode contact degrades, or the heart rate changes, the algorithm quietly recalibrates. It doesn't need a human to intervene.

---
### **The complete picture**

You've now walked through every layer of this project from the ground up:

The heart generates electricity through a specific pathway — SA node → AV node → Bundle of His → Purkinje fibers — producing the PQRST waveform with every beat. Raw ECG signals are contaminated by baseline wander, powerline interference, and muscle noise, each living at different frequencies. Butterworth filters with stateful `zi` memory strip the noise while preserving cardiac signal across streaming chunk boundaries. Pan-Tompkins transforms the cleaned signal through differentiation, squaring, integration, and dual adaptive thresholding to robustly detect every R-peak regardless of patient or signal quality. RMSSD turns those R-peaks into a clinically validated marker of autonomic nervous system health. And the `StreamingBuffer` ties it all together into a pipeline that can run continuously on live hardware.

Every line of code in that project now has a reason behind it. That's genuine ownership.