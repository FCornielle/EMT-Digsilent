from pathlib import Path

import numpy as np
import pandas as pd

from pfemt.config import load_yaml
from pfemt.fault_plotting import plot_fault_summary, plot_fault_waveforms, plot_trv_waveforms
from pfemt.faults import export_fault_manifest, fault_metrics, fault_scenarios, trv_metrics

ROOT = Path(__file__).resolve().parents[2]


def _config(study: str) -> dict:
    return load_yaml(ROOT / "studies" / study / "configs" / "base.yaml")


def _frame(scenario, trv: bool) -> pd.DataFrame:
    time = np.arange(-0.005, 0.181, 1e-5)
    active = (time >= scenario.fault_time_s) & (time <= scenario.clearing_time_s)
    omega = 2.0 * np.pi * 50.0
    data = {"time_s": time}
    for index, phase in enumerate("abc"):
        shift = index * -2.0 * np.pi / 3.0
        data["i_{}_ka".format(phase)] = np.where(
            active, 10.0 * np.sin(omega * time + shift), 0.0
        )
        if trv:
            data["v_source_{}_kv".format(phase)] = 187.8 * np.sin(omega * time + shift)
            data["v_load_{}_kv".format(phase)] = np.where(
                time >= scenario.clearing_time_s,
                20.0 * np.exp(-(time - scenario.clearing_time_s) / 0.005)
                * np.sin(2.0 * np.pi * 2000.0 * (time - scenario.clearing_time_s)),
                0.0,
            )
        else:
            data["v_fault_{}_kv".format(phase)] = np.where(
                active, 2.0, 187.8 * np.sin(omega * time + shift)
            )
            data["v_source_{}_kv".format(phase)] = 187.8 * np.sin(omega * time + shift)
    return pd.DataFrame(data)


def test_fault_campaign_sizes_and_manifest(tmp_path: Path) -> None:
    trv = fault_scenarios(_config("06_circuit_breaker_trv"))
    faults = fault_scenarios(_config("07_faults_variable_clearing"))
    assert len(trv) == 3
    assert len(faults) == 9
    assert {item.fault_id for item in faults} == {
        "single_phase_ground",
        "phase_to_phase",
        "three_phase",
    }
    manifest = export_fault_manifest(faults, tmp_path / "manifest.csv")
    assert len(manifest.read_text(encoding="utf-8").splitlines()) == 10


def test_trv_metrics_and_plots(tmp_path: Path) -> None:
    config = _config("06_circuit_breaker_trv")
    scenario = fault_scenarios(config)[0]
    frame = _frame(scenario, trv=True)
    metrics = trv_metrics(frame, scenario, config)
    assert metrics["trv_peak_kv"] > 100.0
    assert metrics["average_rrrv_kv_per_us"] > 0.0
    assert plot_trv_waveforms(frame, scenario, metrics, tmp_path / "trv.png").is_file()
    summary = pd.DataFrame([{**scenario.__dict__, **metrics}])
    assert plot_fault_summary(summary, tmp_path / "summary.png", trv=True).is_file()


def test_fault_metrics_and_plots(tmp_path: Path) -> None:
    config = _config("07_faults_variable_clearing")
    scenario = fault_scenarios(config)[0]
    frame = _frame(scenario, trv=False)
    metrics = fault_metrics(frame, scenario, config)
    assert metrics["current_peak_ka"] > 9.0
    assert metrics["i2t_ka2s"] > 0.0
    assert plot_fault_waveforms(frame, scenario, metrics, tmp_path / "fault.png").is_file()
    summary = pd.DataFrame([{**scenario.__dict__, **metrics}])
    assert plot_fault_summary(summary, tmp_path / "summary.png", trv=False).is_file()
