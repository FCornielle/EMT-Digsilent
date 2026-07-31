# Study 02 — 220 kV XLPE Cable Energization and Sheath Bonding

> **Status: PowerFactory model built and API-verified; EMT baseline pending.** The
> catalogue-derived `TypCab`, geometric `TypCabsys`, explicit core/sheath
> `ElmLne` pair, `ElmCabsys` coupling, native-diagram layout, 24-case manifest,
> analytical checks, and tests are implemented. PowerFactory 2024 engine
> integration and API read-back pass. The interactive PNG export and waveform
> baseline remain to be completed. No figure below is presented as an EMT result.

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

The idempotent API builder uses geometric cable objects rather than treating the
cable as an overhead line:

| Function | Target PowerFactory object | Stable name |
|---|---|---|
| Source equivalent | `ElmXnet` | `GRID_EQUIVALENT` |
| Sending bus | `ElmTerm` | `BUS_CABLE_SENDING_220` |
| Breaker | `ElmCoup` | `CB_CABLE_220` |
| Core circuit | `ElmLne` | `CABLE_CORE_220KV_40KM` |
| Screen circuit | `ElmLne` | `CABLE_SHEATH_220KV_40KM` |
| Cable coupling | `ElmCabsys` | `CABLE_COUPLING_220KV_40KM` |
| Cable geometry/type | `TypCab` / `TypCabsys` | versioned in YAML |
| Receiving bus | `ElmTerm` | `BUS_CABLE_RECEIVING_220` |
| Screen grounding | grounding branches/nodes | one set per bonding case |
| Native diagram | `IntGrfnet` | `EMT Cable Energization 220 kV` |

DIgSILENT documents `ElmCabsys` for circuits with an explicit sheath and
recommends geometric distributed models for detailed EMT work. Therefore a
simple sequence-only `TypLne` will not be used as the final bonding model.

### Installed API schema preflight

The implementation includes a read-only schema inspector:
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
not evidence that a model is physically valid; geometry, material data, units,
and calculated matrices still require engineering review.

### Run the API builder inside PowerFactory

The stable execution path is an external script selected from a PowerFactory
`ComPython` object. Use
[`scripts/build_model_inside_powerfactory.py`](scripts/build_model_inside_powerfactory.py)
as that external script and execute it from the interactive application.

The builder then performs these steps:

1. creates or activates project `PFEMT_02_HV_Cable_Energization_220kV`;
2. creates the `TypCab` radial layer definition from the reviewed YAML fields;
3. creates one buried, flat-formation `TypCabsys` with phase coordinates
   `[-0.35, 0.00, +0.35] m` at 1.5 m depth;
4. creates separate core and metallic-sheath `ElmLne` circuits with equal
   40 km lengths;
5. couples those circuits through `ElmCabsys.plines`, with the core listed first
   as prescribed by the DIgSILENT bonding tutorial;
6. requests the distributed frequency-dependent phase-domain representation,
   updates the coupling, and calls `ElmCabsys.FitParams()`;
7. creates and activates the EMT Study Case and its result/event commands;
8. creates or reuses the linked native PowerFactory diagram and applies the
   deterministic two-row core/sheath layout; and
9. writes changes to the PowerFactory database when that method is available.

Every named object is created with `create_or_get`, so rerunning the script
updates the study instead of duplicating the network. The successful fit writes
a SHA-256 input signature to `ElmCabsys.desc`; unchanged reruns reuse those
parameters, while a changed cable input forces a new fit. After the build, select
[`scripts/export_diagram_inside_powerfactory.py`](scripts/export_diagram_inside_powerfactory.py)
from a second `ComPython` object to export the visible native diagram to
`outputs/figures/powerfactory_single_line.png`. The exporter opens the linked
`IntGrfnet`, resolves its live `SetDeskpage`, and passes that tab explicitly to
PowerFactory 2024's `ComWr.ExportGraphicTab()` method. This avoids exporting an
unrelated plot or diagram that happened to be active previously.

### PowerFactory 2024 integration evidence

The opt-in integration test has built and read back the actual project
`PFEMT_02_HV_Cable_Energization_220kV`. The verified database state is:

- one `TypCab` with 41.2 mm conductor diameter, 3.1 mm lead sheath, main/
  outer insulation vector `[24.7, 14.2, 1.0] mm`, calibrated main-insulation
  relative permittivity 2.832934, and 90.011% conductor fill factor;
- one buried `TypCabsys` with three phases, explicit sheath (`red=[0]`), no
  cross-bonding in the base state, and coordinates
  `[[-0.35, 0.00, +0.35, 1.5, 1.5, 1.5]] m`;
- one `ElmCabsys` linking the core line first and sheath line second, with
  `i_dist=1`, `i_model=1`, `fd_model=1`, 10 Hz to 20 kHz fitting band, and
  2 kHz main transient frequency; and
- one linked `IntGrfnet` containing exactly nine expected graphics, with the
  core circuit at y=55 and the sheath circuit at y=90.

The native diagram is stored in PowerFactory as `EMT Cable Energization 220 kV`.
PNG export cannot be completed from the headless engine because its Graphics
Board is unavailable; it must be run with the supplied interactive `ComPython`
export script.

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
| Conductor area / diameter | 1,200 mm² Cu / 41.2 mm | ABB Table 37 |
| Nominal XLPE thickness | 23.0 mm | ABB Table 37 |
| Diameter over insulation | 90.6 mm | ABB Table 37 |
| Lead-sheath thickness | 3.1 mm | ABB Table 37 |
| Overall cable diameter | 125.2 mm | ABB Table 37 |
| Burial depth | 1.5 m | assumed |
| Phase spacing | 0.35 m | assumed |
| Soil resistivity | 100 ohm m | assumed |
| Core-screen capacitance | 0.200 uF/km | ABB Table 37 |
| Inductance | 1.330 mH/km | ABB Table 37 |
| Initial EMT step | 2.5 us | requires convergence |

