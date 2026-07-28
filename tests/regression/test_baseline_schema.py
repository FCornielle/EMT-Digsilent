from pathlib import Path

import pytest
import yaml


def test_line_energization_baseline_is_engineering_plausible() -> None:
    root = Path(__file__).resolve().parents[2]
    path = (
        root
        / "studies/01_line_energization/expected/powerfactory_2024_sp2.yaml"
    )
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    baseline = data["baseline"]
    results = data["results"]
    assert baseline["scenario_count"] == 12
    assert baseline["emt_licence_available"] is True
    assert 1.0 < results["worst_voltage_peak_pu"] < 3.0
    assert results["worst_voltage_peak_kv_phase_ground"] > 230.0
    assert results["maximum_closing_current_ka_peak"] > 0.0
    assert results["worst_voltage_angles_deg"] == [30, 90, 150, 210, 270, 330]
    assert results["worst_voltage_peak_pu"] == pytest.approx(2.257009877)

