# QA Strategy for Studies 03–08

This strategy makes study maturity evidence-based. The versioned status source
is [`config/study_delivery.yaml`](../config/study_delivery.yaml); a README or a
plot alone never establishes that a PowerFactory EMT run was executed.

## Test pyramid

| Layer | Scope | Required evidence |
|---|---|---|
| Portable unit tests (many) | Configuration schema and units, stable scenario IDs/order, event timing, analytical calculations, parser fixtures, KPI extraction, plotting from fixture data | Tests run without importing or opening PowerFactory |
| Regression/contract tests (medium) | Scenario-manifest hashes, engineering tolerances, normalized-column contracts, delivery status, baseline metadata, and deterministic figure inventory | Versioned YAML/CSV/JSON fixtures and exact schema checks |
| Opt-in engine integration (few) | Build the same model twice, resolve result-variable codes, execute a minimal EMT case, export CSV, and reopen/archive the project | `pytest.mark.powerfactory` plus `PFEMT_RUN_INTEGRATION=1` |
| Delivery verification (one per release) | Full campaign traceability and archive integrity | Execution metadata, retained result summary, `.pfd`, and SHA-256 manifest |

The default CI suite exercises the first two layers. PowerFactory tests must
remain skipped unless the operator explicitly opts in; installation discovery
or a GUI session must never make an offline test execute the engine by accident.

## Cross-study acceptance gates

1. **Configuration validation:** required quantities, units, bases, object names,
   event order, and physically meaningful ranges fail fast with useful errors.
2. **Deterministic campaign:** the same configuration produces identical,
   uniquely ordered scenario IDs and switching times. A versioned manifest or
   hash detects campaign drift.
3. **Analytical check:** each case has at least one independent hand-calculation
   or published benchmark with a stated tolerance and domain of validity.
4. **Parser contract:** two-row PowerFactory headers map to stable, unique,
   unit-bearing columns. Missing, duplicated, or wrong-unit channels fail.
5. **Metrics and plots:** KPI tests use small committed fixtures. Plot tests check
   labels, units, series coverage, output creation, and finite values—not exact
   pixels.
6. **Idempotent builder:** two builds create no duplicate project, study case,
   network element, event, result object, diagram, or annotation; all references
   still point to the configured objects.
7. **Opt-in integration:** a minimal EMT run validates object attributes,
   command return codes, configured result identifiers, CSV export, and cleanup.
8. **Archive integrity:** a non-empty PFD is exported through PowerFactory and
   its exact SHA-256 is recorded beside the archive.
9. **Result truth:** synthetic, analytical, and fixture data may test software,
   but cannot be presented as executed EMT output.

## Case-by-case acceptance matrix

