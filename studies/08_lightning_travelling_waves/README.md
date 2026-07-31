# Study 08 — Lightning Impulse and Travelling Waves

> **Status: planned.** Waveform source, tower/cable geometry, and insulation
> limits have not yet been implemented.

## Industrial question

What terminal and internal equipment stresses result from direct/indirect
lightning impulses, line/cable wave propagation, reflections, flashover, and
surge-arrester operation?

## Target PowerFactory model

- geometric frequency-dependent line or cable model;
- towers, earth wires/screens, grounding impedances, and terminal substations;
- configurable current impulse source and strike location;
- line-insulator flashover model where required;
- arresters with reviewed voltage-current characteristic and energy channel.

## Scenario matrix and KPIs

The campaign will vary peak current, front/tail time, polarity, strike location,
grounding resistance, operating voltage, arrester location, and equipment
configuration. KPIs are terminal/internal peak voltage, wave-arrival time,
insulation margin, arrester current/energy, and flashover outcome.

## Required figures and completion gate

Required outputs are the native one-line, impulse definition, distance-time
wave map, terminal voltage/current panels, reflection timeline, arrester energy,
scenario ranking, and mesh/time-step sensitivity. Completion requires waveform
and insulation-level provenance plus analytical travel-time verification.
