# Assumptions and engineering limits

This repository is an industrial-style **example**, not a design certificate.

- The source is represented by a 230 kV Thevenin equivalent with 10 GVA
  short-circuit power.
- The receiving end is open; no shunt compensation or surge arresters are
  included in the base case.
- The line uses sequence parameters in `TypLne` so the example remains
  transparent and portable. For an insulation-coordination deliverable, replace
  them with validated tower, conductor, earth-wire and soil-resistivity geometry.
- `ElmLne.i_dist = 1` requests a distributed line. `ElmLne.i_model = 1` selects
  frequency-dependent fitting, followed by `ElmLne.FitParams(0, 1)`.
- The 10 μs step is a screening value. A convergence study with 5 μs and 2.5 μs
  is required before using the peak in a formal engineering decision.
- Closing times are deterministic. Pole scatter, statistical breaker data,
  trapped charge and arrester tolerance belong in the Monte Carlo extension.

