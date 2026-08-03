# EMT Industrial Study Roadmap

The studies are delivered as vertical slices. Each slice contains a technical
README and, as it matures, configuration, model builder, scenario generator,
result contract, plots, tests, and compact references. The common review
sequence is defined in [`case_methodology.md`](case_methodology.md).

| ID | Industrial study | Main KPI | Status |
|---:|---|---|---|
| 01 | [230 kV line energization and point on wave](../studies/01_line_energization/README.md) | open-end peak overvoltage | Verified baseline |
| 02 | [HV cable energization with sheath/bonding alternatives](../studies/02_hv_cable_energization/README.md) | core/sheath voltage and current | Verified EMT baseline; visual and sensitivity extensions pending |
| 03 | [Power-transformer energization](../studies/03_transformer_energization/README.md) | inrush, flux, harmonic content | Planned |
| 04 | [Shunt-capacitor bank energization](../studies/04_capacitor_bank_energization/README.md) | peak/inrush frequency and duty | Planned |
| 05 | [Transformer saturation sensitivity](../studies/05_transformer_saturation_sensitivity/README.md) | residual flux and inrush envelope | Planned |
| 06 | [Circuit-breaker TRV](../studies/06_circuit_breaker_trv/README.md) | RRRV and peak TRV | Planned |
| 07 | [Faults with variable clearing](../studies/07_faults_variable_clearing/README.md) | peak current, DC offset, I²t | Planned |
| 08 | [Lightning impulse and travelling waves](../studies/08_lightning_travelling_waves/README.md) | insulation stress and arrester energy | Planned |
| 09 | [Detailed grid-following/grid-forming IBR](../studies/09_detailed_ibr_models/README.md) | control response and current limiting | Planned |
| 10 | [Instantaneous protection](../studies/10_instantaneous_protection/README.md) | relay pickup/trip and selectivity | Planned |
| 11 | [Parametric sweeps and Monte Carlo](../studies/11_parametric_monte_carlo/README.md) | ranked risk distribution | Foundation implemented |
| 12 | [EMT–EMT and RMS–EMT co-simulation](../studies/12_emt_cosimulation/README.md) | boundary accuracy and runtime | Planned |

## Delivery sequence

1. Maintain the verified Study 01 regression loop.
2. Complete Study 02 numerical-sensitivity extensions and the collaborative
   native-diagram presentation without changing its frozen electrical topology.
3. Add transformer energization because it introduces nonlinear initialization,
   residual flux, and harmonic metrics reusable by later studies.
4. Add variable-clearing fault and TRV cases, sharing event/protection utilities.
5. Add lightning, IBR, and co-simulation after the passive-network regression
   suite is stable.

## Definition of done for every implemented study

- Industry question and decision criterion are explicit.
- Parameters distinguish example, vendor, measured, calculated, and assumed data.
- Model is built/updated through the Python API.
- The linked native PowerFactory single-line diagram is generated and exported.
- Units, bases, and monitored result-variable codes are versioned.
- At least one analytical or published benchmark is documented.
- Time-step and parameter sensitivities are included.
- Raw CSV, normalized CSV, multiple figures, and report are generated automatically.
- A numbered methodology explains model preparation, events, results, and interpretation.
- Offline unit tests and explicit PowerFactory integration checks are defined.
- Result figures are generated from verified simulation output, not synthetic data.
