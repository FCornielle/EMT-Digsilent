import hashlib
from pathlib import Path

import pandas as pd
import pytest
import yaml

from pfemt.cable import cable_derived_quantities, cable_scenarios
from pfemt.config import load_yaml


def test_cable_analytical_reference_matches_versioned_configuration() -> None:
    root = Path(__file__).resolve().parents[2]
    config = load_yaml(root / "studies/02_hv_cable_energization/configs/base.yaml")
    with (root / "studies/02_hv_cable_energization/expected/analytical_design_basis.yaml").open(
        encoding="utf-8"
    ) as stream:
        baseline = yaml.safe_load(stream)
    actual = cable_derived_quantities(config)
    expected = baseline["reference"]
    assert hashlib.sha256(
        (root / "studies/02_hv_cable_energization/configs/base.yaml").read_bytes()
    ).hexdigest().upper() == expected["configuration_sha256"]
    tolerance = baseline["tolerances"]["relative"]
    for key in (
        "phase_voltage_rms_kv",
        "total_capacitance_uf_per_phase",
        "steady_state_charging_current_ka",
        "three_phase_stored_energy_kj",
        "surge_impedance_ohm",
        "one_way_travel_time_ms",
    ):
        assert actual[key] == pytest.approx(expected[key], rel=tolerance)


def test_versioned_cable_scenario_manifest_matches_configuration() -> None:
    root = Path(__file__).resolve().parents[2]
    config = load_yaml(root / "studies/02_hv_cable_energization/configs/base.yaml")
    manifest = pd.read_csv(
        root / "studies/02_hv_cable_energization/parameters/scenario_manifest.csv"
    )
    scenarios = cable_scenarios(config)
    assert manifest["scenario_id"].tolist() == [item.scenario_id for item in scenarios]
    assert manifest["switching_time_s"].tolist() == pytest.approx(
        [item.switching_time_s for item in scenarios]
    )
