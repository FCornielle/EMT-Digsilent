# Study 03 — Power-Transformer Energization and Inrush

> **Status: planned.** This README defines the implementation contract; it does
> not contain simulated results.

## Industrial question

Which breaker-closing point on wave and residual-flux state produce the highest
transformer inrush, asymmetric flux, harmonic content, voltage depression, and
protection duty for a representative HV/MV transformer?

## Target PowerFactory model

- Thevenin source and three-pole energizing breaker.
- Detailed two- or three-winding transformer with vector group and zero-sequence
  path matching the application.
- Nonlinear magnetizing characteristic with air-core slope and hysteresis
  treatment supported by the selected model.
- Configurable residual flux per limb and realistic pre-energization topology.
- Native PowerFactory one-line and instantaneous EMT result channels.

## Scenario matrix

1. phase-A closing angle sweep over one electrical cycle;
2. independent pole scatter;
3. residual-flux magnitude and polarity per limb;
4. source-strength and operating-voltage sensitivity;
5. unloaded and auxiliary-load conditions;
6. controlled-switching versus uncontrolled closing.

## Main KPIs

- peak and RMS phase current;
- current asymmetry and decay time;
- peak core flux per limb;
- second-harmonic and selected harmonic ratios;
- bus-voltage depression and recovery;
- CT/relay instantaneous-current duty.

## Required figures

- native transformer one-line and nonlinear magnetizing curve;
- phase currents and limb fluxes;
- harmonic spectrum versus time window;
- point-on-wave × residual-flux heatmap;
- worst-case ranking and time-step convergence.

## Completion gate

Implemented status requires a verified nonlinear PowerFactory model, residual
flux initialization, deterministic scenario manifest, EMT CSV export, harmonic
analysis, analytical flux/current checks, convergence study, and a versioned
baseline.
