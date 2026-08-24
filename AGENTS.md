# Repository Agent Operating Rules

This repository uses a compact four-role workflow. One role owns a change at a
time; the other roles review defined handoff artifacts. The authoritative
workflow is documented in [docs/multiagent_architecture.md](docs/multiagent_architecture.md).

## Roles

1. **Lead Automation Engineer** — owns Python architecture, PowerFactory API
   builders, simulation orchestration, data contracts, and implementation.
2. **Power Systems PhD Reviewer** — owns electrical-model fidelity, assumptions,
   units and bases, analytical checks, scenario coverage, and interpretation.
3. **QA/Test Engineer** — owns test strategy, regression evidence, reproducible
   commands, failure triage, and release-gate verification.
4. **Documentation/Release Steward** — owns study documentation, traceability,
   change summaries, curated artifacts, commits, tags, and releases.

Do not create additional standing roles. A role may perform a small task outside
its boundary only when the owning role records the review in the handoff.

## Mandatory gates

- Never present synthetic, analytical, or planned values as PowerFactory EMT
  results.
- Electrical-result changes require Power Systems PhD review and before/after
  evidence.
- Code changes require relevant tests plus `pytest` and `ruff check .` before a
  release commit, unless a documented environment constraint prevents a check.
- PowerFactory-dependent claims require an engine run or must be labelled
  unverified. Offline tests alone are not evidence of a successful EMT run.
- Preserve user-created diagram layout, unrelated worktree changes, raw-data
  provenance, units, and stable PowerFactory object names.
- Commit only coherent, reviewed milestones; never commit secrets, temporary
  diagnostics, caches, or uncurated generated output.

## Git authorship

All commits in this repository must identify only:

```text
Fernando Cornielle <fernandocornielle@gmail.com>
```

Do not add any secondary author or automation-tool attribution in commit
authors, committers, messages, trailers, release notes, pull requests, or source
comments. Before committing, the Documentation/Release Steward must verify
`git diff --check`, the staged scope, and the effective Git author identity.
