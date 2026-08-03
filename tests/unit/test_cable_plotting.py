from pathlib import Path

import numpy as np
import pandas as pd

from pfemt.cable import cable_energization_metrics, cable_scenarios
from pfemt.cable_plotting import (
    generate_cable_design_figures,
    plot_cable_emt_waveforms,
    plot_cable_sweep_summary,
)
from pfemt.config import load_yaml


def test_cable_design_figures_are_generated(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    config = load_yaml(root / "studies/02_hv_cable_energization/configs/base.yaml")
    figures = generate_cable_design_figures(config, tmp_path)
    assert set(figures) == {
        "geometry",
        "parameters",
        "length_sensitivity",
        "bonding_matrix",
        "scenario_coverage",
    }
    for figure in figures.values():
        assert figure.is_file()
        assert figure.stat().st_size > 20_000


def test_cable_emt_result_figures_are_generated(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    config = load_yaml(root / "studies/02_hv_cable_energization/configs/base.yaml")
    scenario = cable_scenarios(config)[0]
    time = np.linspace(0.018, 0.040, 220)
    frame = pd.DataFrame({"time_s": time})
    for prefix, scale in (
        ("v_core_recv", 250.0),
        ("v_sheath_send", 25.0),
        ("v_sheath_recv", 30.0),
        ("i_core_send", 2.0),
        ("i_sheath_send", 0.6),
        ("i_ground_send", 0.5),
        ("i_ground_recv", 0.4),
    ):
        for index, phase in enumerate(("a", "b", "c")):
            unit = "kv" if prefix.startswith("v_") else "ka"
            frame["{}_{}_{}".format(prefix, phase, unit)] = scale * np.sin(
                2.0 * np.pi * 50.0 * time - index * 2.0 * np.pi / 3.0
            )
    metrics = cable_energization_metrics(
        frame,
        float(config["network"]["nominal_voltage_kv"]),
        scenario.switching_time_s,
    )
    waveform = plot_cable_emt_waveforms(
        frame, scenario, metrics, tmp_path / "waveforms.png"
    )
    assert waveform.stat().st_size > 20_000

    summary = pd.DataFrame(
        [
            {
                "bonding_id": scenario.bonding_id,
                "bonding_label": scenario.bonding_label,
                "switching_angle_deg": scenario.switching_angle_deg,
                **metrics,
            }
        ]
    )
    campaign = plot_cable_sweep_summary(summary, tmp_path / "campaign.png")
    assert campaign.stat().st_size > 20_000
