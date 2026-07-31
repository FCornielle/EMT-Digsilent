# Study 02 Assumptions and Data Boundaries

## Current maturity

Study 02 has an idempotent PowerFactory API builder, a parameter register,
bonding matrix, analytical checks, plotting pipeline, native-diagram layout,
and PowerFactory object contract. The builder still requires execution and
visual review in the interactive PowerFactory 2024 application. An EMT waveform
or numerical baseline is not claimed yet.

## Model boundary

- One 220 kV, 40 km, three-phase XLPE cable circuit.
- Energization from a Thevenin source through a three-pole breaker.
- Open receiving end for the first switching benchmark.
- Metallic screen represented explicitly in the target `TypCab`/`TypCabsys`
  implementation.
- Isolated, single-point, both-end, and cross-bonded screen alternatives.
- Arresters, terminal sealing ends, joint resistances, and shunt reactors are
  deferred until the basic cable-system model is verified.

## Data classification

Conductor and radial dimensions, catalogue capacitance, and inductance come
from the ABB 220 kV, 1,200 mm2 copper row in Table 37 of *XLPE Submarine Cable
Systems*. The DIgSILENT tutorial method is used to preserve diameter over
insulation and calibrate equivalent permittivity when semiconducting-layer
dimensions are unavailable.

The catalogue row does not provide every material or construction parameter.
The radial region outside the lead sheath is therefore homogenized as an
equivalent oversheath, with no explicit armour or serving. Installation
geometry, soil, resistivities, loss tangents, sequence screening values, and
bonding details remain transparent assumptions. A project application must
replace them with the project cable sheet, installation geometry,
bonding-section lengths, earth continuity conductor, grounding impedances,
joint details, and measured soil properties.

## Numerical boundary

The declared 2.5 us time step is a starting point. It provides multiple samples
within the first-order cable travel time, but it is not accepted until the EMT
model passes time-step convergence and frequency-sweep versus EMT/FFT checks.
