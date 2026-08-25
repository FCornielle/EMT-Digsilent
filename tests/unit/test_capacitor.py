from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from pfemt.capacitor import (
    capacitor_derived_quantities,
    capacitor_scenarios,
    capacitor_switching_metrics,
    export_capacitor_manifest,
)
from pfemt.capacitor_plotting import (
    plot_capacitor_design_basis,
    plot_capacitor_summary,
    plot_capacitor_waveforms,
)
from pfemt.config import load_yaml


def _config() -> dict:
    root = Path(__file__).resolve().parents[2]
    return load_yaml(root / "studies/04_capacitor_bank_energization/configs/base.yaml")


def _frame(switching_time_s: float, ringing_hz: float = 6000.0) -> pd.DataFrame:
    time = np.arange(-0.005, 0.051, 2e-6)
    relative = np.maximum(time - switching_time_s, 0.0)
    active = time >= switching_time_s
    omega = 2.0 * np.pi * 50.0
    ring = np.where(
        active,
        5.0 * np.exp(-relative / 0.004) * np.sin(2 * np.pi * ringing_hz * relative),
        0.0,
    )
    nominal_peak = 230.0 * np.sqrt(2.0 / 3.0)
    data = {"time_s": time}
    for index, phase in enumerate("abc"):
        shift = index * -2.0 * np.pi / 3.0
        data["i_bank_{}_ka".format(phase)] = np.roll(ring, index * 12)
        data["v_main_{}_kv".format(phase)] = nominal_peak * np.sin(omega * time + shift)
        data["v_bank_{}_kv".format(phase)] = np.where(
            active,
            nominal_peak * np.sin(omega * time + shift) + 8.0 * ring,
            0.0,
        )
    return pd.DataFrame(data)


def test_capacitor_campaign_contains_both_topologies_and_six_angles() -> None:
    scenarios = capacitor_scenarios(_config())
    assert len(scenarios) == 12
    assert len({scenario.scenario_id for scenario in scenarios}) == 12
    assert {scenario.topology_id for scenario in scenarios} == {"isolated", "back_to_back"}


def test_capacitor_analytical_values_are_dimensionally_consistent() -> None:
    values = capacitor_derived_quantities(_config())
    assert values["phase_capacitance_uf"] == pytest.approx(6.017, rel=1e-3)
    assert values["back_to_back_frequency_hz"] > values["isolated_frequency_hz"]
    assert values["bank_rated_current_ka"] == pytest.approx(100.0 / (np.sqrt(3) * 230.0))


def test_capacitor_metrics_and_figures(tmp_path: Path) -> None:
    config = _config()
    scenario = capacitor_scenarios(config)[6]
    frame = _frame(scenario.switching_time_s)
    metrics = capacitor_switching_metrics(frame, scenario, config)
    assert metrics["current_peak_ka"] > 4.0
    assert metrics["peak_didt_ka_per_ms"] > 1.0
    assert metrics["dominant_frequency_hz"] > 100.0
    assert plot_capacitor_waveforms(
        frame, scenario, metrics, tmp_path / "waveforms.png"
    ).is_file()
    summary = pd.DataFrame(
        [
            {
                "topology_label": scenario.topology_label,
                "switching_angle_deg": scenario.switching_angle_deg,
                "current_peak_ka": metrics["current_peak_ka"],
                "peak_didt_ka_per_ms": metrics["peak_didt_ka_per_ms"],
                "bank_voltage_peak_pu": metrics["bank_voltage_peak_pu"],
            }
        ]
    )
    assert plot_capacitor_summary(summary, tmp_path / "summary.png").is_file()
    assert plot_capacitor_design_basis(config, tmp_path / "basis.png").is_file()


def test_capacitor_manifest_has_one_row_per_scenario(tmp_path: Path) -> None:
    output = export_capacitor_manifest(
        capacitor_scenarios(_config()), tmp_path / "manifest.csv"
    )
    assert len(output.read_text(encoding="utf-8").splitlines()) == 13
