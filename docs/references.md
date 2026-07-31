# Technical references

References were reviewed on 2026-07-31. Prefer the documentation shipped with
the installed PowerFactory version when a web page and local manual differ.

## Local PowerFactory 2024 SP2 manuals

- `C:\Program Files\DIgSILENT\PowerFactory 2024\Help\UserManual_en.pdf`
  - Chapter 28: RMS/EMT simulations.
  - Section 28.10: single/multiple-domain EMT–EMT and RMS–EMT co-simulation.
  - DSL `event()` reference: `EvtSwitch.i_switch=1` closes and the default
    action opens.
- `C:\Program Files\DIgSILENT\PowerFactory 2024\Help\PythonReference_en.pdf`
  - `Application.CreateProject()`.
  - `Application.GetProjectFolder()`.
  - `DataObject.CreateObject()`.
  - `ElmLne.AreDistParamsPossible()`.
  - `ElmLne.FitParams()`; `i_model=0` constant and `i_model=1`
    frequency-dependent parameters.
  - `SetDesktop.Show()` and `WriteWMF()`.
  - `ComWr` graphic export to PNG/SVG/PDF and other formats.

## Official DIgSILENT knowledge base

- [Configure and run a dynamic simulation via scripting](https://faq.digsilent.de/en/faq-reader-powerfactory/how-do-i-configure-and-run-a-dynamic-simulation-via-scripting.html)
- [General guidance for PowerFactory EMT simulations](https://www.digsilent.de/en/faq-reader-powerfactory/can-you-provide-any-general-guidance-on-how-to-perform-an-emt-simulation.html)
- [Configure overhead-line and cable models for EMT](https://www.digsilent.de/en/faq-reader-powerfactory/how-to-configure-overhead-line-and-cable-models-for-emt-simulations.html)
- [Validate line models by comparing frequency sweep and EMT/FFT](https://www.digsilent.de/index.php/en/faq-reader-powerfactory/how-can-you-validate-cable-and-overhead-line-models-for-emt-simulations.html)
- [Breaker/switch closing options in RMS and EMT](https://www.digsilent.de/en/faq-reader-powerfactory/what-are-the-options-available-for-breaker-switch-close-actions-in-rms-and-emt-simulation.html)
- [Export selected result variables with Python and ComRes](https://www.digsilent.de/en/faq-reader-powerfactory/how-do-i-define-only-single-variables-to-be-exported-from-a-resultfile-using-python.html)
- [Read ElmRes data efficiently through ComRes and pandas](https://faq.digsilent.de/en/faq-reader-powerfactory/how-can-i-read-data-from-a-result-file-elmres-via-script.html)
- [Generate/display new network elements with the Diagram Layout Tool](https://www.digsilent.de/index.php/en/faq-reader-powerfactory/how-to-create-a-network-element-with-a-python-script.html)
- [Export plots and single-line diagrams from the Graphics Board](https://www.digsilent.de/index.php/en/faq-reader-powerfactory/how-can-i-automatically-export-all-plots-available-in-a-project.html)
- [Export the active graphic with Python and ComWr](https://www.digsilent.de/en/faq-reader-powerfactory/how-do-i-export-a-graphic-using-python.html)
- [PowerFactory network diagrams and graphic features](https://www.digsilent.de/en/network-diagrams-and-graphic-features.html)
- [Improve EMT simulation performance](https://www.digsilent.de/en/faq-reader-powerfactory/how-can-you-speed-up-improve-the-performance-of-emt-simulations.html)
- [Internal-solver EMT–EMT and RMS–EMT co-simulation example](https://www.digsilent.de/en/faq-reader-powerfactory/do-you-have-an-example-for-the-internal-solver-co-simulation-emt-emt-or-rms-emt.html)
- [Line energization with a distributed model](https://www.digsilent.de/index.php/en/faq-reader-powerfactory/how-do-you-model-the-line-energisation-of-a-bi-phase-system-using-a-distributed-parameter-line-model.html)

## Interpretation

DIgSILENT recommends geometric line/cable models for detailed EMT work and
requires distributed line parameters to be calculated after configuration.
Accordingly, the supplied API builder always runs feasibility and fitting
checks. The sequence-parameter `TypLne` in Study 01 is a transparent starter,
not a substitute for project geometry in a design deliverable.

The official EMT guidance also recommends choosing the line representation and
time step with respect to the transient frequency range. Study 01 therefore
documents its distributed model, calculates a first-order travel time, compares
the calculated extrema with a regression reference, and repeats the worst case
with several time steps. For a project model, the next verification layer is a
frequency-sweep versus EMT/FFT comparison.
