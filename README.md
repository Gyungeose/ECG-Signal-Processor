# ECG-Signal-Processor
HELLO! This is my very first coding venture, hence I'm just punching in the dark. Nonetheless the goal here is to build:

This project implements a digital signal processing (DSP) pipeline to analyze raw electrocardiogram (ECG) data. Using the MIT-BIH Arrhythmia Database, the software filters biological and environmental noise, detects QRS complexes, and calculates Heart Rate Variability (HRV)—a key metric for autonomic nervous system health.

## Clinical Significance

In clinical practice, raw ECG signals are often obscured by "noise" such as electromyographic (EMG) interference from muscle tremors or baseline wander from respiration. 
* **The Goal:** To automate the transition from noisy raw data to clean, interpretable waveforms.
* **HRV Analysis:** By measuring the R-R interval variation, this tool provides insights into the risk of sudden cardiac death and autonomic dysfunction.

## The Physics

To process cardiac data, we must account for the following physical properties:
* **Voltage Dynamics:** Standard ECG signals range between **0.5mV and 5mV**. The software must maintain this scale during amplification and filtering.
* **Spectral Interference:** Environmental noise typically occurs at **60Hz** (power lines), while respiratory drift occurs at low frequencies (<0.5Hz).
* **Digital Filtering:** I implemented a **Butterworth Bandpass Filter** to isolate the 0.5Hz - 45Hz range, which contains the majority of the QRS complex energy.

## Methodology

The processing pipeline follows these engineering steps:
1. **Data Ingestion:** Utilizing the `wfdb` library to stream patient records from PhysioNet.
2. **Signal Conditioning:** Application of a second-order Butterworth filter to eliminate baseline wander and high-frequency noise.
3. **QRS Detection:** Utilizing a derivative-based approach to identify the steep slope of the R-wave, followed by a moving-window integrator to highlight the energy peaks.
4. **Analytics:** Calculation of the **Root Mean Square of Successive Differences (RMSSD)** to quantify HRV.

## Result

### Raw Signal (Before Processing)
*(Insert your first plot screenshot here)*

### Filtered Signal (After Processing)
*(Coming Soon in Phase 2)*
