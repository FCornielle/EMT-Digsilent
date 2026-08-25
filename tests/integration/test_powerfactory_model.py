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
from pfemt.capacitor import capacitor_scenarios, capacitor_switching_metrics
from pfemt.config import load_yaml
from pfemt.diagram import CABLE_GENERATED_LAYER_NAME
from pfemt.faults import fault_metrics, fault_scenarios, trv_metrics
from pfemt.io import read_powerfactory_csv
from pfemt.lightning import lightning_metrics, lightning_scenarios
from pfemt.transformer import transformer_energization_metrics, transformer_scenarios
from pfemt.workflows import (
    build,
    run_capacitor_scenario,
    run_fault_scenario,
    run_lightning_scenario,
    run_transformer_scenario,
)

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


@pytest.mark.skipif(
    os.environ.get("PFEMT_RUN_INTEGRATION") != "1",
    reason="requires explicit PowerFactory integration opt-in",
)
def test_capacitor_switching_model_executes_back_to_back_emt(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    config = load_yaml(root / "studies/04_capacitor_bank_energization/configs/base.yaml")
    config["connection"]["mode"] = os.environ.get("PFEMT_INTEGRATION_MODE", "external")
    app = connect(config)
    objects = {}
    try:
        objects = build(config, app)
        first_bank_path = objects["bank_a"].GetFullName()
        assert build(config, app)["bank_a"].GetFullName() == first_bank_path
        assert objects["bank_a"].shtype == 2
        assert objects["bank_a"].cgnd == 0
        assert objects["bank_a"].qcapn == pytest.approx(100.0)
        assert objects["reactor_a"].x_pu > 0.0
        scenario = next(
            item
            for item in capacitor_scenarios(config)
            if item.scenario_id == "back_to_back_pow_090deg"
        )
        raw = run_capacitor_scenario(
            app,
            config,
            objects,
            scenario,
            tmp_path / "capacitor_switching.csv",
        )
        frame = read_powerfactory_csv(
            raw,
            config["analysis"]["column_map"],
            config["analysis"]["decimal"],
        )
        metrics = capacitor_switching_metrics(frame, scenario, config)
        assert len(frame) > 1000
        assert float(metrics["current_peak_ka"]) > 5.0
        assert 5000.0 < float(metrics["dominant_frequency_hz"]) < 8000.0
    finally:
        objects.clear()
        del app


@pytest.mark.skipif(
    os.environ.get("PFEMT_RUN_INTEGRATION") != "1",
    reason="requires explicit PowerFactory integration opt-in",
)
def test_breaker_trv_model_executes_and_measures_contact_voltage(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    config = load_yaml(root / "studies/06_circuit_breaker_trv/configs/base.yaml")
    config["connection"]["mode"] = os.environ.get("PFEMT_INTEGRATION_MODE", "external")
    app = connect(config)
    objects = {}
    try:
        objects = build(config, app)
        breaker_path = objects["breaker"].GetFullName()
        assert build(config, app)["breaker"].GetFullName() == breaker_path
        scenario = fault_scenarios(config)[1]
        raw = run_fault_scenario(app, config, objects, scenario, tmp_path / "trv.csv")
        frame = read_powerfactory_csv(
            raw, config["analysis"]["column_map"], config["analysis"]["decimal"]
        )
        metrics = trv_metrics(frame, scenario, config)
        assert len(frame) > 1000
        assert float(metrics["trv_peak_kv"]) > 200.0
        assert float(metrics["average_rrrv_kv_per_us"]) > 0.0
    finally:
        objects.clear()
        del app


@pytest.mark.skipif(
    os.environ.get("PFEMT_RUN_INTEGRATION") != "1",
    reason="requires explicit PowerFactory integration opt-in",
)
def test_fault_network_executes_slg_and_three_phase_signatures(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    config = load_yaml(root / "studies/07_faults_variable_clearing/configs/base.yaml")
    config["connection"]["mode"] = os.environ.get("PFEMT_INTEGRATION_MODE", "external")
    app = connect(config)
    objects = {}
    try:
        objects = build(config, app)
        breaker_path = objects["breaker"].GetFullName()
        assert build(config, app)["breaker"].GetFullName() == breaker_path
        scenarios = fault_scenarios(config)
        slg = scenarios[0]
        slg_raw = run_fault_scenario(app, config, objects, slg, tmp_path / "slg.csv")
        slg_frame = read_powerfactory_csv(
            slg_raw, config["analysis"]["column_map"], config["analysis"]["decimal"]
        )
        slg_metrics = fault_metrics(slg_frame, slg, config)
        active = slg_frame.loc[
            (slg_frame["time_s"] >= slg.fault_time_s)
            & (slg_frame["time_s"] <= slg.fault_time_s + 0.02)
        ]
        assert active["i_a_ka"].abs().max() > 1.0
        assert active[["i_b_ka", "i_c_ka"]].abs().to_numpy().max() < 0.01
        assert float(slg_metrics["recovery_voltage_peak_pu"]) > 0.9

        three_phase = scenarios[6]
        three_raw = run_fault_scenario(
            app, config, objects, three_phase, tmp_path / "three_phase.csv"
        )
        three_frame = read_powerfactory_csv(
            three_raw, config["analysis"]["column_map"], config["analysis"]["decimal"]
        )
        active_three = three_frame.loc[
            (three_frame["time_s"] >= three_phase.fault_time_s)
            & (three_frame["time_s"] <= three_phase.fault_time_s + 0.02)
        ]
        assert active_three[["i_a_ka", "i_b_ka", "i_c_ka"]].abs().max().min() > 1.0
    finally:
        objects.clear()
        del app


@pytest.mark.skipif(
    os.environ.get("PFEMT_RUN_INTEGRATION") != "1",
    reason="requires explicit PowerFactory integration opt-in",
)
def test_lightning_impulse_executes_distributed_travelling_wave(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    config = load_yaml(root / "studies/08_lightning_travelling_waves/configs/base.yaml")
    config["connection"]["mode"] = os.environ.get("PFEMT_INTEGRATION_MODE", "external")
    app = connect(config)
    objects = {}
    try:
        objects = build(config, app)
        first_paths = {
            name: objects[name].GetFullName()
            for name in ("impulse", "line_section_1", "line_section_2", "diagram")
        }
        rebuilt = build(config, app)
        assert {
            name: rebuilt[name].GetFullName()
            for name in ("impulse", "line_section_1", "line_section_2", "diagram")
        } == first_paths
        assert objects["load_flow"].iopt_net == 1
        assert objects["initial_conditions"].iopt_net == "rst"
        scenario = lightning_scenarios(config)[1]
        raw = run_lightning_scenario(
            app, config, objects, scenario, tmp_path / "lightning.csv"
        )
        frame = read_powerfactory_csv(
            raw, config["analysis"]["column_map"], config["analysis"]["decimal"]
        )
        metrics = lightning_metrics(frame, scenario, config)
        assert len(frame) > 10000
        assert float(metrics["line_current_peak_ka"]) > 20.0
        assert float(metrics["remote_voltage_peak_kv"]) > 1000.0
        assert abs(float(metrics["arrival_error_percent"])) < 2.0
    finally:
        objects.clear()
        del app
