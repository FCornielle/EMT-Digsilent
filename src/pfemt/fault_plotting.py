"""Educational figures for breaker-TRV and variable-clearing studies."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from pfemt.faults import FaultScenario

COLORS = ("#0072B2", "#D55E00", "#009E73")


def plot_fault_waveforms(
    frame: pd.DataFrame,
    scenario: FaultScenario,
    metrics: Mapping[str, float],
    destination: Path,
) -> Path:
    """Plot instantaneous current, bus voltage, RMS envelope, and I2t build-up."""
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    relative_ms = (frame["time_s"] - scenario.fault_time_s) * 1000.0
    fig, axes = plt.subplots(2, 2, figsize=(15.2, 9.0), constrained_layout=True)
    currents = ["i_a_ka", "i_b_ka", "i_c_ka"]
    voltages = ["v_fault_a_kv", "v_fault_b_kv", "v_fault_c_kv"]
    for color, phase, column in zip(COLORS, "ABC", currents):
        axes[0, 0].plot(relative_ms, frame[column], color=color, label="Phase {}".format(phase))
    axes[0, 0].set_title("Fault current | peak {:.2f} kA".format(metrics["current_peak_ka"]))
    axes[0, 0].set_ylabel("Current [kA]")
    axes[0, 0].legend(ncol=3)
    for color, phase, column in zip(COLORS, "ABC", voltages):
        axes[0, 1].plot(relative_ms, frame[column], color=color, label="Phase {}".format(phase))
    axes[0, 1].set_title("Fault-bus phase voltage")
    axes[0, 1].set_ylabel("Voltage [kV]")
    ordered = frame.sort_values("time_s").drop_duplicates("time_s", keep="last")
    window = max(3, int(round(0.02 / np.median(np.diff(ordered["time_s"])))))
    for color, phase, column in zip(COLORS, "ABC", currents):
        rms = np.sqrt(ordered[column].pow(2).rolling(window, min_periods=1).mean())
        axes[1, 0].plot(
            (ordered["time_s"] - scenario.fault_time_s) * 1000.0,
            rms,
            color=color,
            label=phase,
        )
    axes[1, 0].set_title("One-cycle moving RMS current")
    axes[1, 0].set_ylabel("RMS current [kA]")
    current_matrix = ordered[currents].to_numpy(dtype=float)
    dt = np.diff(ordered["time_s"].to_numpy(dtype=float), prepend=ordered["time_s"].iloc[0])
    i2t = np.cumsum(np.sum(np.square(current_matrix), axis=1) * dt)
    axes[1, 1].plot(
        (ordered["time_s"] - scenario.fault_time_s) * 1000.0,
        i2t,
        color="#6A3D9A",
    )
    axes[1, 1].set_title("Three-phase thermal duty integral")
    axes[1, 1].set_ylabel("I-squared-t [kA²s]")
    for axis in axes.flat:
        axis.axvline(0.0, color="black", linestyle="--", linewidth=1)
        axis.axvline(
            (scenario.clearing_time_s - scenario.fault_time_s) * 1000.0,
            color="#CC79A7",
            linestyle="--",
            linewidth=1,
        )
        axis.set_xlabel("Time relative to fault inception [ms]")
        axis.grid(True, alpha=0.25)
    fig.suptitle("{} | {}".format(scenario.scenario_id, scenario.fault_label))
    fig.savefig(output, dpi=180)
    plt.close(fig)
    return output


def plot_trv_waveforms(
    frame: pd.DataFrame,
    scenario: FaultScenario,
    metrics: Mapping[str, float],
    destination: Path,
) -> Path:
    """Plot breaker currents, both terminal voltages, and contact TRV."""
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    relative_us = (frame["time_s"] - scenario.clearing_time_s) * 1e6
    mask = (relative_us >= -5000.0) & (relative_us <= 15000.0)
    fig, axes = plt.subplots(2, 2, figsize=(15.2, 9.0), constrained_layout=True)
    for color, phase, column in zip(COLORS, "ABC", ("i_a_ka", "i_b_ka", "i_c_ka")):
        axes[0, 0].plot(relative_us[mask], frame.loc[mask, column], color=color, label=phase)
    axes[0, 0].set_title("Breaker current before commanded opening")
    axes[0, 0].set_ylabel("Current [kA]")
    axes[0, 0].legend(ncol=3)
    for color, phase in zip(COLORS, "abc"):
        axes[0, 1].plot(
            relative_us[mask], frame.loc[mask, "v_source_{}_kv".format(phase)], color=color
        )
    axes[0, 1].set_title("Source-side phase voltage")
    axes[0, 1].set_ylabel("Voltage [kV]")
    for color, phase in zip(COLORS, "abc"):
        axes[1, 0].plot(
            relative_us[mask], frame.loc[mask, "v_load_{}_kv".format(phase)], color=color
        )
    axes[1, 0].set_title("Load-side phase voltage")
    axes[1, 0].set_ylabel("Voltage [kV]")
    for color, phase in zip(COLORS, "abc"):
        contact = frame["v_source_{}_kv".format(phase)] - frame["v_load_{}_kv".format(phase)]
        axes[1, 1].plot(relative_us[mask], contact[mask], color=color, label=phase.upper())
    axes[1, 1].set_title(
        "Contact TRV | peak {:.1f} kV | avg. RRRV {:.3f} kV/us".format(
            metrics["trv_peak_kv"], metrics["average_rrrv_kv_per_us"]
        )
    )
    axes[1, 1].set_ylabel("Source minus load voltage [kV]")
    for axis in axes.flat:
        axis.axvline(0.0, color="black", linestyle="--", linewidth=1)
        axis.set_xlabel("Time relative to commanded opening [us]")
        axis.grid(True, alpha=0.25)
    fig.suptitle("{} | ideal three-pole breaker baseline".format(scenario.scenario_id))
    fig.savefig(output, dpi=180)
    plt.close(fig)
    return output


def plot_fault_summary(summary: pd.DataFrame, destination: Path, trv: bool) -> Path:
    """Plot campaign KPIs by clearing duration."""
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    if trv:
        panels = (
            ("trv_peak_kv", "Peak TRV [kV]"),
            ("average_rrrv_kv_per_us", "Average RRRV [kV/us]"),
            ("interruption_current_peak_ka", "Pre-opening current peak [kA]"),
        )
    else:
        panels = (
            ("current_peak_ka", "Peak current [kA]"),
            ("first_cycle_rms_max_ka", "First-cycle RMS [kA]"),
            ("i2t_ka2s", "I-squared-t [kA²s]"),
        )
    fig, axes = plt.subplots(1, 3, figsize=(16.0, 5.2), constrained_layout=True)
    for fault_label, group in summary.groupby("fault_label", sort=False):
        ordered = group.sort_values("fault_duration_ms")
        for axis, (column, ylabel) in zip(axes, panels):
            axis.plot(
                ordered["fault_duration_ms"],
                ordered[column],
                marker="o",
                linewidth=2,
                label=str(fault_label),
            )
            axis.set_xlabel("Fault duration [ms]")
            axis.set_ylabel(ylabel)
            axis.grid(True, alpha=0.25)
    axes[0].legend(fontsize=8)
    fig.suptitle("Study 06 breaker TRV campaign" if trv else "Study 07 variable-clearing campaign")
    fig.savefig(output, dpi=180)
    plt.close(fig)
    return output
