# Study 10 — Protection Studies with Instantaneous EMT Values

> **Status: planned.** Relay algorithms and instrument-transformer models are
> not yet selected.

## Industrial question

Do CT/VT transients, waveform distortion, DC offset, saturation, converter
current limiting, and sampling/filtering alter pickup, direction, timing, or
selectivity compared with fundamental-frequency studies?

## Target model

- reusable fault/switching cases from Studies 03, 06, 07, and 09;
- CT/CVT or sensor transient models where decision-relevant;
- sampled instantaneous measurements;
- documented relay filtering, phasor estimation, logic, timers, and trip output;
- explicit breaker operation and feedback.

## Main KPIs

- pickup/dropout/trip time and asserted elements;
- measured versus primary current/voltage error;
- directional/polarizing quantity margin;
- harmonic restraint/blocking behavior;
- main/backup selectivity and breaker clearing time.

## Required figures and completion gate

Required outputs are the one-line/protection-zone diagram, primary/secondary
waveforms, measurement error, relay operating quantities, digital state
timeline, trip matrix, and sensitivity plots. Completion requires independently
tested relay logic and traceable settings.
