# EMT industrial study roadmap

The studies are delivered as vertical slices. Each slice contains a model
builder, configuration, scenario generator, result contract, plots, tests and a
technical README. The common review sequence is defined in
[`case_methodology.md`](case_methodology.md).

| ID | Industrial study | Main KPI | Status |
|---:|---|---|---|
| 01 | 230 kV line energization and point-on-wave | open-end peak overvoltage | Implemented |
| 02 | HV cable energization with sheath/bonding alternatives | core/sheath voltage and current | Planned |
| 03 | Power-transformer energization | inrush, flux and harmonic content | Planned |
| 04 | Shunt-capacitor bank energization/back-to-back switching | peak/inrush frequency and duty | Planned |
| 05 | Transformer saturation sensitivity | residual flux and inrush envelope | Planned |
| 06 | Circuit-breaker TRV | RRRV and peak TRV against envelope | Planned |
| 07 | SLG, LL and 3LG faults with variable clearing | peak current, DC offset and I²t | Planned |
| 08 | Lightning impulse and travelling waves | terminal BIL stress and arrester energy | Planned |
| 09 | Detailed grid-following/grid-forming IBR model | control response and current limiting | Planned |
| 10 | Instantaneous protection study | relay pickup/trip and selectivity | Planned |
| 11 | Parametric sweeps, Monte Carlo and worst-case search | ranked risk distribution | Foundation implemented |
| 12 | EMT–EMT and RMS–EMT co-simulation | boundary accuracy and runtime | Planned |

## Delivery sequence

1. Validate the complete Study 01 loop on the installed PowerFactory version.
2. Add transformer energization because it introduces nonlinear initialization,
   residual flux and harmonic metrics reusable by several later studies.
3. Add variable-clearing fault and TRV cases, sharing event/protection utilities.
4. Add cable/lightning studies with geometric and frequency-dependent models.
5. Add IBR and co-simulation after the passive-network regression suite is
   stable.

## Definition of done for every study

- Industry question and decision criterion are explicit.
- Parameters distinguish example, vendor, measured and assumed data.
- Model is built/updated through the Python API.
- The linked native PowerFactory single-line diagram is generated and exported.
- Units, bases and monitored result-variable codes are versioned.
- At least one analytical or published benchmark is documented.
- Time-step and parameter sensitivities are included.
- Raw CSV, normalized CSV, multiple figures and report are generated automatically.
- A numbered methodology explains model preparation, events, results and interpretation.
- Offline unit tests and explicit PowerFactory integration checks are defined.
