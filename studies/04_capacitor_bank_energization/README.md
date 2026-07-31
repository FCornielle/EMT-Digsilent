# Study 04 — Capacitor-Bank Energization and Back-to-Back Switching

> **Status: planned.** No EMT result is claimed yet.

## Industrial question

What voltage, current, frequency, and energy duties arise during isolated-bank
and back-to-back capacitor switching, and are the breaker, reactor, bus, and
capacitor units adequately rated?

## Target PowerFactory model

- source, bus, breaker, bank sections, series reactor, and stray inductance;
- existing energized bank for back-to-back scenarios;
- pole-by-pole closing events with point-on-wave control;
- optional trapped charge and restrike cases;
- native PowerFactory one-line and instantaneous terminal measurements.

## Scenario matrix

1. first-bank versus back-to-back energization;
2. bank size and number of energized steps;
3. point on wave and pole scatter;
4. source and bus inductance;
5. reactor tolerance and damping resistance;
6. trapped charge and optional restrike timing.

## Main KPIs

- peak and frequency of inrush current;
- peak capacitor and bus voltage;
- current derivative and breaker duty;
- reactor voltage/current and energy;
- discharge/restrike transient severity.

## Required figures and completion gate

The case will include a native one-line, parameter overview, switching
waveforms, frequency spectrum, scenario heatmap, equipment-duty comparison, and
time-step sensitivity. Implemented status requires an analytical LC-frequency
check and a versioned PowerFactory baseline.
