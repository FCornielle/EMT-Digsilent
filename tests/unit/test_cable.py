from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from pfemt.cable import (
    cable_bonding_cases,
    cable_derived_quantities,
    cable_energization_metrics,
    cable_geometry,
    cable_length_sensitivity,
    cable_scenarios,
    export_cable_scenario_manifest,
    inactive_ground_result_channels,
)
from pfemt.config import load_yaml


def _config() -> dict:
    root = Path(__file__).resolve().parents[2]
    return load_yaml(root / "studies/02_hv_cable_energization/configs/base.yaml")


def test_cable_design_basis_has_expected_physical_scale() -> None:
    result = cable_derived_quantities(_config())
    assert result["phase_voltage_rms_kv"] == pytest.approx(220.0 / np.sqrt(3.0))
    assert result["total_capacitance_uf_per_phase"] == pytest.approx(8.0)
    assert result["steady_state_charging_current_ka"] == pytest.approx(0.319229, rel=1e-5)
    assert result["three_phase_stored_energy_kj"] == pytest.approx(387.2)
    assert result["one_way_travel_time_ms"] == pytest.approx(0.652380, rel=1e-5)
    assert result["samples_per_travel_time"] > 100.0


def test_catalogue_geometry_is_converted_to_consistent_powerfactory_layers() -> None:
    geometry = cable_geometry(_config())
    assert geometry.conductor_diameter_mm == pytest.approx(41.2)
    assert geometry.conductor_fill_factor_pct == pytest.approx(90.0113, rel=1e-5)
    assert geometry.nominal_main_insulation_thickness_mm == pytest.approx(23.0)
    assert geometry.effective_main_insulation_thickness_mm == pytest.approx(24.7)
    assert geometry.main_insulation_relative_permittivity == pytest.approx(2.83293, rel=1e-5)
    assert geometry.sheath_area_mm2 == pytest.approx(912.538, rel=1e-5)
    assert geometry.oversheath_thickness_mm == pytest.approx(14.2)


def test_cable_length_sensitivity_is_linear_for_capacitive_quantities() -> None:
    frame = cable_length_sensitivity(_config(), np.asarray([20.0, 40.0]))
    assert frame.iloc[1]["charging_current_ka"] == pytest.approx(
        2.0 * frame.iloc[0]["charging_current_ka"]
    )
    assert frame.iloc[1]["stored_energy_kj"] == pytest.approx(
        2.0 * frame.iloc[0]["stored_energy_kj"]
    )


def test_bonding_cases_preserve_the_declared_topologies() -> None:
    cases = cable_bonding_cases(_config())
    assert [case["id"] for case in cases] == [
        "isolated",
        "single_point",
        "both_ends",
        "cross_bonded",
    ]
    assert cases[0]["grounded_sending"] is False
    assert cases[-1]["cross_bonded"] is True


def test_cable_scenario_campaign_is_complete_and_deterministic() -> None:
    first = cable_scenarios(_config())
    second = cable_scenarios(_config())
    assert first == second
    assert len(first) == 24
    assert len({scenario.scenario_id for scenario in first}) == 24
    assert first[0].scenario_id == "isolated_pow_000deg"
    assert first[5].switching_time_s == pytest.approx(0.028333333333333335)
    assert first[6].bonding_id == "single_point"
    assert first[-1].cross_bonded is True


def test_open_ground_switch_channels_are_declared_as_physical_zeros() -> None:
    isolated, single_point, both_ends = (
        next(
            scenario
            for scenario in cable_scenarios(_config())
            if scenario.bonding_id == bonding_id
        )
        for bonding_id in ("isolated", "single_point", "both_ends")
    )
    assert len(inactive_ground_result_channels(isolated)) == 6
    assert inactive_ground_result_channels(single_point) == [
        "i_ground_recv_a_ka",
        "i_ground_recv_b_ka",
        "i_ground_recv_c_ka",
    ]
    assert inactive_ground_result_channels(both_ends) == []


def test_cable_scenario_manifest_has_one_row_per_case(tmp_path: Path) -> None:
    destination = export_cable_scenario_manifest(
        cable_scenarios(_config()), tmp_path / "scenario_manifest.csv"
    )
    rows = destination.read_text(encoding="utf-8").splitlines()
    assert len(rows) == 25
    assert rows[0].startswith("scenario_id,bonding_id,bonding_label")


def test_cable_scenario_ids_preserve_fractional_angles() -> None:
    config = _config()
    config["sweep"]["angles_deg"] = [2.4, 2.49]
    identifiers = [scenario.scenario_id for scenario in cable_scenarios(config)]
    assert identifiers[:2] == ["isolated_pow_002p4deg", "isolated_pow_002p49deg"]
    assert len(set(identifiers)) == 8


def test_cable_emt_metrics_find_peaks_after_switching() -> None:
    frame = pd.DataFrame(
        {
            "time_s": [0.0, 0.02, 0.021],
            "v_core_recv_a_kv": [999.0, 100.0, -300.0],
            "v_core_recv_b_kv": [0.0, 120.0, 150.0],
            "v_core_recv_c_kv": [0.0, -140.0, 130.0],
            "i_core_send_a_ka": [0.0, 1.0, -2.0],
            "i_core_send_b_ka": [0.0, 0.5, 1.5],
            "i_core_send_c_ka": [0.0, 0.4, 1.0],
            "v_sheath_send_a_kv": [0.0, 10.0, 20.0],
            "v_sheath_send_b_kv": [0.0, 11.0, 21.0],
            "v_sheath_send_c_kv": [0.0, 12.0, 22.0],
            "v_sheath_recv_a_kv": [0.0, 13.0, 23.0],
            "v_sheath_recv_b_kv": [0.0, 14.0, 24.0],
            "v_sheath_recv_c_kv": [0.0, 15.0, 25.0],
            "i_sheath_send_a_ka": [0.0, 0.1, 0.2],
            "i_sheath_send_b_ka": [0.0, 0.2, 0.3],
            "i_sheath_send_c_ka": [0.0, 0.3, 0.4],
            "i_ground_send_a_ka": [0.0, 0.1, 0.5],
            "i_ground_send_b_ka": [0.0, 0.2, 0.4],
            "i_ground_send_c_ka": [0.0, 0.2, 0.3],
            "i_ground_recv_a_ka": [0.0, 0.1, 0.2],
            "i_ground_recv_b_ka": [0.0, 0.1, 0.2],
            "i_ground_recv_c_ka": [0.0, 0.1, 0.2],
        }
    )
    metrics = cable_energization_metrics(frame, 220.0, 0.02)
    assert metrics["core_voltage_peak_kv"] == pytest.approx(300.0)
    assert metrics["core_voltage_peak_channel"] == "v_core_recv_a_kv"
    assert metrics["core_voltage_peak_time_ms"] == pytest.approx(1.0)
    assert metrics["core_voltage_peak_pu"] == pytest.approx(
        300.0 / (220.0 / np.sqrt(3.0) * np.sqrt(2.0))
    )
    assert metrics["ground_current_peak_ka"] == pytest.approx(0.5)
