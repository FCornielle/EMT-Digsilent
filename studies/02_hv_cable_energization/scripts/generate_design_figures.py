"""Generate Study 02 analytical design-basis figures."""

from __future__ import annotations

import sys
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[3]
SOURCE = REPOSITORY / "src"
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))

from pfemt.cable_plotting import generate_cable_design_figures  # noqa: E402
from pfemt.config import load_yaml, validate_study_config  # noqa: E402

configuration = load_yaml(REPOSITORY / "studies/02_hv_cable_energization/configs/base.yaml")
validate_study_config(configuration)
figures = generate_cable_design_figures(
    configuration,
    REPOSITORY / "studies/02_hv_cable_energization/outputs/design_basis",
)
for name, path in figures.items():
    print("{}: {}".format(name, path))
