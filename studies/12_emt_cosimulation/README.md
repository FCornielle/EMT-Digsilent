# Study 12 — EMT–EMT and RMS–EMT Co-Simulation

> **Status: planned.** Interface model, partition, and reference monolithic case
> have not yet been selected.

## Industrial question

Can a partitioned simulation reproduce the decision-relevant waveforms and
KPIs of the reference model while reducing runtime or allowing interaction with
another specialist EMT/control tool?

## Target variants

- PowerFactory EMT–EMT partition with internal solver coupling;
- PowerFactory RMS–EMT partition;
- external co-simulation interface where a justified tool/model is available;
- matched reference case without partitioning.

## Verification method

1. define the electrical partition and exchanged variables;
2. document coordinate systems, bases, interpolation, delay, and time steps;
3. initialize both domains consistently;
4. run identical steady-state and disturbance cases;
5. compare interface power balance, waveforms, events, KPIs, and runtime;
6. sweep communication step and interface impedance;
7. identify stability/accuracy limits.

## Required figures and completion gate

Required outputs are the partition diagram, signal/data-flow map, initialization
residuals, interface waveforms, power-balance error, monolithic-versus-coupled
overlay, communication-step sensitivity, and runtime comparison. Completion
requires a versioned reference case and quantitative error tolerances.
