# Study 02 Assumptions and Data Boundaries

## Current maturity

Study 02 is at the engineering-basis stage. The parameter register, bonding
matrix, analytical checks, plotting pipeline, and PowerFactory object contract
are defined. An EMT waveform or numerical baseline is not claimed yet.

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

All electrical and geometric values are transparent engineering-example data.
They are not manufacturer data. A project application must replace them with
the cable data sheet, installation geometry, bonding-section lengths, earth
continuity conductor, grounding impedances, joint details, and measured soil
properties.

## Numerical boundary

The declared 2.5 us time step is a starting point. It provides multiple samples
within the first-order cable travel time, but it is not accepted until the EMT
model passes time-step convergence and frequency-sweep versus EMT/FFT checks.
