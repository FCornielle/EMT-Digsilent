# Study 02 — 220 kV XLPE Cable Energization and Sheath Bonding

> **Status: engineering basis started.** Configuration, parameter traceability,
> analytical checks, a 24-case bonding-by-angle manifest, plotting, and tests
> are implemented.
> The detailed `TypCab`/`TypCabsys` EMT model and its waveform baseline are the
> next delivery. No figure in this README is presented as an EMT result.

## 1. Industrial question

How do breaker point on wave and metallic-screen bonding affect the transient
core voltage, screen voltage, conductor current, screen current, and energy
duty when a long 220 kV XLPE cable is energized with its receiving end open?

This question is relevant to cable sealing ends, link boxes, sheath-voltage
limiters, grounding conductors, arresters, shunt reactors, controlled switching,
and commissioning procedures.

## 2. Decisions and acceptance metrics

The completed EMT study will rank each switching/bonding scenario using:

1. maximum core-to-screen and core-to-ground voltage at both cable ends;
2. maximum metallic-screen voltage to ground at joints and terminations;
3. peak and RMS conductor current;
4. peak and RMS screen/earth-continuity-conductor current;
5. dominant transient frequency and damping;
6. one-way wave-arrival time and reflection sequence;
7. arrester or sheath-voltage-limiter energy, when those devices are added;
8. time-step and model-bandwidth sensitivity.

Equipment limits are intentionally absent from this example. They must come
from project specifications and manufacturer data.

## 3. Target PowerFactory model

```text
Thevenin source -> sending bus -> three-pole breaker -> core ElmLne circuit
                -> open receiving bus

screen terminals -> screen ElmLne circuit -> screen terminals
                    ^ both ElmLne circuits coupled by ElmCabsys
```

PowerFactory represents the explicit-sheath example as core and screen line
circuits coupled by `ElmCabsys`; the coupling receives the geometric
`TypCabsys`, which in turn references the single-core `TypCab` definition.

The final API builder will use geometric cable objects rather than treating the
cable as an overhead line:

| Function | Target PowerFactory object | Stable name |
|---|---|---|
| Source equivalent | `ElmXnet` | `GRID_EQUIVALENT` |
| Sending bus | `ElmTerm` | `BUS_CABLE_SENDING_220` |
| Breaker | `ElmCoup` | `CB_CABLE_220` |
| Core circuit | `ElmLne` | `CABLE_CORE_220KV_40KM` |
| Screen circuit | `ElmLne` | `CABLE_SCREEN_220KV_40KM` |
| Cable coupling | `ElmCabsys` | `CABLE_SYSTEM_220KV_40KM` |
| Cable geometry/type | `TypCab` / `TypCabsys` | versioned in YAML |
| Receiving bus | `ElmTerm` | `BUS_CABLE_RECEIVING_220` |
| Screen grounding | grounding branches/nodes | one set per bonding case |
| Native diagram | `IntGrfnet` | `EMT Cable Energization 220 kV` |

DIgSILENT documents `ElmCabsys` for circuits with an explicit sheath and
recommends geometric distributed models for detailed EMT work. Therefore a
simple sequence-only `TypLne` will not be used as the final bonding model.

### Installed API schema preflight

The next implementation step now includes a read-only schema inspector:
[`scripts/inspect_installed_cable_schema.py`](scripts/inspect_installed_cable_schema.py).
Against the installed PowerFactory 2024 data schema it confirms the cable
classes and their real attribute names before any object is created. The latest
installed schema build exposes 60 `TypCab`, 47 `TypCabsys`, and 81 `ElmCabsys`
attributes. The preflight specifically verifies the attributes needed for:

- conductor, insulation, and metallic-screen geometry in `TypCab`;
- cable references, phase positions, bonding, burial, and earth data in
  `TypCabsys`;
- linked line circuits and distributed frequency-dependent EMT settings in
  `ElmCabsys`.

Run the inspection with:

```powershell
python studies/02_hv_cable_energization/scripts/inspect_installed_cable_schema.py `
  --output studies/02_hv_cable_energization/outputs/powerfactory_cable_schema.json
