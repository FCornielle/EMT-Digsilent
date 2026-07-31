"""PowerFactory integration smoke test.

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
    reason="requires explicit PowerFactory integration opt-in",
)
def test_line_energization_model_builds() -> None:
    root = Path(__file__).resolve().parents[2]
    config = load_yaml(root / "studies/01_line_energization/configs/base.yaml")
    config["connection"]["mode"] = os.environ.get(
        "PFEMT_INTEGRATION_MODE",
        "external",
    )
    app = connect(config)
    objects = {}
    try:
        objects = build(config, app)
        assert objects["line"].AreDistParamsPossible() == 0
        assert objects["line"].i_dist == 1
        assert objects["line"].i_model == 1
        assert objects["study_case"].loc_name == config["powerfactory"]["study_case"]
        assert objects["diagram"].loc_name == "EMT Line Energization 230 kV"
        assert len(objects["diagram"].GetContents("*.IntGrf")) == 6
    finally:
        objects.clear()
        del app


@pytest.mark.skipif(
    os.environ.get("PFEMT_RUN_INTEGRATION") != "1",
    reason="requires explicit PowerFactory integration opt-in",
)
def test_explicit_cable_energization_model_builds() -> None:
    root = Path(__file__).resolve().parents[2]
    config = load_yaml(root / "studies/02_hv_cable_energization/configs/base.yaml")
    config["connection"]["mode"] = os.environ.get(
        "PFEMT_INTEGRATION_MODE",
        "external",
    )
    app = connect(config)
    objects = {}
    try:
        objects = build(config, app)
        assert objects["cable_system"].i_dist == 1
        assert objects["cable_system"].i_model == 1
        assert objects["cable_system"].fd_model == 1
        assert objects["cable_system"].typ_id == objects["cable_system_type"]
        assert list(objects["cable_system"].plines) == [
            objects["core_line"],
            objects["sheath_line"],
        ]
        assert objects["study_case"].loc_name == config["powerfactory"]["study_case"]
        assert objects["diagram"].loc_name == "EMT Cable Energization 220 kV"
        assert len(objects["diagram"].GetContents("*.IntGrf")) >= 9
    finally:
        objects.clear()
        del app
