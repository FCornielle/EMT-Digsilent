from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from pfemt.config import load_yaml
from pfemt.transformer import (
    export_transformer_manifest,
    reconstruct_flux_proxy,
    transformer_derived_quantities,
    transformer_energization_metrics,
    transformer_scenarios,
)
from pfemt.transformer_plotting import (
    plot_transformer_design_basis,
    plot_transformer_sweep_summary,
    plot_transformer_waveforms,
)


def _config() -> dict:
    root = Path(__file__).resolve().parents[2]
    return load_yaml(root / "studies/03_transformer_energization/configs/base.yaml")


def _frame(switching_time_s: float) -> pd.DataFrame:
    time = np.arange(-0.02, 0.141, 0.0001)
    relative = np.maximum(time - switching_time_s, 0.0)
    active = time >= switching_time_s
    omega = 2.0 * np.pi * 50.0
    decay = np.exp(-relative / 0.08)
    current_a = np.where(active, 1.5 * decay * np.sin(omega * relative) + 0.8 * decay, 0.0)
    current_b = np.where(active, 1.0 * decay * np.sin(omega * relative - 2.094), 0.0)
    current_c = np.where(active, 0.9 * decay * np.sin(omega * relative + 2.094), 0.0)
    hv_peak = 230.0 * np.sqrt(2.0 / 3.0)
    lv_peak = 34.5 * np.sqrt(2.0 / 3.0)
    return pd.DataFrame(
        {
            "time_s": time,
            "i_hv_a_ka": current_a,
            "i_hv_b_ka": current_b,
            "i_hv_c_ka": current_c,
            "v_hv_a_kv": np.where(active, hv_peak * np.sin(omega * relative), 0.0),
            "v_hv_b_kv": np.where(active, hv_peak * np.sin(omega * relative - 2.094), 0.0),
            "v_hv_c_kv": np.where(active, hv_peak * np.sin(omega * relative + 2.094), 0.0),
            "v_lv_a_kv": np.where(active, lv_peak * np.sin(omega * relative), 0.0),
            "v_lv_b_kv": np.where(active, lv_peak * np.sin(omega * relative - 2.094), 0.0),
            "v_lv_c_kv": np.where(active, lv_peak * np.sin(omega * relative + 2.094), 0.0),
        }
    )


def test_transformer_campaign_is_complete_and_residual_flux_is_balanced() -> None:
    scenarios = transformer_scenarios(_config())
    assert len(scenarios) == 18
    assert len({scenario.scenario_id for scenario in scenarios}) == 18
    assert {scenario.residual_id for scenario in scenarios} == {
        "demagnetized",
        "adverse_a",
        "opposite_a",
    }
    for scenario in scenarios:
        assert (
            scenario.residual_flux_a_pu
            + scenario.residual_flux_b_pu
            + scenario.residual_flux_c_pu
        ) == pytest.approx(0.0)


def test_transformer_rated_bases_are_dimensionally_consistent() -> None:
    derived = transformer_derived_quantities(_config())
    assert derived["rated_hv_current_ka"] == pytest.approx(100.0 / (np.sqrt(3) * 230.0))
    assert derived["rated_lv_current_ka"] == pytest.approx(100.0 / (np.sqrt(3) * 34.5))
    assert derived["hv_base_impedance_ohm"] == pytest.approx(529.0)
    assert derived["leakage_impedance_ohm"] == pytest.approx(66.125)


def test_flux_proxy_preserves_declared_initial_residual_flux() -> None:
    scenario = transformer_scenarios(_config())[6]
    frame = _frame(scenario.switching_time_s)
    flux = reconstruct_flux_proxy(
        frame,
        scenario.switching_time_s,
        50.0,
        230.0,
        (
            scenario.residual_flux_a_pu,
            scenario.residual_flux_b_pu,
            scenario.residual_flux_c_pu,
        ),
    )
    sample = flux.loc[flux["time_s"] >= scenario.switching_time_s].iloc[0]
    assert sample["flux_a_pu"] == pytest.approx(scenario.residual_flux_a_pu)
    assert sample["flux_b_pu"] == pytest.approx(scenario.residual_flux_b_pu)
    assert sample["flux_c_pu"] == pytest.approx(scenario.residual_flux_c_pu)


def test_transformer_metrics_and_figures_are_generated(tmp_path: Path) -> None:
    config = _config()
    scenario = transformer_scenarios(config)[6]
    frame = _frame(scenario.switching_time_s)
    metrics = transformer_energization_metrics(frame, scenario, config)
    assert metrics["current_peak_ka"] > 1.0
    assert metrics["current_peak_pu"] > 1.0
    assert metrics["flux_proxy_peak_pu"] >= abs(scenario.residual_flux_a_pu)
    assert metrics["second_harmonic_ratio"] >= 0.0
    assert plot_transformer_waveforms(
        frame,
        scenario,
        metrics,
        config,
        tmp_path / "waveforms.png",
    ).is_file()
    summary = pd.DataFrame(
        [
            {
                "residual_id": scenario.residual_id,
                "residual_label": scenario.residual_label,
                "switching_angle_deg": scenario.switching_angle_deg,
                "current_peak_pu": metrics["current_peak_pu"],
                "flux_proxy_peak_pu": metrics["flux_proxy_peak_pu"],
                "second_harmonic_ratio": metrics["second_harmonic_ratio"],
            }
        ]
    )
    assert plot_transformer_sweep_summary(summary, tmp_path / "summary.png").is_file()
    assert plot_transformer_design_basis(config, tmp_path / "basis.png").is_file()


def test_transformer_manifest_has_one_row_per_scenario(tmp_path: Path) -> None:
    scenarios = transformer_scenarios(_config())
    output = export_transformer_manifest(scenarios, tmp_path / "manifest.csv")
    assert len(output.read_text(encoding="utf-8").splitlines()) == 19
