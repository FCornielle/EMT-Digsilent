# Contributing

## Workflow

1. Create a focused branch.
2. Add or update engineering configuration before changing analysis code.
3. Run `pytest` and `ruff check .`.
4. Keep generated study outputs out of Git.
5. Use imperative commit subjects such as `Add transformer inrush scenario`.

## Engineering review checklist

- Are all inputs traceable and correctly unitized?
- Are pu bases stated?
- Do events target the intended object and phases?
- Are PowerFactory command return codes checked?
- Was a time-step convergence study performed?
- Are result-variable codes valid for the selected simulation domain?
- Are any sample/synthetic results unmistakably labelled?

Changes that alter an accepted electrical result should include the reason,
before/after metrics and reviewer sign-off.

