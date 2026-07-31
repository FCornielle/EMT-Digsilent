# Study 06 — Circuit-Breaker Transient Recovery Voltage

> **Status: planned.** No TRV envelope comparison has been performed yet.

## Industrial question

What transient recovery voltage appears across each breaker pole after current
interruption, and how do peak TRV, rate of rise, time to peak, and pole factors
compare with the applicable breaker capability envelope?

## Target cases

- terminal and short-line faults;
- first-pole-to-clear conditions;
- single-, two-, and three-phase interruption;
- variable arcing/current-zero and clearing times;
- source/cable/line-side capacitance and trapped charge;
- reactor or transformer limited-fault duties where applicable.

## Main KPIs

- peak TRV and time to peak;
- RRRV over explicitly defined time intervals;
- current-zero slope and post-arc context;
- pole discrepancy and first-pole factor;
- margin to the selected standard/manufacturer envelope.

## Required figures and completion gate

The README will show the native one-line, interruption sequence, current-zero
zoom, per-pole TRV, envelope overlay, scenario ranking, and numerical
sensitivity. Implemented status requires explicit envelope provenance and
reviewed interpolation rather than a generic pass/fail threshold.
