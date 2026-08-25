# Changelog

All notable changes are documented in this file. The project follows
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Reusable Python interface for PowerFactory internal and external execution.
- First industrial study: 230 kV overhead-line energization.
- Point-on-wave scenario generation, EMT result export, metrics and plots.
- Offline tests for configuration, scenarios and post-processing.
- Native PowerFactory `IntGrfnet` generation and interactive PNG export.
- Analytical travelling-wave checks and automatic baseline comparison.
- Worst-angle time-step sensitivity from 20 us down to 1.25 us.
- Educational parameter, sweep, envelope, travelling-wave and convergence figures.
- Study-specific README contracts for all twelve industrial cases.
- Study 02 cable-energization engineering basis, bonding matrix, analytical checks,
  figures, and tests.
- Catalogue-derived Study 02 `TypCab`/`TypCabsys`/`ElmCabsys` builder, explicit
  core/sheath circuits, native diagram layout, and internal PowerFactory scripts.
- PowerFactory 2024 integration read-back and fit fingerprints that avoid
  recalculating unchanged frequency-dependent cable parameters.
- Compact four-role delivery architecture with explicit Power Systems PhD and
  QA review gates.
- Engine-verified Studies 03–08, including transformer inrush, capacitor
  switching, magnetic sensitivity, breaker TRV, variable-clearing faults, and
  native lightning travelling waves.
- Restorable PFD archives, compact executed-result evidence, SHA-256 manifests,
  and educational figures for every engine-verified Study 03–08 case.

### Changed

- Rewrote all technical documentation, labels and generated reports in English.
- Expanded Study 01 into a numbered, reproducible engineering methodology.
- Replaced the synthetic one-line drawing with a PowerFactory-linked diagram.
- Reorganized the root README as a concise multi-study technical index.
