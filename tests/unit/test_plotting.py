from pathlib import Path

import numpy as np
import pandas as pd

from pfemt.config import load_yaml
from pfemt.metrics import line_energization_derived_quantities
from pfemt.plotting import (
    plot_overvoltage_envelope,
    plot_parameter_overview,
    plot_sweep_summary,
    plot_timestep_sensitivity,
    plot_travelling_wave_detail,
)


def _assert_figure(path: Path) -> None:
    assert path.is_file()
    assert path.stat().st_size > 10_000


def test_educational_figures_are_generated(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    config = load_yaml(root / "studies/01_line_energization/configs/base.yaml")
    derived = line_energization_derived_quantities(config)
    _assert_figure(plot_parameter_overview(config, derived, tmp_path / "parameters.png"))

    summary = pd.DataFrame(
        {
            "switching_angle_deg": [0.0, 30.0, 60.0],
            "voltage_peak_pu": [2.1, 2.25, 2.0],
            "current_ka_peak": [0.86, 0.75, 0.85],
        }
    )
    _assert_figure(plot_sweep_summary(summary, tmp_path / "sweep.png"))

    aligned = pd.DataFrame(
        {
            "switching_angle_deg": np.repeat([0.0, 30.0], 100),
            "relative_time_ms": np.tile(np.linspace(0.0, 10.0, 100), 2),
            "voltage_envelope_pu": 1.0 + np.abs(np.sin(np.linspace(0.0, 8.0, 200))),
        }
    )
    _assert_figure(plot_overvoltage_envelope(aligned, tmp_path / "envelope.png"))

    time_s = np.linspace(0.01975, 0.025, 300)
    frame = pd.DataFrame(
        {
            "time_s": time_s,
            "v_recv_a_kv": 300.0 * np.sin(2.0 * np.pi * 1000.0 * time_s),
            "v_recv_b_kv": 260.0 * np.sin(2.0 * np.pi * 1000.0 * time_s - 2.1),
            "v_recv_c_kv": 280.0 * np.sin(2.0 * np.pi * 1000.0 * time_s + 2.1),
        }
    )
    metrics = {"switching_time_s": 0.020, "nominal_phase_peak_kv": 187.79}
    _assert_figure(
        plot_travelling_wave_detail(
            frame, metrics, derived["one_way_travel_time_ms"], tmp_path / "travelling.png"
        )
    )

    sensitivity = pd.DataFrame(
        {
            "time_step_us": [5.0, 10.0, 20.0],
            "voltage_peak_pu": [2.257, 2.256, 2.251],
            "current_ka_peak": [0.866, 0.865, 0.861],
        }
    )
    _assert_figure(plot_timestep_sensitivity(sensitivity, tmp_path / "sensitivity.png"))
