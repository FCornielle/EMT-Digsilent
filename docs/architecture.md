# Architecture

## Design goals

1. Separate the proprietary simulation engine from portable analysis code.
2. Keep every engineering input in a reviewable YAML/CSV file.
3. Make internal PowerFactory execution and external engine mode use the same
   workflow.
4. Fail explicitly on missing objects, variables, attributes and command errors.
5. Preserve raw exports while producing stable normalized data.

## Data flow

```text
study YAML
   │
   ├── model builder ── PowerFactory project / Study Case / IntGrfnet diagram
   │                         │
   ├── scenario manifest     ├── ComInc (EMT initial conditions)
   │                         ├── EvtSwitch
   │                         ├── ComSim
   │                         └── ElmRes → ComRes
   │                                      │
   └────────────────────────────────── raw CSV
                                          │
                         pandas normalization
                                          │
             analytical checks ── metrics ── figures ── report
```

The only modules importing `powerfactory` are the runtime connection helpers.
Scenario generation, metrics, plotting and reporting can therefore run on CI
without opening the simulation application.

## Diagram contract

The electrical model and its single-line diagram are separate PowerFactory
objects linked by `IntGrf.pDataObj`. The builder first runs `ComSgllayout` to
insert graphical representations and then applies deterministic horizontal
coordinates. If `ComSgllayout` previously created a diagram such as
`GRID_230KV(1)`, the builder detects it by its linked electrical objects,
reuses it, renames it, and applies the same layout instead of creating a
duplicate. `ComWr` exports the active `SetDeskpage` from the interactive
Graphics Board. Matplotlib is used for result plots only; it does not redraw
the PowerFactory network diagram.

## Object naming

Every object referenced by automation has a stable uppercase ASCII name. Display
titles may use accents and spaces; API identifiers do not. Exact class suffixes
(`.ElmTerm`, `.ElmLne`, `.ElmCoup`) are used to prevent ambiguous lookup.

## Results contract

Raw `ComRes` exports remain immutable. `analysis.column_map` maps PowerFactory
headers to these stable columns:

| Column | Meaning | Unit |
|---|---|---|
| `time_s` | simulation time | s |
| `v_recv_[abc]_kv` | instantaneous receiving-end phase voltage | kV |
| `i_send_[abc]_ka` | instantaneous sending-end phase current | kA |

Changing a monitored signal or unit is a schema change and must update tests and
study documentation.

PowerFactory result-variable identifiers are case-sensitive: this study uses
`m:U:[A|B|C]` for kV and `m:I:bus1:[A|B|C]` for kA. Their lowercase variants
return pu values and are intentionally not used in the engineering CSV.
