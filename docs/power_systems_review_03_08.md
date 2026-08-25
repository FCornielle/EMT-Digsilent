# Power-Systems Technical Review: EMT Studies 03-08

**Status:** implementation design gate. Nothing in this document is a
PowerFactory result. These are educational industrial benchmarks, not
equipment-specific compliance studies.

## Common automation and acceptance boundary

PowerFactory's Python interface can create/configure network objects and events,
execute `ComInc`/`ComSim`, register `ElmRes` channels, export with `ComRes`, run
parameter campaigns, calculate KPIs, export native graphics and archive PFDs.
Before each model is frozen, however, a reviewer must inspect the native data
model and diagram for phase connectivity, grounding, vector group, breaker-pole
mapping, conductor order, measurement polarity and equipment curves. Final
diagram routing, legends and result-box readability remain an interactive task.
Version-specific object attributes and result identifiers require an
engine-backed integration test; offline mocks are not evidence that an EMT
channel exists.

Every case shall establish the transient frequency range, validate relevant
line models by frequency sweep, and compare the baseline with at least two
successively smaller integration steps. Governing KPIs, event times and waveform
shape must converge to a declared tolerance. Raw adaptive-step time stamps are
preserved; resampling is explicitly labelled. A failed or ambiguous event is a
failed scenario, not a missing row.

