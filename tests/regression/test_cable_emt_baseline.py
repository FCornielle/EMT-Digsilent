import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest
import yaml


def test_cable_emt_baseline_is_complete_and_traceable() -> None:
    root = Path(__file__).resolve().parents[2]
    expected = root / "studies/02_hv_cable_energization/expected"
    metadata = yaml.safe_load(
        (expected / "powerfactory_2024_emt_baseline.yaml").read_text(encoding="utf-8")
    )["baseline"]
    config = root / "studies/02_hv_cable_energization/configs/base.yaml"
    assert hashlib.sha256(config.read_bytes()).hexdigest().upper() == metadata[
        "configuration_sha256"
    ]

    summary = pd.read_csv(expected / metadata["sweep_file"])
    assert len(summary) == metadata["scenario_count"] == 24
    assert summary["scenario_id"].is_unique
    assert set(summary["bonding_id"]) == {
        "isolated",
        "single_point",
        "both_ends",
        "cross_bonded",
    }
    assert set(summary.groupby("bonding_id").size()) == {6}
    assert summary["switching_angle_deg"].nunique() == 6

    worst = json.loads(
        (expected / metadata["worst_case_file"]).read_text(encoding="utf-8")
    )
    ranked = summary.sort_values("core_voltage_peak_pu", ascending=False).iloc[0]
    assert worst["scenario_id"] == ranked["scenario_id"]
    assert worst["core_voltage_peak_pu"] == pytest.approx(
        ranked["core_voltage_peak_pu"]
    )
