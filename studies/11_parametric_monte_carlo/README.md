# Study 11 — Parametric Sweeps, Monte Carlo, and Worst-Case Search

> **Status: foundation implemented.** Deterministic point-on-wave and seeded
> Monte Carlo scenario generation exist; risk-oriented orchestration is planned.

## Industrial question

How can uncertain operating conditions, tolerances, switching statistics, and
event timings be converted into a reproducible stress distribution and a
reviewable governing case?

## Method

1. define distributions, correlations, truncation, and provenance;
2. separate epistemic parameter uncertainty from random event variation;
3. generate deterministic manifests with seeds and immutable case identifiers;
4. execute PowerFactory batches with failure/retry accounting;
5. calculate KPIs and preserve failed/non-converged cases;
6. estimate quantiles and confidence intervals;
7. refine the tail with structured search without hiding the sampled evidence;
8. replay the governing case exactly.

## Main KPIs and figures

KPIs are study-specific stress metrics plus convergence/failure rate and
runtime. Required figures include input distributions, correlation checks,
convergence versus sample count, KPI histogram/CDF, parameter-stress scatter,
sensitivity ranking, tail cases, and deterministic replay comparison.

## Completion gate

Implemented status requires schema-validated distributions, seed/replay tests,
parallel-safe execution, resumable manifests, statistical verification, and at
least one fully integrated EMT study using the workflow.
