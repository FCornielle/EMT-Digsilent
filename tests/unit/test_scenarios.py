from pathlib import Path

import pytest

from pfemt.config import load_yaml
from pfemt.scenarios import (
    monte_carlo_scenarios,
    point_on_wave_scenarios,
    switching_time,
)


def _config():
    root = Path(__file__).resolve().parents[2]
    return load_yaml(root / "studies/01_line_energization/configs/base.yaml")


def test_switching_angle_to_time_at_50_hz() -> None:
    assert switching_time(0.02, 90.0, 50.0) == pytest.approx(0.025)
    assert switching_time(0.02, 360.0, 50.0) == pytest.approx(0.02)


def test_point_on_wave_manifest_is_deterministic() -> None:
    first = point_on_wave_scenarios(_config())
    second = point_on_wave_scenarios(_config())
    assert first == second
    assert len(first) == 12
    assert first[3].scenario_id == "pow_090deg"
    assert first[3].switching_time_s == pytest.approx(0.025)


def test_monte_carlo_seed_reproduces_cases() -> None:
    config = _config()
    config["monte_carlo"]["samples"] = 5
    first = monte_carlo_scenarios(config)
    second = monte_carlo_scenarios(config)
    assert first == second
    assert all(0.95 <= case.source_voltage_pu <= 1.05 for case in first)
    assert all(140.0 <= case.line_length_km <= 160.0 for case in first)

