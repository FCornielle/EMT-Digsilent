# Study 09 — Detailed Grid-Following and Grid-Forming IBR Models

> **Status: planned.** Converter controls and manufacturer-specific parameters
> are not included yet.

## Industrial question

How do detailed converter switching/control models respond to weak-grid
disturbances, faults, voltage-angle changes, current limiting, and protection
interactions in the EMT time domain?

## Target model variants

- grid-following current-control model with PLL;
- grid-forming voltage-control model with declared outer-loop strategy;
- average-value and detailed switching variants where available;
- DC source/link, transformer, filters, cables, and grid equivalent;
- current limiting, blocking, restart, and protection logic.

## Scenario matrix and KPIs

Scenarios will vary SCR/XR, operating P/Q, voltage/frequency disturbance, fault
type, control gains, current limit, and model fidelity. KPIs include current
limit tracking, P/Q recovery, DC-link excursion, PLL or angle stability,
harmonic spectrum, unbalance, and control/protection state transitions.

## Required figures and completion gate

Required outputs are the native one-line and control block diagram, steady-state
initialization audit, instantaneous AC/DC waveforms, dq trajectories, state
timeline, harmonic spectrum, SCR sensitivity, and model-comparison plots.
Completion requires parameter provenance and initialization/control validation.
