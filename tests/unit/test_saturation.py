from pathlib import Path

import pandas as pd

from pfemt.config import load_yaml
from pfemt.saturation import export_saturation_manifest, saturation_scenarios
from pfemt.saturation_plotting import plot_saturation_curves, plot_saturation_summary


def _config() -> dict:
    root = Path(__file__).resolve().parents[2]
    return load_yaml(
        root / "studies/05_transformer_saturation_sensitivity/configs/base.yaml"
    )


def test_saturation_campaign_is_unique_balanced_and_contains_baseline() -> None:
    scenarios = saturation_scenarios(_config())
    assert len(scenarios) == 9
    assert len({scenario.scenario_id for scenario in scenarios}) == 9
    assert scenarios[0].scenario_id == "baseline"
    for scenario in scenarios:
        assert abs(
            scenario.residual_flux_a_pu
            + scenario.residual_flux_b_pu
            + scenario.residual_flux_c_pu
        ) < 1e-12
        assert scenario.saturation_exponent in {9, 13, 15}


def test_saturation_manifest_and_summary_plots(tmp_path: Path) -> None:
    scenarios = saturation_scenarios(_config())
    manifest = export_saturation_manifest(scenarios, tmp_path / "manifest.csv")
    assert len(manifest.read_text(encoding="utf-8").splitlines()) == 10
    assert plot_saturation_curves(scenarios, tmp_path / "curves.png").is_file()
    summary = pd.DataFrame(
        [
            {
                "scenario_id": scenario.scenario_id,
                "label": scenario.label,
                "knee_flux_pu": scenario.knee_flux_pu,
                "flux_proxy_peak_pu": 2.5 + index * 0.01,
                "current_peak_pu": 5.0 + index * 0.1,
            }
            for index, scenario in enumerate(scenarios)
        ]
    )
    assert plot_saturation_summary(summary, tmp_path / "summary.png").is_file()
