# Multi-Agent Engineering Architecture

## Purpose

The project uses four durable roles to separate implementation, independent
power-system review, verification, and publication without adding unnecessary
coordination layers. Roles describe responsibilities, not commit authorship.

## Operating model

```text
Lead Automation Engineer
        |
        v
Power Systems PhD Reviewer
        |
        v
QA/Test Engineer
        |
        v
Documentation/Release Steward
        |
        +---- failed gate ----> owning role
```

A study normally moves through the roles in this order. Review can run in
parallel when artifacts are stable, and the role named for each quality gate
must examine its evidence. Findings return to the role that owns the affected
artifact.

## Roles and ownership

### 1. Lead Automation Engineer

Owns reusable `src/pfemt` code, study builders, PowerFactory API integration,
events, result-channel contracts, exports, analysis pipelines, and idempotency.
The handoff contains the implementation diff, configuration/schema changes,
commands to reproduce the model and run, and known technical limitations.

### 2. Power Systems PhD Reviewer

Owns independent review of network topology, equipment models, parameter
provenance, units and bases, EMT applicability, initialization, event timing,
numerical resolution, scenario completeness, analytical scale checks, and KPI
interpretation. The handoff is an engineering review note containing assumptions,
expected physical behavior, checks performed, deviations, and disposition.

### 3. QA/Test Engineer

Owns risk-based tests, unit and regression coverage, configuration validation,
result-contract checks, deterministic reruns, PowerFactory integration evidence,
and defect reporting. The handoff is a verification record with environment,
exact commands, pass/fail counts, engine evidence where required, and unresolved
risks. QA does not accept a result merely because the command completed.

### 4. Documentation/Release Steward

Owns study READMEs, methodology clarity, references, curated figures and compact
baselines, changelog/release notes, repository hygiene, commits, tags, and pushes.
The handoff is a release checklist linking the engineering review, verification
record, included artifacts, commit identifier, and remaining limitations.

## Quality gates

| Gate | Required evidence | Approver |
|---|---|---|
| Implementation | Named-object contract, reproducible commands, focused tests | Lead Automation Engineer |
| Engineering | Traceable inputs, analytical checks, physical interpretation, declared limits | Power Systems PhD Reviewer |
| Verification | `pytest`, `ruff check .`, regression checks, and engine run when claimed | QA/Test Engineer |
| Publication | README/result consistency, curated artifacts, clean diff, authorship check | Documentation/Release Steward |

Any unavailable check is recorded as a limitation, not silently waived. A study
status advances only when its required evidence exists: planned, engineering
basis, implemented, or verified baseline.

## Commit and release policy

- Commit at coherent milestones: study scaffold, model implementation, verified
  baseline, or documentation/release closure.
- Keep commits focused and use imperative subjects. Do not rewrite unrelated
  user changes.
- Run `git diff --check`, review `git diff --cached`, then verify the configured
  identity before every commit.
- The sole author and committer identity is
  `Fernando Cornielle <fernandocornielle@gmail.com>`.
- Keep the configured Fernando Cornielle identity as the only attribution in
  repository history and release material.
- Push only after the applicable gates pass. Tags and release notes must state
  verified scope, PowerFactory version, reproduction commands, and limitations.

## Definition of done for an EMT study

A completed verified baseline includes a reproducible PowerFactory model,
versioned inputs and event matrix, explicit result variables and units, raw-to-
normalized export traceability, analytical and numerical checks, reviewed KPIs,
educational figures, a study README, passing quality gates, and a restorable
project archive. Visual refinement may follow, but it must not change electrical
connectivity without repeating engineering and QA review.
