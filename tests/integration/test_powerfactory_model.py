"""PowerFactory integration smoke test.

Run explicitly on a workstation with PowerFactory open:
PFEMT_RUN_INTEGRATION=1 pytest -m powerfactory
"""

import os
from pathlib import Path

import pytest

from pfemt.application import connect
from pfemt.builders.cable_energization import apply_cable_bonding_scenario
from pfemt.cable import cable_scenarios
from pfemt.config import load_yaml
from pfemt.diagram import CABLE_GENERATED_LAYER_NAME
from pfemt.io import read_powerfactory_csv
from pfemt.transformer import transformer_energization_metrics, transformer_scenarios
from pfemt.workflows import build, run_transformer_scenario

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
        assert objects["sheath_ground_sending"].bus1 is not None
        assert objects["sheath_ground_receiving"].bus1 is not None
        assert objects["sheath_ground_sending"].on_off == 0
        assert objects["sheath_ground_receiving"].on_off == 0
        assert objects["study_case"].loc_name == config["powerfactory"]["study_case"]
        assert objects["diagram"].loc_name == "EMT Cable Energization 220 kV"
        assert len(objects["diagram"].GetContents("*.IntGrf")) >= 9
        represented = {
            graphic.pDataObj.loc_name
            for graphic in objects["diagram"].GetContents("*.IntGrf")
            if getattr(graphic, "pDataObj", None) is not None
        }
        assert represented == set(config["objects"].values()) - {
            config["objects"]["cable_system"]
        }
        guide_layers = [
            layer
            for layer in objects["diagram"].GetContents("*.IntGrflayer")
            if layer.loc_name == CABLE_GENERATED_LAYER_NAME
        ]
        assert all(layer.GetNumberOfAnnotationElements() == 0 for layer in guide_layers)

        scenarios = cable_scenarios(config)
        single_point = next(
            item for item in scenarios if item.bonding_id == "single_point"
        )
        apply_cable_bonding_scenario(objects, single_point)
        assert objects["sheath_ground_sending"].on_off == 1
        assert objects["sheath_ground_receiving"].on_off == 0
        assert list(objects["cable_system_type"].bond) == [0.0]

        cross_bonded = next(
            item for item in scenarios if item.bonding_id == "cross_bonded"
        )
        apply_cable_bonding_scenario(objects, cross_bonded)
        assert objects["sheath_ground_sending"].on_off == 1
        assert objects["sheath_ground_receiving"].on_off == 1
        assert list(objects["cable_system_type"].bond) == [1.0]

        isolated = next(item for item in scenarios if item.bonding_id == "isolated")
        apply_cable_bonding_scenario(objects, isolated)
        assert objects["sheath_ground_sending"].on_off == 0
        assert objects["sheath_ground_receiving"].on_off == 0
        assert list(objects["cable_system_type"].bond) == [0.0]
    finally:
        objects.clear()
        del app


@pytest.mark.skipif(
    os.environ.get("PFEMT_RUN_INTEGRATION") != "1",
    reason="requires explicit PowerFactory integration opt-in",
)
def test_transformer_inrush_model_executes_nonlinear_emt(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    config = load_yaml(root / "studies/03_transformer_energization/configs/base.yaml")
    config["connection"]["mode"] = os.environ.get(
        "PFEMT_INTEGRATION_MODE",
        "external",
    )
    app = connect(config)
    objects = {}
    try:
        objects = build(config, app)
        first_paths = {
            name: objects[name].GetFullName()
            for name in ("source", "breaker", "transformer", "diagram")
        }
        rebuilt = build(config, app)
        assert {
            name: rebuilt[name].GetFullName()
            for name in ("source", "breaker", "transformer", "diagram")
        } == first_paths
        assert objects["transformer_type"].itrmt == 2
        assert objects["transformer_type"].iHyster == 0
        assert objects["transformer_type"].ksat == 13
        scenario = next(
            item
            for item in transformer_scenarios(config)
            if item.scenario_id == "opposite_a_pow_090deg"
        )
        raw = run_transformer_scenario(
            app,
            config,
            objects,
            scenario,
            tmp_path / "transformer_inrush.csv",
        )
        frame = read_powerfactory_csv(
            raw,
            config["analysis"]["column_map"],
            config["analysis"]["decimal"],
        )
        metrics = transformer_energization_metrics(frame, scenario, config)
        assert len(frame) > 1000
        assert float(metrics["current_peak_pu"]) > 2.0
        assert 0.5 < float(metrics["lv_voltage_peak_pu"]) < 1.5
    finally:
        objects.clear()
        del app
