# Industrial EMT Studies with DIgSILENT PowerFactory and Python

[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-3776AB.svg)](https://www.python.org/)
[![PowerFactory 2024](https://img.shields.io/badge/PowerFactory-2024-004B87.svg)](https://www.digsilent.de/)
[![Tests](https://img.shields.io/badge/tests-passing-2E8B57.svg)](#verification)

A reproducible, engineering-oriented collection of electromagnetic transient
(EMT) studies automated through the DIgSILENT PowerFactory Python API. Every
case is treated as a small software project: question, assumptions, native
PowerFactory model, scenario matrix, result contract, validation, figures, and
technical interpretation are kept together.

The repository distinguishes four maturity levels:

- **Verified baseline:** PowerFactory EMT results and regression evidence exist.
- **Implemented:** the complete model/workflow exists but may not have a frozen
  cross-version baseline.
- **Engineering basis:** inputs, methodology, analytical checks, and starter
  automation exist; EMT results are not claimed.
- **Planned:** the implementation contract exists without fabricated results.

## Study catalogue

| ID | Study | Primary decision metric | Status |
|---:|---|---|---|
| 01 | [230 kV line energization and point on wave](studies/01_line_energization/README.md) | open-end peak voltage | **Verified baseline** |
| 02 | [220 kV cable energization and sheath bonding](studies/02_hv_cable_energization/README.md) | core/screen voltage and current | **Verified baseline** |
| 03 | [Transformer energization and inrush](studies/03_transformer_energization/README.md) | inrush, flux, harmonics | Planned |
| 04 | [Capacitor-bank energization](studies/04_capacitor_bank_energization/README.md) | inrush peak/frequency and duty | Planned |
| 05 | [Transformer saturation sensitivity](studies/05_transformer_saturation_sensitivity/README.md) | residual-flux/inrush envelope | Planned |
| 06 | [Circuit-breaker TRV](studies/06_circuit_breaker_trv/README.md) | peak TRV and RRRV | Planned |
| 07 | [Faults with variable clearing](studies/07_faults_variable_clearing/README.md) | peak current, DC offset, I²t | Planned |
| 08 | [Lightning and travelling waves](studies/08_lightning_travelling_waves/README.md) | insulation stress and arrester energy | Planned |
| 09 | [Detailed grid-following/grid-forming IBR](studies/09_detailed_ibr_models/README.md) | control/current-limit response | Planned |
| 10 | [Instantaneous protection](studies/10_instantaneous_protection/README.md) | pickup, trip, selectivity | Planned |
| 11 | [Parametric sweeps and Monte Carlo](studies/11_parametric_monte_carlo/README.md) | ranked risk distribution | Foundation implemented |
| 12 | [EMT–EMT and RMS–EMT co-simulation](studies/12_emt_cosimulation/README.md) | interface accuracy and runtime | Planned |

All cases follow the same
[15-step engineering methodology](docs/case_methodology.md) and
[README review contract](docs/study_readme_template.md).

## Study 01 — verified 230 kV line energization

### Question and model

What is the maximum open-end phase-ground voltage when a 150 km, 230 kV
overhead line is energized at different points on the voltage wave?

```text
Thevenin source -> sending bus -> three-pole breaker
                 -> distributed frequency-dependent EMT line -> open end
```

The API creates the electrical network and a linked native PowerFactory
`IntGrfnet`; Matplotlib is used only for result figures.

### Verified PowerFactory results

| KPI | Result |
|---|---:|
| Maximum receiving-end voltage | **2.2570 pu / 423.85 kV peak** |
| Governing voltage angles | **30, 90, 150, 210, 270, 330 degrees** |
| Maximum sending-end current | **0.865571 kA peak** |
| Governing current angles | **0, 60, 120, 180, 240, 300 degrees** |
| Point-on-wave cases | **12** |
| EMT time-step verification | **20 to 1.25 us** |

The full assumptions, object names, methodology, result variables, and rerun
instructions are in the
[Study 01 README](studies/01_line_energization/README.md).

### Key figures

![Study 01 point-on-wave sweep](docs/assets/01_point_on_wave_sweep.png)

The two repeating voltage/current groups come from balanced three-phase
symmetry. Voltage is governed by 30 + 60*n degree closures, while current is
governed by 0 + 60*n degrees; therefore maximum closing current is not a proxy
for maximum receiving-end voltage.

![Study 01 worst-case waveforms](docs/assets/01_worst_case_waveforms.png)

The 30-degree case shows the initially de-energized open line, the strong
high-frequency wavefronts immediately after closing, and their decay toward the
power-frequency response. The maximum is taken across absolute phase values, so
the large negative phase-C excursion governs the reported 2.257 pu result.

![Study 01 travelling-wave detail](docs/assets/01_travelling_wave_detail.png)

The receiving end first responds near the independently calculated 0.518 ms
one-way travel time. Later steps are repeated open-end/source reflections; their
timing is evidence that the result is produced by a distributed propagation
model rather than by a lumped steady-state approximation.

![Study 01 time-step sensitivity](docs/assets/01_timestep_sensitivity.png)

Peak voltage and current converge upward as the time step decreases. The 2.5 us
case is within 0.1% of the 1.25 us reference, while the 10 us regression baseline
underestimates both peaks by about 1%; a completed run is therefore not, by
itself, evidence of numerical convergence.

## Study 02 — verified 220 kV cable energization

### Question and target model

How do breaker point on wave and metallic-screen bonding affect the transient
core voltage, screen voltage, conductor current, and screen current of a 40 km
220 kV XLPE cable energized with an open receiving end?

The implemented builder creates catalogue-derived geometric `TypCab`/
`TypCabsys` data, separate core and sheath `ElmLne` circuits, their `ElmCabsys`
coupling, and a distributed frequency-dependent phase-domain representation.
PowerFactory 2024 engine construction and API read-back pass; interactive native
diagram export remains a collaborative visual task. The Python API has executed
and processed all 24 bonding-by-point-on-wave cases.

### Engineering basis

| Quantity | First-order value |
|---|---:|
| Total capacitance | **8.00 uF/phase** |
| Steady-state charging current | **0.319 kA/phase** |
| Three-phase stored-energy scale | **387.20 kJ** |
| Surge impedance | **81.55 ohm** |
| One-way travel time | **0.652 ms** |
| Samples per travel time at 2.5 us | **approximately 261** |

These remain analytical scale checks, not EMT results. The assumptions,
object/result contract, bonding scenarios, executed baseline, and completion
gate are documented in the
[Study 02 README](studies/02_hv_cable_energization/README.md).

A read-only PowerFactory 2024 schema preflight now verifies the installed
`TypCab`, `TypCabsys`, and `ElmCabsys` attributes used by the geometric model
builder. The dimensions, capacitance, and inductance are tied to the ABB Table
37 row for a 220 kV, 1,200 mm² copper single-core cable; installation and
unspecified material properties remain explicit teaching assumptions.

### Design-basis figures

![Study 02 cable parameter basis](docs/assets/02_cable_parameter_overview.png)

The sequence bars show that earth-return behavior differs materially from the
positive-sequence path, while the summary box converts the 40 km input data into
charging-current, stored-energy, surge-impedance, and travel-time scale checks.
These are design-basis calculations and are deliberately labelled as non-EMT
results.

![Study 02 bonding matrix](docs/assets/02_cable_bonding_matrix.png)

Each row is a physically different metallic-screen topology. The matrix makes
the grounded ends and cross-bonded sections explicit so that a result can later
be traced to topology instead of being attributed only to a case number.

![Study 02 cable length sensitivity](docs/assets/02_cable_length_sensitivity.png)

Charging current and electric-field energy increase linearly with cable length
because total shunt capacitance is proportional to length in this first-order
check. The highlighted 40 km point identifies the base case; the plot does not
predict switching peaks or screen stress.

![Study 02 scenario coverage](docs/assets/02_cable_scenario_coverage.png)

The left panel assigns all 24 bonding-by-angle cases stable sequence numbers.
The right panel verifies the 50 Hz angle-to-event-time conversion from 20.0 to
28.33 ms. The colors separate bonding topologies only and do not represent EMT
severity.

### Verified PowerFactory EMT results

| KPI | Result |
|---|---:|
| Maximum open-end conductor voltage | **2.195 pu / 394.331 kV peak** |
| Governing case | **ideal cross-bonded, 30 degrees** |
| Maximum metallic-screen voltage | **133.995 kV peak** |
| Governing screen-voltage case | **isolated, 60 degrees** |
| Maximum ground current | **3.186 kA peak** |
| Governing ground-current case | **both ends, 60 degrees** |
| EMT cases | **24** |

![Study 02 bonding and point-on-wave EMT comparison](docs/assets/02_cable_bonding_pow_comparison.png)

Every marker is an executed PowerFactory EMT case. The comparison shows the
central engineering trade-off: isolated screens experience the greatest
terminal screen voltage; grounding suppresses that voltage but transfers the
duty into grounding current. The ideal `TypCabsys` cross-bonded model gives the
largest conductor overvoltage in this benchmark but does not resolve individual
link boxes or minor sections.

![Study 02 governing EMT waveforms](docs/assets/02_cross_bonded_pow_030deg_waveforms.png)

The four panels align the breaker closing instant with receiving-end conductor
voltage, sending-end core current, terminal screen voltage, and screen/ground
current. The 394.331 kV peak occurs 1.638 ms after closing. Both terminal screen
voltages remain clamped in this ideal representation; explicit sectional
cross-bonding is required before evaluating local joint or SVL duty.

## Common engineering workflow

1. Define the decision, KPI, units, bases, and acceptance-source provenance.
2. Version project data and classify every input by maturity.
3. Build or update named PowerFactory objects through an idempotent API builder.
4. Generate the linked native PowerFactory single-line diagram.
5. Configure initial conditions and deterministic events.
6. Run scenario sweeps and preserve a machine-readable manifest.
7. Export instantaneous channels through `ElmRes` and `ComRes`.
8. Normalize CSV data with pandas and calculate KPIs.
9. Compare against analytical checks and compact regression references.
10. Verify time step, model bandwidth, and governing uncertainties.
11. Generate native diagrams and multiple reviewable result figures.
12. Export the complete inactive PowerFactory project to its versioned `.pfd`
    path inside the study folder.
13. State limitations before using an example in an equipment decision.

## Quick start

### Install

```powershell
cd "C:\Users\VM-PF\Documents\06 - EMT DIgSILENT"
py -3.9 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
pfemt doctor
```

Use the Python version matching the installed PowerFactory Python module.

### Reproduce Study 01

```powershell
pfemt validate studies/01_line_energization/configs/base.yaml
pfemt build studies/01_line_energization/configs/base.yaml
pfemt sweep studies/01_line_energization/configs/base.yaml
pfemt sensitivity studies/01_line_energization/configs/base.yaml
pfemt analyse studies/01_line_energization/configs/base.yaml
pfemt archive studies/01_line_energization/configs/base.yaml
```

For the native diagram, run the supplied `*_inside_powerfactory.py` scripts from
interactive `ComPython` objects as explained in the Study 01 README.

### Reproduce Study 02

```powershell
pfemt validate studies/02_hv_cable_energization/configs/base.yaml
pfemt manifest studies/02_hv_cable_energization/configs/base.yaml
pfemt build studies/02_hv_cable_energization/configs/base.yaml
pfemt sweep studies/02_hv_cable_energization/configs/base.yaml
pfemt analyse studies/02_hv_cable_energization/configs/base.yaml
python studies/02_hv_cable_energization/scripts/generate_design_figures.py
python studies/02_hv_cable_energization/scripts/generate_scenario_manifest.py
python studies/02_hv_cable_energization/scripts/inspect_installed_cable_schema.py `
  --output studies/02_hv_cable_energization/outputs/powerfactory_cable_schema.json
pfemt archive studies/02_hv_cable_energization/configs/base.yaml
```

For the native model, select
`studies/02_hv_cable_energization/scripts/build_model_inside_powerfactory.py`
from an interactive `ComPython` object. Run the companion
`export_diagram_inside_powerfactory.py` script after visually reviewing the
linked diagram. The Study 02 README documents the exact steps and the remaining
advanced validation gates.

Run `pfemt archive` from a terminal with the interactive PowerFactory window
closed. The command builds the current model, temporarily deactivates it as
required by `ComPfdexport`, writes the configured `.pfd` atomically, and
reactivates the project before exiting.

## Repository structure

```text
.
|-- docs/                     methodology, architecture, references, figures
|-- src/pfemt/                reusable PowerFactory and analysis modules
|-- studies/
|   |-- 01_line_energization/ complete verified vertical slice
|   |-- 02_hv_cable_energization/ verified EMT baseline
|   `-- 03...12/             study-specific implementation contracts
|-- tests/                    unit, regression, plotting, integration tests
`-- config/                   connection examples without secrets
```

Generated raw/normalized outputs remain outside Git. Compact numerical
references and curated figures are versioned for review.

## Verification

- PowerFactory command return codes are checked.
- Stable names and explicit object classes are used.
- Raw CSV files are preserved before pandas normalization.
- Units and result-variable identifiers are versioned per study.
- Synthetic data are restricted to unit tests and are never presented as study
  results.
- Native network diagrams remain linked to PowerFactory electrical objects.
- Analytical references are labelled separately from EMT baselines.
- Planned cases contain no fabricated KPI values.

Run the complete offline quality suite with:

```powershell
pytest
ruff check .
```

## Documentation

- [Architecture](docs/architecture.md)
- [Standard case methodology](docs/case_methodology.md)
- [Study README template](docs/study_readme_template.md)
- [Technical references](docs/references.md)
- [Implementation roadmap](docs/roadmap.md)
- [Contribution guide](CONTRIBUTING.md)

## Engineering-use boundary

This repository is an educational and automation reference. Project decisions
require validated geometry and equipment data, reviewed model fidelity,
appropriate operating scenarios, numerical convergence, independent checking,
and the applicable utility/manufacturer/standard acceptance criteria.
