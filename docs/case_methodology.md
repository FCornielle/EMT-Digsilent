# Standard Methodology for Every EMT Case

Every implemented case must follow the same review sequence. A roadmap entry is
not considered implemented until all applicable items are present.

1. **Engineering question** — state the decision that the simulation supports.
2. **Acceptance metrics** — define the electrical quantities, bases, units, and
   statistical interpretation before running cases.
3. **System boundary** — identify the retained network, equivalents, interfaces,
   and omitted equipment.
4. **Input basis** — classify each value as example, assumed, calculated,
   measured, utility, or vendor data.
5. **PowerFactory objects** — list element classes, stable names, types,
   controllers, commands, events, and result files.
6. **Native single-line diagram** — generate and export the linked PowerFactory
   `IntGrfnet`/`SetDeskpage` representation.
7. **Initialization** — explain pre-event topology, steady state, initial flux,
   trapped charge, controller state, or other history-dependent conditions.
8. **Event matrix** — define event type, location, phases, time, scatter, clearing
   sequence, and parameter sweep.
9. **Result contract** — version every monitored variable, object, unit, sample
   rate, and normalization rule.
10. **Numerical verification** — demonstrate time-step/output-step sensitivity
    and solver/model settings appropriate to the transient bandwidth.
11. **Independent comparison** — use an analytical estimate, published example,
    standard envelope, frequency sweep, alternative model, or second tool.
12. **Visualization** — include the native one-line, parameters, representative
    waveforms, scenario comparison, worst-case ranking, and verification plot.
13. **Interpretation** — distinguish observed physics, numerical artifacts,
    modelling uncertainty, and decision-relevant stress.
14. **Reproducibility** — preserve configuration, scenario manifest, metadata,
    compact reference results, tests, and rerun instructions.
15. **Engineering boundary** — identify the additional project data and review
    required before using the example in a design decision.

Study-specific READMEs should use numbered sections and link directly to the
configuration, parameter register, compact references, and curated figures.
