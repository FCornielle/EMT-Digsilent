"""Licensed integration smoke test.

Run explicitly on a workstation with PowerFactory open:
PFEMT_RUN_INTEGRATION=1 pytest -m powerfactory
"""

import os
from pathlib import Path

import pytest

from pfemt.application import connect
from pfemt.config import load_yaml
from pfemt.workflows import build

pytestmark = pytest.mark.powerfactory


@pytest.mark.skipif(
    os.environ.get("PFEMT_RUN_INTEGRATION") != "1",
    reason="requires an interactive PowerFactory EMT licence",
)
def test_line_energization_model_builds() -> None:
    root = Path(__file__).resolve().parents[2]
    config = load_yaml(root / "studies/01_line_energization/configs/base.yaml")
    config["connection"]["mode"] = os.environ.get(
        "PFEMT_INTEGRATION_MODE",
        "external",
    )
    app = connect(config)
    objects = build(config, app)
    assert app.LicenceHasModule("stabemt") == 1
    assert objects["line"].AreDistParamsPossible() == 0
    assert objects["line"].i_dist == 1
    assert objects["line"].i_model == 1
    assert objects["study_case"].loc_name == config["powerfactory"]["study_case"]
