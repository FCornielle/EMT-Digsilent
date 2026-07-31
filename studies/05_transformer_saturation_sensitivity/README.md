# Study 05 — Transformer Saturation and Residual-Flux Sensitivity

> **Status: planned.** This study extends Study 03 after its nonlinear model is
> verified.

## Industrial question

How sensitive are inrush, flux, harmonic restraint, and voltage recovery to the
magnetizing curve, knee point, air-core reactance, losses, residual flux, and
model initialization?

## Method

1. reuse the verified Study 03 network and event definitions;
2. define reviewed nonlinear-curve variants without silently rescaling them;
3. sweep residual-flux magnitude and polarity by limb;
4. repeat governing switching angles and pole-scatter cases;
5. rank current/flux/harmonic KPIs and quantify parameter sensitivity;
6. separate numerical non-convergence from physical saturation severity.

## Main KPIs

- peak current and flux;
- saturation duration per half-cycle;
- harmonic ratios used by transformer differential protection;
- decay constant and waveform asymmetry;
- local/global sensitivity coefficients for uncertain inputs.

## Required figures and completion gate

Required outputs are magnetizing-curve overlays, current/flux waveforms,
residual-flux heatmaps, parameter tornado plots, harmonic comparisons, and
convergence checks. Completion depends on Study 03 and requires a reviewed
parameter-provenance register plus reproducible worst-case search.