```

The generated JSON remains an environment report. Attribute presence alone is
not permission to guess geometry, units, or enumeration values; those inputs
must be taken from a reviewed cable datasheet or an approved PowerFactory cable
template before the idempotent builder is enabled.

## 4. Input basis

The executable source of truth is [`configs/base.yaml`](configs/base.yaml). Each
value and its maturity are listed in
[`parameters/parameter_basis.csv`](parameters/parameter_basis.csv).

| Parameter | Base value | Current classification |
|---|---:|---|
| Nominal voltage | 220 kV line-line RMS | example |
| Frequency | 50 Hz | example |
| Source strength | 8,000 MVA | example |
| Cable length | 40 km | example |
| Core area | 1,200 mm² Cu | example |
| Screen area | 185 mm² | example |
| Burial depth | 1.5 m | assumed |
| Phase spacing | 0.35 m | assumed |
| Soil resistivity | 100 ohm m | assumed |
| Core-screen capacitance | 0.230 uF/km | example |
| Initial EMT step | 2.5 us | requires convergence |

![Cable parameter overview](../../docs/assets/02_cable_parameter_overview.png)

**How to read this figure.** The zero-sequence resistance and inductance exceed
the positive-sequence values because the return path includes screens, grounding
connections, and earth. The core-screen capacitance dominates the charging
current and stored-energy scale shown in the summary box. The calculated 0.359
ms travel time and roughly 144 samples per travel time indicate that the initial
2.5 us step can resolve the first wavefront, but they do not replace a formal
time-step and fitting-band convergence study.

## 5. Bonding scenario matrix

The first campaign separates screen topology from breaker point on wave:

| Case | Sending end | Receiving end | Cross-bonded sections | Primary concern |
|---|---|---|---|---|
| Isolated | open | open | no | screen voltage stress |
| Single-point | grounded | open | no | remote-end screen voltage |
| Both ends | grounded | grounded | no | circulating/transient screen current |
| Cross-bonded | grounded | grounded | yes | section imbalance and link-box duty |

![Metallic-screen bonding matrix](../../docs/assets/02_cable_bonding_matrix.png)

The matrix describes topology only. It does not assign a fabricated severity
ranking; that ranking must come from the EMT simulations.

**How to read this figure.** Moving from the isolated row to single-point and
both-end bonding changes the available screen-current return path; the
cross-bonded row additionally introduces sectional screen transposition. Those
topological changes are expected to redistribute screen voltage and current,
which is why they must be represented by explicit PowerFactory nodes and
connections rather than by a result label applied after simulation.

The initial screening campaign combines the four topologies with six phase-A
closing angles. This produces the versioned
[`parameters/scenario_manifest.csv`](parameters/scenario_manifest.csv).

![Bonding-by-angle scenario coverage](../../docs/assets/02_cable_scenario_coverage.png)

**How to read this figure.** The left panel proves that every bonding row is
paired with every requested angle and assigns stable case numbers #01 through
#24. The right panel independently checks the event conversion at 50 Hz: 0
degrees closes at 20.0 ms and 150 degrees at 28.33 ms. Cell color is only a
visual topology grouping, not a prediction of overvoltage or screen-current
severity.
The 0-to-150-degree set is a balanced-system screening set; it must be expanded
when pole scatter, trapped charge, or project asymmetry breaks the assumed
half-cycle equivalence.

## 6. Analytical design checks

Before building the EMT model, the repository calculates transparent scale
checks from the declared positive-sequence capacitance and inductance:

```text
Vphase,rms = VLL,rms / sqrt(3)
Icharge    = 2*pi*f*Ctotal*Vphase,rms
W3-phase   = 3*Ctotal*Vphase,rms^2
Zc         = sqrt(L/C)
travel     = length / [1/sqrt(L*C)]
```

For the 40 km example:

- phase voltage: **127.02 kV RMS**;
- total capacitance: **9.20 uF per phase**;
- first-order steady-state charging current: **0.367 kA per phase**;
- three-phase stored-energy scale: **445.28 kJ**;
- surge impedance: **39.01 ohm**;
- one-way travel time: **0.359 ms**;
- approximately **144 time steps per one-way travel time** at 2.5 us.

![Cable length sensitivity](../../docs/assets/02_cable_length_sensitivity.png)

**How to read this figure.** Both curves are linear because total capacitance is
proportional to cable length in this analytical model. The orange marker is the
40 km base case, corresponding to 0.367 kA charging current and 445.28 kJ stored
energy. The plot is useful for checking input scale and recognizing how quickly
reactive demand grows with length, but it cannot reproduce sheath coupling,
frequency-dependent attenuation, or switching-wave reflections.

These calculations verify scale and sampling. They cannot predict the final
screen voltage, switching overvoltage, high-frequency loss, or reflection
pattern of the explicit cable system.

## 7. Detailed EMT methodology

1. **Define the decision.** Identify insulation, screen, link-box, grounding,
   reactor, arrester, or switching duty to be assessed.
2. **Collect project data.** Obtain cable layers, conductor/screen materials,
   geometry, bonding-section lengths, joints, grounding impedances, earth
   continuity conductor, soil properties, and terminal equipment.
3. **Build geometric cable types.** Create `TypCab` and `TypCabsys` objects with
   explicit cores and metallic screens.
4. **Create the cable system.** Connect the cable system between sending and
   receiving terminals with stable API names.
5. **Configure bonding.** Implement isolated, single-point, both-end, and
   cross-bonded alternatives as explicit topology states.
6. **Select the EMT line representation.** Use a distributed,
   frequency-dependent phase-domain model with a declared fitting band.
7. **Calculate cable parameters.** Stop if PowerFactory cannot calculate the
   requested distributed model.
8. **Initialize the open-end case.** Define pre-switch voltage, breaker state,
   initial screen conditions, shunt reactors, and trapped charge.
9. **Sweep breaker point on wave.** Generate the deterministic 24-row manifest,
   then run each requested closing angle for every bonding topology; add pole
   scatter in a later sensitivity stage.
10. **Record instantaneous channels.** Export core and screen voltages/currents
    at terminations and section joints through `ElmRes`/`ComRes`.
11. **Calculate KPIs.** Rank core voltage, screen voltage, conductor/screen
    current, oscillation frequency, damping, and device energy.
12. **Verify numerical convergence.** Repeat the governing cases with smaller
    time steps and wider frequency-fitting ranges.
13. **Validate the cable model.** Compare frequency-sweep impedance with the
    EMT voltage/current FFT response.
14. **Visualize results.** Include the native PowerFactory one-line, parameter
    basis, waveform panels, bonding comparison, distance profile, spectrum,
    and numerical-sensitivity figures.
15. **State the engineering boundary.** Separate example conclusions from
    project equipment acceptance.

## 8. Planned result contract

| Location | Quantity | Unit |
|---|---|---|
| Sending core | instantaneous phase voltage/current | kV, kA |
| Receiving core | instantaneous phase voltage/current | kV, kA |
| Sending screen | screen-to-ground voltage/current | kV, kA |
| Receiving screen | screen-to-ground voltage/current | kV, kA |
| Cross-bonding joints | screen voltage/current | kV, kA |
| Grounding branches | current and dissipated energy | kA, kJ |
| Limiting devices | voltage, current, energy | kV, kA, kJ |

The exact PowerFactory result-variable identifiers will be versioned only after
they are verified against the installed cable-system model.

## 9. Current reproducible deliverables

- configuration schema and study boundary;
- parameter/assumption register;
- four explicit bonding scenarios and 24 deterministic bonding-by-angle cases;
- analytical KPI calculations and versioned reference;
- a versioned scenario manifest and four educational design-basis figures;
- an installed PowerFactory cable-class schema preflight;
- unit and regression tests;
- target PowerFactory object and result contracts.

Generate the current figures with:

```powershell
python studies/02_hv_cable_energization/scripts/generate_design_figures.py
python studies/02_hv_cable_energization/scripts/generate_scenario_manifest.py
```

The CLI also writes the same campaign to the configured output directory:

```powershell
pfemt manifest studies/02_hv_cable_energization/configs/base.yaml
```

## 10. Completion gate

Study 02 remains **Started**, not **Implemented**, until all of the following are
available:

1. idempotent `TypCab`/`TypCabsys` PowerFactory API builder;
2. native linked single-line diagram and exported image;
3. verified core and screen result-variable identifiers;
4. complete bonding × point-on-wave EMT campaign;
5. time-step and frequency-band sensitivity;
6. frequency-sweep versus EMT/FFT comparison;
7. compact PowerFactory baseline and curated result figures.

## 11. Technical references

- [DIgSILENT: configure overhead-line and cable models for EMT](https://www.digsilent.de/index.php/en/faq-reader-powerfactory/how-to-configure-overhead-line-and-cable-models-for-emt-simulations.html)
- [DIgSILENT: overhead-line and cable modelling objects](https://www.digsilent.de/en/faq-reader-powerfactory/how-do-you-model-overhead-lines-and-cables-in-powerfactory.html)
- [DIgSILENT: `ElmCabsys` with `TypCabsys` and single-core `TypCab`](https://www.digsilent.de/en/faq-reader-powerfactory/how-do-you-model-cables-in-a-pipe.html)
- [DIgSILENT: isolated, single-point, both-end, and cross-bonded screens](https://www.digsilent.de/en/faq-reader-powerfactory/how-do-you-model-the-bonding-of-cables-isolated-single-and-double-bonded.html)
- [DIgSILENT: detailed cable/sheath voltage and current profiles with Python](https://www.digsilent.de/en/faq-reader-powerfactory/do-you-have-a-python-script-to-calculate-the-voltage-and-current-in-a-line-as-function-of-distance.html)
- [DIgSILENT: validate cable EMT models with frequency sweep and EMT/FFT](https://www.digsilent.de/en/faq-reader-powerfactory/how-can-you-validate-cable-and-overhead-line-models-for-emt-simulations/category/dynamic-simulation.html)
