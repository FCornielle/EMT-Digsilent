from pathlib import Path

import pandas as pd
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
    assert 1.0 < results["worst_voltage_peak_pu"] < 3.0
    assert results["worst_voltage_peak_kv_phase_ground"] > 230.0
    assert results["maximum_closing_current_ka_peak"] > 0.0
    assert results["worst_voltage_angles_deg"] == [30, 90, 150, 210, 270, 330]
    assert results["worst_voltage_peak_pu"] == pytest.approx(2.257009877)


def test_timestep_reference_documents_peak_convergence() -> None:
    root = Path(__file__).resolve().parents[2]
    path = (
        root
        / "studies/01_line_energization/expected/timestep_sensitivity_powerfactory_2024_sp2.csv"
    )
    frame = pd.read_csv(path).sort_values("time_step_us")
    finest = frame.iloc[0]
    next_finest = frame.iloc[1]
    voltage_error = abs(next_finest["voltage_peak_pu"] - finest["voltage_peak_pu"]) / finest[
        "voltage_peak_pu"
    ]
    current_error = abs(next_finest["current_ka_peak"] - finest["current_ka_peak"]) / finest[
        "current_ka_peak"
    ]
    assert finest["time_step_us"] == pytest.approx(1.25)
    assert voltage_error < 0.001
    assert current_error < 0.001
