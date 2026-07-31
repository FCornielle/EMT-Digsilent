"""Generate the versioned Study 02 bonding-by-angle scenario manifest."""

from __future__ import annotations

import sys
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[3]
SOURCE = REPOSITORY / "src"
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))

from pfemt.cable import (  # noqa: E402
    cable_scenarios,
    export_cable_scenario_manifest,
)
from pfemt.config import load_yaml, validate_study_config  # noqa: E402

STUDY = REPOSITORY / "studies/02_hv_cable_energization"
configuration = load_yaml(STUDY / "configs/base.yaml")
validate_study_config(configuration)
manifest = export_cable_scenario_manifest(
    cable_scenarios(configuration),
    STUDY / "parameters/scenario_manifest.csv",
)
print(manifest)
