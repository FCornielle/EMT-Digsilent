from pathlib import Path

import numpy as np
import pytest

from pfemt.cable import (
    cable_bonding_cases,
    cable_derived_quantities,
    cable_length_sensitivity,
)
from pfemt.config import load_yaml


def _config() -> dict:
    root = Path(__file__).resolve().parents[2]
    return load_yaml(root / "studies/02_hv_cable_energization/configs/base.yaml")


def test_cable_design_basis_has_expected_physical_scale() -> None:
    result = cable_derived_quantities(_config())
    assert result["phase_voltage_rms_kv"] == pytest.approx(220.0 / np.sqrt(3.0))
    assert result["total_capacitance_uf_per_phase"] == pytest.approx(9.2)
    assert result["steady_state_charging_current_ka"] == pytest.approx(0.367113, rel=1e-5)
    assert result["three_phase_stored_energy_kj"] == pytest.approx(445.28)
    assert result["one_way_travel_time_ms"] == pytest.approx(0.358887, rel=1e-5)
    assert result["samples_per_travel_time"] > 100.0


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
