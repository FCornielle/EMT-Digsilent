"""Educational figures for capacitor-bank energization studies."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from pfemt.capacitor import CapacitorScenario, capacitor_derived_quantities


def plot_capacitor_waveforms(
    frame: pd.DataFrame,
    scenario: CapacitorScenario,
    metrics: Mapping[str, float],
    destination: Path,
) -> Path:
    """Plot bank current, bus/bank voltages, spectrum, and di/dt."""
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    relative_ms = (frame["time_s"] - scenario.switching_time_s) * 1000.0
    mask = (relative_ms >= -2.0) & (relative_ms <= 30.0)
    colors = ("#0072B2", "#D55E00", "#009E73")
    fig, axes = plt.subplots(2, 2, figsize=(15.5, 9.2), constrained_layout=True)
    for color, phase, column in zip(
        colors,
        "ABC",
        ("i_bank_a_ka", "i_bank_b_ka", "i_bank_c_ka"),
    ):
        axes[0, 0].plot(relative_ms[mask], frame.loc[mask, column], color=color, label=phase)
    axes[0, 0].set_title(
        "Switched-bank current | peak {:.2f} kA".format(metrics["current_peak_ka"])
    )
    axes[0, 0].set_ylabel("Current [kA]")
    axes[0, 0].legend(ncol=3)
    for color, phase, column in zip(
        colors,
        "ABC",
        ("v_main_a_kv", "v_main_b_kv", "v_main_c_kv"),
    ):
        axes[0, 1].plot(relative_ms[mask], frame.loc[mask, column], color=color, label=phase)
    axes[0, 1].set_title("Main-bus phase voltage")
    axes[0, 1].set_ylabel("Voltage [kV]")
    for color, phase, column in zip(
        colors,
        "ABC",
        ("v_bank_a_kv", "v_bank_b_kv", "v_bank_c_kv"),
    ):
        axes[1, 0].plot(relative_ms[mask], frame.loc[mask, column], color=color, label=phase)
    axes[1, 0].set_title("Switched-bank terminal voltage")
    axes[1, 0].set_ylabel("Voltage [kV]")
    early = frame.loc[
        (frame["time_s"] >= scenario.switching_time_s)
        & (frame["time_s"] <= scenario.switching_time_s + 0.02)
    ]
    values = early["i_bank_a_ka"].to_numpy(dtype=float)
    if len(values) > 8:
        dt = float(np.median(np.diff(early["time_s"].to_numpy(dtype=float))))
        spectrum = np.abs(np.fft.rfft(values - np.mean(values))) * 2.0 / len(values)
        frequencies = np.fft.rfftfreq(len(values), dt)
        frequency_mask = frequencies <= 15000.0
        axes[1, 1].plot(
            frequencies[frequency_mask] / 1000.0,
            spectrum[frequency_mask],
            color="#6A3D9A",
        )
    axes[1, 1].axvline(metrics["dominant_frequency_hz"] / 1000.0, color="#D55E00", linestyle="--")
    axes[1, 1].set_title(
        "Early current spectrum | dominant {:.2f} kHz".format(
            metrics["dominant_frequency_hz"] / 1000.0
        )
    )
    axes[1, 1].set_xlabel("Frequency [kHz]")
    axes[1, 1].set_ylabel("Current magnitude [kA]")
    for axis in axes.flat:
        axis.grid(True, alpha=0.25)
    for axis in axes[:, 0]:
        axis.set_xlabel("Time relative to closing [ms]")
    axes[0, 1].set_xlabel("Time relative to closing [ms]")
    fig.suptitle(
        "{} | {} | close at {:.0f} degrees".format(
            scenario.scenario_id,
            scenario.topology_label,
            scenario.switching_angle_deg,
        )
    )
    fig.savefig(output, dpi=180)
    plt.close(fig)
    return output


def plot_capacitor_summary(summary: pd.DataFrame, destination: Path) -> Path:
    """Compare topology and point-on-wave duties."""
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.2), constrained_layout=True)
    panels = (
        ("current_peak_ka", "Peak switched-bank current [kA]"),
        ("peak_didt_ka_per_ms", "Peak |di/dt| [kA/ms]"),
        ("bank_voltage_peak_pu", "Peak bank voltage [pu]"),
    )
    for topology, group in summary.groupby("topology_label", sort=False):
        ordered = group.sort_values("switching_angle_deg")
        for axis, (column, ylabel) in zip(axes, panels):
            axis.plot(
                ordered["switching_angle_deg"],
                ordered[column],
                marker="o",
                linewidth=2,
                label=str(topology),
            )
            axis.set_xlabel("Phase-A closing angle [degrees]")
            axis.set_ylabel(ylabel)
            axis.grid(True, alpha=0.25)
    axes[0].legend(fontsize=8)
    fig.suptitle("Study 04 capacitor switching: isolated versus back-to-back")
    fig.savefig(output, dpi=180)
    plt.close(fig)
    return output


def plot_capacitor_design_basis(config: Mapping[str, object], destination: Path) -> Path:
    """Plot the analytical LC checks and declared equipment basis."""
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    derived = capacitor_derived_quantities(config)
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.2), constrained_layout=True)
    axes[0].bar(
        ["Isolated bank", "Back-to-back"],
        [derived["isolated_frequency_hz"] / 1000.0, derived["back_to_back_frequency_hz"] / 1000.0],
        color=("#0072B2", "#D55E00"),
    )
    axes[0].set_ylabel("First-order natural frequency [kHz]")
    axes[0].set_title("Analytical LC screening values")
    axes[0].grid(True, axis="y", alpha=0.25)
    axes[1].axis("off")
    lines = [
        "230 kV grounded-wye bank",
        "Bank rating: 100 Mvar per branch",
        "Phase capacitance: {:.3f} uF".format(derived["phase_capacitance_uf"]),
        "Source inductance: {:.3f} mH".format(derived["source_inductance_mh"]),
        "Series reactor: {:.3f} mH".format(derived["reactor_inductance_mh"]),
        "Rated bank current: {:.3f} kA".format(derived["bank_rated_current_ka"]),
        "Illustrative inputs: replace with site data",
    ]
    axes[1].text(0.03, 0.95, "\n".join(lines), va="top", fontsize=12, linespacing=1.6)
    fig.suptitle("Study 04 capacitor-switching design basis — not EMT results")
    fig.savefig(output, dpi=180)
    plt.close(fig)
    return output
