from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from pfemt.config import load_yaml
from pfemt.lightning import (
    export_lightning_manifest,
    lightning_metrics,
    lightning_scenarios,
    line_wave_quantities,
)
from pfemt.lightning_plotting import (
    plot_distance_time_map,
    plot_lightning_summary,
    plot_lightning_waveforms,
)

ROOT = Path(__file__).resolve().parents[2]


def _config() -> dict:
    return load_yaml(ROOT / "studies/08_lightning_travelling_waves/configs/base.yaml")


def _frame(config: dict) -> pd.DataFrame:
    derived = line_wave_quantities(config)
    time = np.arange(-100e-6, 1.201e-3, 0.1e-6)
    pulse = 30.0 * np.where(
        time >= 0.0,
        np.exp(-time / 50e-6) - np.exp(-time / 1e-6),
        0.0,
    )

    def delayed(delay_us: float) -> np.ndarray:
        shifted = time - delay_us * 1e-6
        return 250.0 * np.where(
            shifted >= 0.0,
            np.exp(-shifted / 80e-6) - np.exp(-shifted / 1.5e-6),
            0.0,
        )

    return pd.DataFrame(
        {
            "time_s": time,
            "i_injected_a_ka": pulse,
            "v_strike_a_kv": delayed(0.0),
            "v_mid_a_kv": delayed(derived["section_travel_time_us"]),
            "v_remote_a_kv": delayed(derived["end_to_end_travel_time_us"]),
        }
    )


def test_lightning_scenarios_and_line_analytical_values(tmp_path: Path) -> None:
    config = _config()
    scenarios = lightning_scenarios(config)
    assert [item.waveform_code for item in scenarios] == [0, 1, 3]
    assert len({item.scenario_id for item in scenarios}) == 3
    values = line_wave_quantities(config)
    assert values["surge_impedance_ohm"] == pytest.approx(285.7, rel=0.02)
    assert 300.0 < values["end_to_end_travel_time_us"] < 400.0
    manifest = export_lightning_manifest(scenarios, tmp_path / "manifest.csv")
    assert len(manifest.read_text(encoding="utf-8").splitlines()) == 4


def test_lightning_metrics_and_figures(tmp_path: Path) -> None:
    config = _config()
    scenario = lightning_scenarios(config)[1]
    frame = _frame(config)
    metrics = lightning_metrics(frame, scenario, config)
    assert metrics["line_current_peak_ka"] > 20.0
    assert metrics["remote_voltage_peak_kv"] > 100.0
    assert abs(metrics["arrival_error_percent"]) < 2.0
    assert metrics["source_charge_c"] > 0.0
    assert plot_lightning_waveforms(
        frame, scenario, metrics, tmp_path / "waveforms.png"
    ).is_file()
    summary = pd.DataFrame([{**scenario.__dict__, **metrics}])
    assert plot_lightning_summary(summary, tmp_path / "summary.png").is_file()
    assert plot_distance_time_map(frame, scenario, tmp_path / "map.png").is_file()