The physical row is the ABB 220 kV single-core, 1,200 mm² copper-conductor
example in Table 37. It is used as an industrially recognizable teaching basis,
not as a complete product reproduction. Following DIgSILENT's cable-parameter
tutorial, the API preserves the catalogue diameter over insulation: the
effective main-insulation thickness is `(90.6 - 41.2)/2 = 24.7 mm`. Because
semiconducting-layer dimensions are not given, the equivalent relative
permittivity is calibrated to the 0.20 uF/km catalogue capacitance, giving
approximately 2.833. The 3.1 mm lead sheath corresponds to an annular area of
approximately 912.5 mm².

The 14.2 mm radial region outside the lead sheath is represented as an
equivalent oversheath so the overall diameter remains 125.2 mm. Armour and
serving are not explicitly represented; burial, spacing, soil, resistivity, and
loss-tangent values remain declared study assumptions. These boundaries must be
replaced for an actual installation.

![Catalogue-to-TypCab radial mapping](../../docs/assets/02_cable_geometry.png)

**How to read this figure.** The circles are drawn at their declared radial
dimensions, so the narrow grey ring makes the 3.1 mm lead sheath visible between
the XLPE equivalent and the outer construction. The figure also exposes the
model reduction: the large black region is one homogenized outer-insulation
layer, not an assertion that the catalogue cable has no separate bedding,
armour, or serving. This is why the final frequency-domain matrices must be
reviewed against project data before the EMT sweep is accepted.

![Cable parameter overview](../../docs/assets/02_cable_parameter_overview.png)

**How to read this figure.** The zero-sequence resistance and inductance exceed
the positive-sequence values because the return path includes screens, grounding
connections, and earth. The core-screen capacitance dominates the charging
current and stored-energy scale shown in the summary box. The calculated 0.652
ms travel time and roughly 261 samples per travel time indicate that the initial
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
- total capacitance: **8.00 uF per phase**;
- first-order steady-state charging current: **0.319 kA per phase**;
- three-phase stored-energy scale: **387.20 kJ**;
- surge impedance: **81.55 ohm**;
- one-way travel time: **0.652 ms**;
- approximately **261 time steps per one-way travel time** at 2.5 us.

![Cable length sensitivity](../../docs/assets/02_cable_length_sensitivity.png)

**How to read this figure.** Both curves are linear because total capacitance is
proportional to cable length in this analytical model. The orange marker is the
40 km base case, corresponding to 0.319 kA charging current and 387.20 kJ stored
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
- a versioned scenario manifest and five educational design-basis figures;
- an installed PowerFactory cable-class schema preflight;
- an idempotent `TypCab`/`TypCabsys`/`ElmCabsys` API builder;
- an internal `ComPython` build script and native-diagram export script;
- unit, regression, builder-contract, and opt-in integration tests;
- target PowerFactory result contracts.

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

Study 02 remains **Started**, not **Complete**, until all of the following are
available. A checked item means the repository implementation exists; it does
not substitute for reviewing the executed PowerFactory model.

- [x] idempotent `TypCab`/`TypCabsys`/`ElmCabsys` PowerFactory API builder;
- [x] deterministic native linked-diagram generator;
- [x] successful PowerFactory 2024 engine build and object/diagram read-back;
- [ ] exported native diagram image from the interactive Graphics Board;
- [ ] verified core and screen result-variable identifiers;
- [ ] complete bonding x point-on-wave EMT campaign;
- [ ] time-step and frequency-band sensitivity;
- [ ] frequency-sweep versus EMT/FFT comparison;
- [ ] compact PowerFactory baseline and curated result figures.

## 11. Technical references

- [DIgSILENT: configure overhead-line and cable models for EMT](https://www.digsilent.de/index.php/en/faq-reader-powerfactory/how-to-configure-overhead-line-and-cable-models-for-emt-simulations.html)
- [DIgSILENT: overhead-line and cable modelling objects](https://www.digsilent.de/en/faq-reader-powerfactory/how-do-you-model-overhead-lines-and-cables-in-powerfactory.html)
- [DIgSILENT: `ElmCabsys` with `TypCabsys` and single-core `TypCab`](https://www.digsilent.de/en/faq-reader-powerfactory/how-do-you-model-cables-in-a-pipe.html)
- [DIgSILENT: isolated, single-point, both-end, and cross-bonded screens](https://www.digsilent.de/en/faq-reader-powerfactory/how-do-you-model-the-bonding-of-cables-isolated-single-and-double-bonded.html)
- [DIgSILENT: detailed cable/sheath voltage and current profiles with Python](https://www.digsilent.de/en/faq-reader-powerfactory/do-you-have-a-python-script-to-calculate-the-voltage-and-current-in-a-line-as-function-of-distance.html)
- [DIgSILENT: validate cable EMT models with frequency sweep and EMT/FFT](https://www.digsilent.de/en/faq-reader-powerfactory/how-can-you-validate-cable-and-overhead-line-models-for-emt-simulations/category/dynamic-simulation.html)
- [DIgSILENT: export plots and network diagrams with Python](https://www.digsilent.de/index.php/en/faq-reader-powerfactory/how-can-i-automatically-export-all-plots-available-in-a-project.html)
- [ABB: XLPE Submarine Cable Systems, Table 37](https://resources.news.e.abb.com/attachments/published/13326/en-US/55ED60680654/XLPE-Submarine-Cable-Systems-2GM5007-.pdf)