| Study | Configuration and deterministic scenarios | Independent analytical acceptance | KPI/parser and plotting acceptance | PowerFactory acceptance |
|---|---|---|---|---|
| **03 Transformer energization** | Validate vector group, ratings, leakage data, nonlinear curve monotonicity, air-core slope, residual flux per limb, pole scatter, and closing-angle grid. IDs encode closing/residual-flux state in fixed order. | Unsaturated volts-per-turn flux integral and source short-circuit current agree within stated modelling tolerance; limiting inrush values remain physically bounded. | Parse phase current, bus voltage, and limb flux with units. Test peak/RMS current, flux, decay, and harmonics; create waveform, spectrum, heatmap, ranking, and convergence plots. | Build twice without duplicate transformer, curve, breaker, events, or channels. Minimal run proves residual-flux initialization and three-pole switching. |
| **04 Capacitor-bank energization** | Validate bank MVAr/capacitance, section count, reactor and stray inductance, damping, trapped charge, restrike order, angle, and pole scatter. IDs distinguish isolated and back-to-back cases. | Computed capacitance, isolated/back-to-back LC frequency, stored energy, and ideal peak-current bounds agree with configured quantities. | Parse bus/capacitor voltage, bank/reactor current, and energy channels. Test peak, frequency, `di/dt`, and equipment duty; create waveform, spectrum, duty, heatmap, and convergence plots. | Build twice without duplicate banks, sections, reactors, breakers, or events. Minimal runs cover first-bank and back-to-back paths. |
| **05 Saturation sensitivity** | Inherit a pinned Study 03 baseline; validate curve provenance, knee variants, loss and air-core parameters, residual flux, and reproducible sweep ordering. Reject silent curve rescaling. | Each curve is monotonic and continuous; knee/air-core slopes and flux integration match the versioned curve data. Sensitivity signs and finite-difference calculations are tested. | Reuse Study 03 parser contract. Test saturation duration, harmonic ratios, decay, and sensitivity coefficients; create curve overlays, residual-flux maps, tornado, harmonic, and convergence plots. | Build variants without mutating the frozen Study 03 source model. Repeated runs restore baseline attributes after every scenario. |
| **06 Circuit-breaker TRV** | Validate fault topology, pole sequence, current-zero/clearing times, terminal and short-line capacitances, envelope provenance, and interpolation range. IDs preserve fault/pole/time ordering. | Short-line travel time and initial RRRV estimate are independently calculated; envelope interpolation is checked at breakpoints and outside-range input is rejected. | Parse pole currents and voltages on both breaker sides. Test current zero, peak TRV, time to peak, interval-defined RRRV, and margin; create zero zoom, per-pole TRV, envelope, ranking, and sensitivity plots. | Build twice without duplicate faults, breakers, pole events, or result channels. Minimal run demonstrates voltage difference across each open pole after interruption. |
| **07 Variable-clearing faults** | Validate fault type/phases, location, resistance, inception angle, main/backup clearing order, pole discrepancy, and reclose logic. IDs are unique over the complete Cartesian campaign. | Initial symmetrical current and X/R-derived DC envelope agree with an independent network-equivalent calculation; solid-fault limits and sequence relationships are checked. | Parse phase/sequence voltage and current. Test first-cycle RMS, absolute peak, DC offset, `I²t`, voltage recovery, and sequence content; create event, waveform, comparison, heatmap, and convergence plots. | Build each fault class twice without stale events. Minimal runs cover SLG, LL, LLG, and three-phase faults and deterministic event ordering. |
| **08 Lightning and travelling waves** | Validate impulse definition, line/cable geometry, frequency-dependent model, strike location, grounding, arrester V-I points, and insulation levels. IDs order impulse/location/grounding/arrester states deterministically. | Impulse peak/front/tail construction, surge impedance, one-way travel time, reflection coefficients, and simple arrester-energy integral meet stated tolerances. | Parse terminal/internal voltage, lightning/arrester current, and arrester energy. Test arrival time, peak stress, insulation margin, reflection timing, and flashover state; create impulse, distance-time, terminal, reflection, energy, ranking, and discretization plots. | Build twice without duplicate strike sources, towers, flashover controls, arresters, or channels. Minimal run verifies first-arrival timing and arrester conduction. |

## Result-provenance rule

Fixtures must live under test data or analytical references and be labelled as
such. A study may claim `engine_verified` only when its manifest entry declares:

- `result_provenance: powerfactory_emt`;
- retained executed-result files and machine-readable result metadata;
- metadata fields `engine: DIgSILENT PowerFactory`, `simulation_type: EMT`, and
  `execution_status: executed`;
- the exported PFD and a matching SHA-256 manifest.

The regression gate rejects the word `synthetic` in executed-result metadata.
Generated illustrations may explain a method, but must never be placed in an
executed baseline or captioned as a PowerFactory result.

## Maturing a study

The manifest has three monotonic stages:

1. `planned`: the study README is an explicit method contract and
   `result_provenance` is `not_executed`.
2. `offline_ready`: all portable gates in the manifest have at least one
   existing evidence path. The integration test is marked `powerfactory` and
   guarded by `PFEMT_RUN_INTEGRATION`; result and archive evidence stay empty.
3. `engine_verified`: the full campaign has executed, provenance metadata and
   retained summaries are versioned, and the final PFD hash is verified.

Evidence paths are repository-relative. Update one study entry in the same
commit as its implementation or execution evidence. Never advance the stage to
make a failing gate pass; add the missing evidence or keep the earlier stage.

Run the contract locally with:

```powershell
pytest tests/regression/test_study_delivery_contract.py
ruff check tests/regression/test_study_delivery_contract.py
```

Run all portable checks before an important commit:

```powershell
pytest -m 'not powerfactory'
ruff check .
```

Engine verification remains explicit:

```powershell
$env:PFEMT_RUN_INTEGRATION = '1'
pytest -m powerfactory
```
