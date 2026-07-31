# Industrial EMT Studies with DIgSILENT PowerFactory and Python

[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-3776AB.svg)](https://www.python.org/)
[![PowerFactory 2024](https://img.shields.io/badge/PowerFactory-2024-004B87.svg)](https://www.digsilent.de/)
[![Tests](https://img.shields.io/badge/tests-passing-2E8B57.svg)](#verification-and-quality-controls)

This repository is an educational, reproducible framework for electromagnetic
transient (EMT) studies in DIgSILENT PowerFactory. Each study is treated as an
engineering case: the question, assumptions, model, events, monitored signals,
acceptance checks, figures, and regression reference are versioned together.

> **Current scope:** Study 01, 230 kV overhead-line energization, is fully
> implemented and verified. The remaining industry cases are explicitly marked
> as planned in the [roadmap](docs/roadmap.md); this repository does not present
> unimplemented studies as completed work.

All future cases follow the same
[15-step engineering methodology](docs/case_methodology.md).

## Study 01 — 230 kV line energization

### Engineering question

What is the maximum open-end phase-ground voltage when a 150 km, 230 kV line is
energized at different points on the voltage wave, and which breaker-closing
angle produces the most severe duty?

This question appears in insulation-coordination screening, controlled-switching
specification, reactor and surge-arrester assessment, and commissioning studies.

### PowerFactory model

The Python builder creates the electrical objects and their linked PowerFactory
`IntGrfnet` representation; it does not redraw the one-line with Matplotlib.
Run
[`export_diagram_inside_powerfactory.py`](studies/01_line_energization/scripts/export_diagram_inside_powerfactory.py)
from an interactive PowerFactory `ComPython` object to export the active
`SetDeskpage` through `ComWr`. The native PNG is written to
`studies/01_line_energization/outputs/figures/powerfactory_single_line.png`.

```text
Thevenin grid -- sending bus -- three-pole breaker -- distributed EMT line -- open end
```

| Item | Base-case value | PowerFactory object/model |
|---|---:|---|
| System voltage | 230 kV line-line RMS | `ElmTerm` |
| Frequency | 50 Hz | network nominal frequency |
| Source strength | 10,000 MVA, R/X = 0.10 | `ElmXnet` |
| Line length | 150 km | `ElmLne` |
| Line representation | distributed, frequency-dependent | `i_dist=1`, `i_model=1` |
| EMT time step | 10 us | `ComSim` |
| Simulation window | -20 ms to 120 ms | `ComInc`/`ComSim` |
| Point-on-wave cases | 0 to 330 degrees in 30-degree steps | `EvtSwitch` |

![Input parameters and analytical checks](docs/assets/01_parameter_overview.png)

### Methodology

1. **Define the decision and KPI.** The KPI is the largest absolute
   receiving-end phase-ground voltage after breaker closing, expressed on the
   nominal phase-ground peak base.
2. **Version the input basis.** Source, line, simulation, event, and result
   settings are stored in
   [`base.yaml`](studies/01_line_energization/configs/base.yaml), while every
   engineering assumption is classified in the parameter register.
3. **Build the PowerFactory model through the API.** The builder creates the
   project, grid, terminals, cubicles, source, breaker, line type, line, Study
   Case, commands, events folder, result file, and native single-line diagram.
4. **Configure the EMT line.** The example calls
   `AreDistParamsPossible()` and `FitParams(0, 1)` and stops on a non-zero return
   code. Project work should replace sequence inputs with validated geometry.
5. **Initialize the network.** `ComInc` uses instantaneous EMT mode and the
   versioned initial-condition settings.
6. **Apply the event.** One three-pole close event is placed at the absolute
   time corresponding to each requested phase-A electrical angle.
7. **Run the sweep.** `ComSim` executes 12 deterministic scenarios. Each event
   time and parameter set is written to the scenario manifest.
8. **Record instantaneous quantities.** Receiving-end `Vabc` and sending-end
   `Iabc` are registered in `ElmRes` using unit-specific variable identifiers.
9. **Export and normalize.** `ComRes` writes the raw CSV. pandas maps the
   PowerFactory headers to a stable, unit-explicit schema.
10. **Calculate and rank KPIs.** Python calculates voltage/current peaks,
    phase, time, angle ranking, and first-order travelling-wave checks.
11. **Verify numerical repeatability.** The sweep is compared automatically
    with the versioned PowerFactory 2024 SP2 baseline and the worst angle is run
    at 20, 10, 5, 2.5, and 1.25 us.
12. **Interpret the result.** The example result is a workflow benchmark, not a
    project insulation withstand criterion.

The voltage base is:

```text
Vbase,phase-ground,peak = Vnominal,line-line,RMS * sqrt(2/3)
                       = 187.79 kV
```

### Verified results

The 12-case PowerFactory run produced:

- maximum voltage: **2.2570 pu / 423.85 kV phase-ground peak**;
- maximum-voltage angles: **30, 90, 150, 210, 270, and 330 degrees**;
- maximum closing current: **0.8656 kA peak**;
- maximum-current angles: **0, 60, 120, 180, 240, and 300 degrees**.

The alternating 60-degree groups are consistent with a balanced three-phase
system: shifting the phase-A closing reference by 60 degrees exchanges the
phase that experiences the largest instantaneous voltage or current.

![Point-on-wave voltage and current sweep](docs/assets/01_point_on_wave_sweep.png)

### Waveform interpretation

The worst scenario is examined at three levels. The complete waveform shows the
pre-event steady state, closing instant, initial travelling-wave response, and
later reflections.

![Worst-case instantaneous waveforms](docs/assets/01_worst_case_waveforms.png)

Aligning all scenarios to their own closing instant makes the point-on-wave
dependence visible without confusing it with the absolute event-time offset.

![All-scenario overvoltage envelope](docs/assets/01_overvoltage_envelope.png)

From the positive-sequence X and B inputs, the first-order analytical check gives
approximately 286 ohm surge impedance and 0.519 ms one-way travel time. The
simulation is not expected to equal the ideal lossless 2 pu open-end step because
it includes phase coupling, losses, source impedance, frequency dependence, and
successive reflections.

![Travelling-wave detail](docs/assets/01_travelling_wave_detail.png)

### Numerical verification

The post-processor compares the calculated extrema against the versioned
reference in
[`powerfactory_2024_sp2.yaml`](studies/01_line_energization/expected/powerfactory_2024_sp2.yaml).
The default relative tolerances are 0.5% for voltage and 1.0% for current.

The time-step study uses the worst switching angle. Its purpose is to quantify
peak-value sensitivity, not merely to show that all simulations complete. The
10 us baseline is retained for regression continuity; acceptance of a formal
design peak must be based on the finer-step convergence trend.

At 30 degrees, the 1.25 us run produced **2.2783 pu** and **0.7786 kA**. The
2.5 us result differs by only **0.036% in voltage** and **0.056% in current**,
whereas the 10 us baseline is approximately **0.935% lower in voltage** and
**0.984% lower in current**. This example therefore demonstrates why a
successful run is not the same as a converged engineering result.

![EMT time-step sensitivity](docs/assets/01_timestep_sensitivity.png)

## Reproduce the study

### Install the Python package

```powershell
cd powerfactory-emt-industrial-studies
py -3.9 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
pfemt doctor
pfemt validate studies/01_line_energization/configs/base.yaml
```

Use the Python version shipped in the matching
`PowerFactory <version>/Python/<version>` directory.

### Recommended first run: PowerFactory ComPython

1. Open PowerFactory.
2. Create a **Python Script (`ComPython`)** object.
3. Select
   `studies/01_line_energization/scripts/build_model_inside_powerfactory.py`
   as the external script and run it once.
4. Run `export_diagram_inside_powerfactory.py` while the generated diagram is
   available on the Graphics Board.
5. Run `run_sweep_inside_powerfactory.py`.
6. Run `run_timestep_sensitivity_inside_powerfactory.py`.
7. From a terminal, run `python scripts/analyse_results.py` in the study folder.

### Terminal workflow

The same model and sweep can be executed in external mode:

```powershell
pfemt build studies/01_line_energization/configs/base.yaml
pfemt sweep studies/01_line_energization/configs/base.yaml
pfemt sensitivity studies/01_line_energization/configs/base.yaml
pfemt analyse studies/01_line_energization/configs/base.yaml
```

If a specific PowerFactory user is required, provide it through environment
variables rather than a committed YAML file:

```powershell
$env:PFEMT_USERNAME = "powerfactory_user"
$env:PFEMT_PASSWORD = "temporary_secret"
```

### Generated output contract

`studies/01_line_energization/outputs/` contains:

- raw PowerFactory CSV files;
- normalized unit-explicit CSV files;
- scenario manifest and run metadata;
- per-scenario JSON metrics and Markdown reports;
- ranked sweep summary;
- analytical and baseline-comparison JSON files;
- time-step sensitivity CSV;
- native PowerFactory diagram and analysis figures.

Generated outputs are ignored by Git. Curated figures and compact numerical
references are copied to `docs/assets/` and `expected/` for review.

## Repository structure

```text
.
|-- config/                         connection profiles without secrets
|-- docs/                           architecture, references, roadmap, figures
|-- src/pfemt/                      reusable automation package
|   |-- builders/                   PowerFactory API model builders
|   |-- diagram.py                  native IntGrfnet generation/export
|   |-- events.py                   switching-event configuration
|   |-- results.py                  ElmRes registration and ComRes export
|   |-- metrics.py                  EMT KPIs and analytical checks
|   |-- plotting.py                 reproducible educational figures
|   `-- workflows.py                end-to-end orchestration
|-- studies/
|   `-- 01_line_energization/
|       |-- configs/                executable study definition
|       |-- parameters/             assumptions and parameter basis
|       |-- expected/               regression references
|       |-- scripts/                ComPython entry points
|       `-- outputs/                generated and ignored by Git
`-- tests/                          unit, regression, and integration checks
```

## Verification and quality controls

- Every PowerFactory command return code is checked.
- Object lookup uses stable names and explicit class suffixes.
- Raw exports are preserved; normalized files are derived artifacts.
- Result variables and physical units are versioned as a schema.
- Synthetic data appear only in unit tests and are never presented as study results.
- The native diagram is built from linked `IntGrf` objects in PowerFactory.
- The regression comparison fails when voltage or current leaves its tolerance.
- The time-step study quantifies the numerical sensitivity of the reported peak.
- `pytest` and `ruff check .` are required before publication.

## Engineering boundary

This is an industrial-style educational example, not a design certificate. A
project deliverable must use validated tower/conductor/earth-wire geometry, soil
resistivity, line transposition, breaker pole scatter, trapped charge, source
uncertainty, arrester data, equipment withstand curves, and the applicable
insulation-coordination standard.

The source code is released under the [MIT terms](LICENSE). Citation metadata
are provided in [CITATION.cff](CITATION.cff).