Official basis: [PowerFactory EMT capabilities](https://www.digsilent.de/index.php/en/electromagnetic-transients-emt.html),
[general EMT guidance](https://www.digsilent.de/en/faq-reader-powerfactory/can-you-provide-any-general-guidance-on-how-to-perform-an-emt-simulation.html),
[step-size guidance](https://faq.digsilent.de/en/faq-reader-powerfactory/how-can-you-speed-up-improve-the-performance-of-emt-simulations.html),
[line-model validation](https://www.digsilent.de/en/faq-reader-powerfactory/how-can-you-validate-cable-and-overhead-line-models-for-emt-simulations/category/dynamic-simulation.html),
[Python result export](https://www.digsilent.de/en/faq-reader-powerfactory/how-can-i-export-results-via-python.html), and
[Python graphic export](https://www.digsilent.de/index.php/en/faq-reader-powerfactory/how-can-i-automatically-export-all-plots-available-in-a-project.html).

## Study 03 - Power-transformer energization and inrush

- **Industrial question:** Which closing sequence and physically possible
  residual-flux state govern inrush, bus depression, harmonic-restraint
  security and current duty for the selected transformer and system?
- **Minimum physical model:** Three-sequence Thevenin source; independent
  breaker poles; winding resistance/leakage, vector group and neutral path;
  core-construction-appropriate nonlinear transformer with EMT peak-domain
  excitation curve, air-core slope and reviewed loss/hysteresis treatment; and
  residual flux per limb. A three-limb core must not receive three arbitrary
  residual values that violate its magnetic constraint.
- **Scenario matrix:** Coarse phase-A point-on-wave scan over one cycle followed
  by local refinement; simultaneous and credible pole-scatter orders;
  demagnetized, measured and bounded residual-flux vectors; minimum/nominal/
  maximum operating voltage; strong/weak source with documented short-circuit
  level and X/R; unloaded and agreed auxiliary-load cases; controlled switching
  as a comparison.
- **Instantaneous channels:** Three-phase breaker/winding current, source and
  transformer-bus phase voltage, neutral current/voltage, per-limb flux or a
  validated equivalent state, magnetizing current and pole state/time. CT
  secondary current is claimed only if a CT model is included.
- **KPIs:** Absolute and per-phase peak, first-cycle RMS, DC asymmetry and decay,
  voltage minimum/recovery, maximum limb flux, duration above the declared knee,
  and window-defined harmonic ratios. Rank current and voltage duty separately.
- **Analytical validation:** Reconstruct flux from integrated winding voltage
  after resistive drop; verify bases, vector-group displacement, no-load loss/
  current and expected closing-angle/residual-flux dependence. Declare FFT
  window and taper because inrush is non-stationary.
- **Numerical sensitivity:** Integration step, solver damping, event
  interpolation, saturation-curve density and simulation horizon; repeat the
  governing cases with the reviewed loss/hysteresis alternatives.
- **Acceptance limitations:** No universal inrush or second-harmonic threshold
  is valid. Acceptance needs nameplate/test data, excitation curve, core design,
  residual-flux basis, operating limits and actual relay logic. RMS excitation
  pairs cannot be copied unreviewed into an EMT peak-domain curve.
- **API versus native review:** The API can build, sweep residual states/events,
  simulate and export. Native review is required for core/winding connection,
  neutral path, saturation/hysteresis pages, residual initialization, curve
  plot and current-reference directions.

Official references: [DIgSILENT saturation conversion](https://www.digsilent.de/en/faq-reader-powerfactory/how-do-you-convert-the-saturation-characteristic-of-a-transformer-from-rms-values-to-peak-values-for-emt-studies.html),
[DIgSILENT inrush parameter identification](https://www.digsilent.de/en/faq-reader-powerfactory/how-do-you-configure-the-system-parameter-identification-for-emt-simulations.html),
[CIGRE TB 568 description](https://www.cigre.org/userfiles/files/News/CIGRE%20Study%20Committees-Capabilities%20%26%20Resources%20for%20Africa.PDF),
[IEC 60076-1](https://webstore.iec.ch/en/publication/588), and
[IEC 60076-3](https://webstore.iec.ch/en/publication/601).

## Study 04 - Capacitor-bank energization and back-to-back switching

- **Industrial question:** Do isolated-bank and back-to-back operations keep
  the bank, breaker, reactor and bus within their specified current, voltage,
  frequency, energy and switching-duty envelopes?
- **Minimum physical model:** Source impedance, bus/connection inductance,
  independent poles, actual bank connection and neutral, step capacitance,
  reactor R-L and losses. Back-to-back cases explicitly include the energized
  bank and short inter-bank path. Trapped charge is an initial state. Restrike
  needs a validated dielectric/arc model and is outside the ideal-switch base.
- **Scenario matrix:** First-bank/back-to-back; credible step combinations;
  point-on-wave coarse/refined scans; pole scatter; zero and positive/negative
  trapped-voltage patterns; source and connection impedance; reactor/loss
  tolerances; controlled/uncontrolled closing. Restrike is a separate extension.
- **Instantaneous channels:** Per-pole current and contact voltage, bus/bank
  phase voltages, each step current, reactor current/voltage, capacitor state,
  neutral current/voltage, pole state, and arrester V/I when present.
- **KPIs:** Peak/frequency/damping of inrush, inrush-current integral, maximum
  bank/bus voltage, maximum `di/dt`, reactor duty/energy, trapped voltage, and
  controlled-switching reduction against the same condition.
- **Analytical validation:** Derive each topology's equivalent L-C natural
  frequency; compare the initial oscillation and an energy-based peak estimate;
  verify reactive power from capacitance, connection and nominal voltage.
- **Numerical sensitivity:** Integration step, stray inductance, resistance/loss
  model and event interpolation. An ideal zero-inductance back-to-back loop is
  not physical.
- **Acceptance limitations:** Use actual IEC/manufacturer bank, reactor and
  breaker ratings. Ideal-switch results cannot establish breaker life, restrike
  probability or contact erosion. Internal units/fuses are outside the terminal
  equivalent unless explicitly represented.
- **API versus native review:** The API can set steps, initial `uC` states,
  events, sweeps and exports. Native review covers phase/neutral connection,
  trapped-charge state, inter-bank path, reactor placement and breaker detail.

Official references: [DIgSILENT capacitor switching](https://www.digsilent.de/en/faq-reader-powerfactory/do-you-have-an-example-on-capacitor-switching.html),
[DIgSILENT residual-voltage initialization](https://www.digsilent.de/en/faq-reader-powerfactory/i-want-to-model-the-residual-voltage-for-capacitor-switching-can-you-help-me.html),
[CIGRE TB 817](https://electra.cigre.org/313-december-2020/technical-brochures/shunt-capacitor-switching-in-distribution-and-transmission-systems.html),
[IEC 60871-1](https://webstore.iec.ch/en/publication/3770), and
[IEC TS 60871-3](https://webstore.iec.ch/en/publication/88033).

## Study 05 - Transformer saturation and residual-flux sensitivity

- **Industrial question:** Which uncertain magnetic inputs materially change
  the governing Study 03 current, recovery and protection conclusions?
- **Minimum physical model:** Reuse frozen Study 03. Vary only immutable,
  provenance-controlled peak excitation curves, knee region, air-core slope,
  core loss/hysteresis and physically admissible residual-flux states.
- **Scenario matrix:** Governing/representative Study 03 closings combined with
  data-supported low/base/high magnetic variants and admissible remanence;
  screen first, then refine dominant parameters and relevant source interactions.
- **Instantaneous channels:** Complete Study 03 set plus magnetizing V/I,
  per-limb saturation state or reconstructed threshold crossing, and exact
  parameter-set identifier/hash.
- **KPIs:** Study 03 KPIs, saturation duration/volt-seconds, normalized local
  sensitivity, ranked influence, interaction effects and uncertainty bands.
- **Analytical validation:** Overlay curves in physical units; verify monotonicity,
  continuity and rated-voltage no-load data; reconstruct flux independently;
  verify remanence constraints and unchanged transformer bases.
- **Numerical sensitivity:** Repeat dominant variants across step size and curve
  density. A sensitivity sign/ranking that changes numerically is not an
  engineering conclusion.
- **Acceptance limitations:** This does not replace factory excitation or
  remanence data. Arbitrary percentage bands are illustrative. Protection
  conclusions require actual relay, CT and windowing models.
- **API versus native review:** The API can clone types, apply the design and
  quantify sensitivity. Native review is required for curve overlays, core/
  hysteresis selection, provenance and shared-type mutation checks.

Official references: [DIgSILENT saturation guidance](https://www.digsilent.de/en/faq-reader-powerfactory/how-do-you-convert-the-saturation-characteristic-of-a-transformer-from-rms-values-to-peak-values-for-emt-studies.html),
[DIgSILENT parameter identification](https://www.digsilent.de/en/faq-reader-powerfactory/how-do-you-configure-the-system-parameter-identification-for-emt-simulations.html), and
[CIGRE TB 568 description](https://www.cigre.org/userfiles/files/News/CIGRE%20Study%20Committees-Capabilities%20%26%20Resources%20for%20Africa.PDF).

## Study 06 - Circuit-breaker transient recovery voltage

- **Industrial question:** After the specified interruption duty, does each
  contact voltage remain below the applicable breaker TRV capability with
  adequate peak and rate-of-rise margin?
- **Minimum physical model:** Source equivalent and capacitance; independent
  poles with selected zero-current/chopping/arc model; line/load capacitance and
  trapped charge; grounding; and a distributed line for short-line-fault duty.
  Measure voltage directly across each contact. Different duties do not share a
  generic envelope.
- **Scenario matrix:** Applicable terminal/short-line faults, fault type/level/
  location, first-pole-to-clear sequence, arcing time, pole scatter, source
  grounding/strength and capacitance tolerance. Add chopping/reignition only for
  the relevant technology and data.
- **Instantaneous channels:** Per-pole source/load voltage, contact voltage with
  polarity, current, command/contact state, neutral current and nearby node
  voltages, with a dense current-zero window.
- **KPIs:** Peak TRV, time to peak, standard-defined RRRV/reference-line result,
  current-zero time/slope, first-pole factor, envelope crossing and minimum
  peak/rate margin. Maximum adjacent-sample derivative is not RRRV.
- **Analytical validation:** Independently reproduce and unit-test the chosen
  IEC/manufacturer envelope; compare reduced-network L-C frequency and short-line
  travel time; verify contact voltage equals the terminal-voltage difference.
- **Numerical sensitivity:** Integration step, line fit, stray capacitance and
  arc/current-zero settings; require stable zero time, peak, time to peak and
  envelope margin.
- **Acceptance limitations:** Compliance requires exact breaker rating, duty,
  standard edition and manufacturer capability. The DIgSILENT example is a
  method, not a universal limit. An ideal switch cannot assess post-arc current,
  dielectric recovery or reignition.
- **API versus native review:** The API can configure duties, pole events,
  results and envelope comparison. Native review covers opening logic, curve,
  pole mapping, arc model, capacitances and current-zero/TRV overlay.

Official references: [DIgSILENT TRV example](https://www.digsilent.de/index.php/en/faq-reader-powerfactory/do-you-have-an-example-for-high-voltage-circuit-breakers-for-transient-recovery-voltage-trv-analysis.html),
[breaker-opening options](https://www.digsilent.de/en/faq-reader-powerfactory/what-are-the-options-available-for-breaker-switch-open-actions-in-rms-and-emt-simulation.html),
[vacuum-breaker model](https://www.digsilent.de/index.php/en/faq-reader-powerfactory/how-can-i-model-a-vacuum-circuit-breaker.html), and
[IEC 62271-100:2021+AMD1:2024](https://webstore.iec.ch/en/publication/62785).

## Study 07 - Faults with variable clearing

- **Industrial question:** How do fault type, position, impedance, inception
  angle and pole clearing affect making/interruption duty, I-squared-t, voltage
  recovery and protection-observable quantities?
- **Minimum physical model:** Documented sequence equivalents, transformer
  vector groups/grounding, frequency-appropriate lines/cables, physical fault
  terminals/sections and independent breaker poles. Mid-line faults require an
  explicit split. Constant resistance is not an arc model.
- **Scenario matrix:** Stage SLG/LL/LLG/three-phase faults by representative
  location, then resistance/source strength, inception-angle refinement and
  main/backup or pole-discrepant clearing. Reclosing/secondary arc are separate.
- **Instantaneous channels:** Phase V/I at breakers and fault, pole state,
  neutral/ground/fault-branch current, fault voltage and each source contribution.
  Derived sequence quantities declare their window/filter.
- **KPIs:** Absolute/first-cycle peak, initial symmetrical RMS, DC offset/decay,
  source contribution, current at contact separation/zero, I-squared-t, voltage
  minimum/recovery and negative-/zero-sequence magnitude.
- **Analytical validation:** Compare initial symmetrical current/contributions
  with independently configured IEC 60909; check peak/DC trend with X/R,
  three-phase current with Thevenin impedance and SLG current with the
  zero-sequence network; verify actual recorded event order.
- **Numerical sensitivity:** Refine around inception/opening, test close event
  ordering, compare line models and converge peak, zero, I-squared-t and recovery.
- **Acceptance limitations:** IEC 60909 is a benchmark, not a reference for every
  EMT sample, arc or recovery. Breaker/CT/relay conclusions need their models.
  Ideal sources do not represent converter current limiting.
- **API versus native review:** The API can create locations/events, sweep and
  compare. Native review covers line splits, phase selection, grounding,
  zero-sequence paths, pole mapping, timeline and signal polarity.

Official references: [DIgSILENT SLG EMT example](https://www.digsilent.de/en/faq-reader-powerfactory/do-you-have-an-example-of-modelling-a-single-phase-line-to-ground-fault.html),
[breaker-opening options](https://www.digsilent.de/en/faq-reader-powerfactory/what-are-the-options-available-for-breaker-switch-open-actions-in-rms-and-emt-simulation.html), and
[IEC 60909-0:2026](https://webstore.iec.ch/en/publication/68454).

## Study 08 - Lightning impulse and travelling waves

- **Industrial question:** For traceable stroke and operating conditions, what
  travelling-wave, flashover and arrester stresses reach line/substation
  insulation, and which uncertainties govern the insulation margin?
- **Minimum physical model:** Conductor/tower geometry; distributed,
  frequency-dependent phase-domain line fitted over the study band; phase and
  shield conductors, towers/coupling and grounding; EMT impulse at the strike
  node; reviewed threshold/volt-time/leader-progression insulator switch; and
  point-by-point metal-oxide arrester V-I curve, lead inductance and energy.
- **Scenario matrix:** Separate direct phase strike, shield-wire/tower strike and
  terminal injection. Vary data-supported first/subsequent stroke peak,
  front/tail/polarity, location, power-frequency angle, tower grounding, shield/
  arrester configuration, insulator model and termination. Do not mix waveform
  definitions under one label.
- **Instantaneous channels:** Source current, conductor/tower V/I at strike and
  observations, insulator voltage/state, footing V/I, arrester V/I/energy and
  equipment terminal voltage, with distributed samples for a distance-time map.
- **KPIs:** Source peak/front/tail, first-arrival time/velocity, incident and
  reflected peaks/times/polarity, insulator stress/flashover, arrester residual
  voltage/current/energy and margin to the selected withstand level.
- **Analytical validation:** Travel time `distance/velocity`, reduced
  surge-impedance reflection, source charge and arrester-energy integration;
  frequency-sweep versus EMT/FFT line response; and standalone waveform
  verification before network connection.
- **Numerical sensitivity:** Step versus front/shortest travel time, span/tower
  segmentation, line-fit range, travel-time frequency, footing/lead inductance
  and insulator model; converge arrival, peak, flashover and energy.
- **Acceptance limitations:** Acceptance needs IEC coordination levels and
  equipment-specific transformer, arrester and insulator data. Deterministic
  flashover does not establish outage rate. PowerFactory 2024 `ElmImpulse`
  provides IEC 62305-1, Heidler, double-exponential, and CIGRE families; each
  still needs traceable project parameters. Constant footing resistance is not
  a broadband soil model.
- **API versus native review:** The API can configure sources, line sections,
  sweeps and distance-time processing after schema verification. Native review
  is mandatory for geometry/order, shielding/grounding, strike node, line-fit
  report, insulator model, arrester curve/lead and the spatial diagram.

Official references: [DIgSILENT lightning source](https://www.digsilent.de/index.php/en/faq-reader-powerfactory/how-can-i-model-a-lightning-current-source-in-powerfactory-emt-simulation.html),
[CIGRE-waveform limitation](https://www.digsilent.de/index.php/en/faq-reader-powerfactory/how-do-you-model-an-lightning-impulse-according-to-the-cigre-waveform.html),
[line-model configuration](https://faq.digsilent.de/en/faq-reader-powerfactory/how-to-configure-overhead-line-and-cable-models-for-emt-simulations.html),
[insulator flashover](https://www.digsilent.de/en/faq-reader-powerfactory/how-do-you-model-the-flashover-across-transmission-line-insulators-during-lightning-transients/category/dynamic-simulation.html),
[soil ionisation](https://www.digsilent.de/index.php/en/faq-reader-powerfactory/how-do-you-model-a-variable-resistance-to-consider-soil-ionisation-in-lightning-transient-emt-simulations.html),
[CIGRE TB 839](https://electra.cigre.org/317-august-2021/technical-brochures/procedures-for-estimating-the-lightning-performance-of-transmission-lines-new-aspects-and-guide-to-procedures-for-estimating-the-lightning-performance-of-transmission-lines.html),
[IEC 60071-1](https://webstore.iec.ch/en/publication/59657),
[IEC 60071-2](https://webstore.iec.ch/en/publication/64145), and
[IEC 60099-4](https://webstore.iec.ch/en/publication/735).

## Blocking inputs before an implemented claim

1. Studies 03/05 lack transformer test/nameplate/core data and defensible
   remanence bounds; installed-version residual-flux and limb-flux identifiers
   need engine introspection.
2. Study 04 lacks the bank connection/steps, reactor/connection impedance,
   trapped-charge basis and breaker ratings.
3. Study 06 lacks an exact breaker, duty-specific TRV envelope, arcing data,
   capacitances and short-line geometry; no pass/fail claim is possible.
4. Study 07 needs frozen sequence/grounding equivalents, physical fault
   locations and clearing sequence.
5. The Study 08 propagation baseline is implemented, but geometry, grounding,
   shield wires, insulator, arrester and withstand data remain mandatory before
   an equipment-specific insulation or outage-rate conclusion.
6. PowerFactory 2024 attributes, event options and instantaneous result
   identifiers used by Studies 03–08 have engine-backed tests; new equipment
   variants require the same version-specific preflight before a full campaign.
