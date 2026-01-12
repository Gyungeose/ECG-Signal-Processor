# ECG-Signal-Processor
HELLO! This is my very first coding venture, hence I'm just punching in the dark. Nonetheless the goal here is to build:

A Python-based digital signal processing tool to filter raw ECG data and analyze Heart Rate Variability (HRV) using the MIT-BIH database.

**WHAT?**  
A Python-based digital signal processing tool to filter raw ECG data, clean it using physics-based filters, identify the R-peaks, and performs a statistical analysis on the Heart Rate Variability (HRV) using the MIT-BIH database.

**WHY?**	
Raw ECG data is often full of noise (muscle tremors, breathing interference, etc.). We need clean signals. Furthermore, HRV (the variation in time between beats) is a critical biomarker for autonomic nervous system health and sudden cardiac death risk.

**HOW?**	
1. Signal Processing: Use the Pan-Tompkins Algorithm logic (math-heavy).\
2. Filtering: Apply a "Bandpass Filter" to remove non-cardiac noise.\
3. Peak Detection: Use calculus (derivatives) to find the sharpest point of the QRS complex.\
4. Visualization: Plot the results using professional-grade libraries.
