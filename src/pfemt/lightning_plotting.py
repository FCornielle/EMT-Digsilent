"""Educational plots for native impulse and travelling-wave studies."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from pfemt.lightning import LightningScenario


def plot_lightning_waveforms(
    frame: pd.DataFrame,
    scenario: LightningScenario,
    metrics: Mapping[str, float],
    destination: Path,
) -> Path:
    """Plot injected line current and phase-A voltage at three distances."""
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    time_us = frame["time_s"] * 1e6
    fig, axes = plt.subplots(2, 2, figsize=(15.2, 9.0), constrained_layout=True)
    axes[0, 0].plot(time_us, frame["i_injected_a_ka"], color="#D55E00")
    axes[0, 0].set_title(
        "Line entrance current | peak {:.1f} kA".format(metrics["line_current_peak_ka"])
    )
    axes[0, 0].set_ylabel("Current [kA]")
    voltage_channels = (
        ("v_strike_a_kv", "0 km / strike", "#0072B2"),
        ("v_mid_a_kv", "50 km / midpoint", "#009E73"),
        ("v_remote_a_kv", "100 km / remote", "#6A3D9A"),
    )
    for column, label, color in voltage_channels:
        axes[0, 1].plot(time_us, frame[column], label=label, color=color)
    axes[0, 1].set_title("Phase-A travelling voltage waves")
    axes[0, 1].set_ylabel("Voltage [kV]")
    axes[0, 1].legend()
    zoom = (time_us >= -10.0) & (time_us <= 550.0)
    for column, label, color in voltage_channels:
        axes[1, 0].plot(time_us[zoom], frame.loc[zoom, column], label=label, color=color)
    for arrival, color in (
        (metrics["strike_arrival_us"], "#0072B2"),
        (metrics["midpoint_arrival_us"], "#009E73"),
        (metrics["remote_arrival_us"], "#6A3D9A"),
    ):
        axes[1, 0].axvline(arrival, color=color, linestyle="--", linewidth=1)
    axes[1, 0].set_title("First-arrival window at 5% of each local peak")
    axes[1, 0].set_ylabel("Voltage [kV]")
    distances = np.array([0.0, 50.0, 100.0])
    arrivals = np.array(
        [
            metrics["strike_arrival_us"],
            metrics["midpoint_arrival_us"],
            metrics["remote_arrival_us"],
        ]
    )
    axes[1, 1].plot(arrivals, distances, marker="o", linewidth=2, color="#0072B2")
    axes[1, 1].set_title(
        "Measured propagation | {:.0f} km/s".format(metrics["apparent_velocity_km_per_s"])
    )
    axes[1, 1].set_ylabel("Observation distance [km]")
    axes[1, 1].set_xlabel("First-arrival time [microseconds]")
    for axis in axes.flat:
        axis.axvline(0.0, color="black", linestyle=":", linewidth=1)
        axis.grid(True, alpha=0.25)
    axes[0, 0].set_xlabel("Time from impulse start [microseconds]")
    axes[0, 1].set_xlabel("Time from impulse start [microseconds]")
    axes[1, 0].set_xlabel("Time from impulse start [microseconds]")
    fig.suptitle("{} | {}".format(scenario.scenario_id, scenario.label))
    fig.savefig(output, dpi=180)
    plt.close(fig)
    return output


def plot_lightning_summary(summary: pd.DataFrame, destination: Path) -> Path:
    """Compare waveform families, terminal stresses, and propagation checks."""
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    ordered = summary.sort_values("configured_peak_current_ka")
    labels = ordered["scenario_id"].str.replace("_", " ")
    x = np.arange(len(ordered))
    fig, axes = plt.subplots(1, 3, figsize=(16.0, 5.4), constrained_layout=True)
    axes[0].bar(x, ordered["line_current_peak_ka"], color="#D55E00")
    axes[0].set_ylabel("Line entrance current peak [kA]")
    width = 0.25
    for offset, column, label, color in (
        (-width, "strike_voltage_peak_kv", "Strike", "#0072B2"),
        (0.0, "midpoint_voltage_peak_kv", "Midpoint", "#009E73"),
        (width, "remote_voltage_peak_kv", "Remote", "#6A3D9A"),
    ):
        axes[1].bar(x + offset, ordered[column], width=width, label=label, color=color)
    axes[1].set_ylabel("Phase-A voltage peak [kV]")
    axes[1].legend(fontsize=8)
    axes[2].bar(x, ordered["measured_end_to_end_travel_us"], color="#0072B2")
    axes[2].axhline(
        float(ordered["end_to_end_travel_time_us"].iloc[0]),
        color="#D55E00",
        linestyle="--",
        label="Analytical sequence-LC value",
    )
    axes[2].set_ylabel("End-to-end travel time [microseconds]")
    axes[2].legend(fontsize=8)
    for axis in axes:
        axis.set_xticks(x, labels, rotation=20, ha="right")
        axis.grid(True, axis="y", alpha=0.25)
    fig.suptitle("Study 08 native lightning impulse and travelling-wave comparison")
    fig.savefig(output, dpi=180)
    plt.close(fig)
    return output


def plot_distance_time_map(
    frame: pd.DataFrame, scenario: LightningScenario, destination: Path
) -> Path:
    """Interpolate the three retained observation traces into a distance-time map."""
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    ordered = frame.sort_values("time_s").drop_duplicates("time_s", keep="last")
    time_us = ordered["time_s"].to_numpy(dtype=float) * 1e6
    mask = (time_us >= 0.0) & (time_us <= 700.0)
    traces = ordered.loc[
        mask, ["v_strike_a_kv", "v_mid_a_kv", "v_remote_a_kv"]
    ].to_numpy(dtype=float).T
    known_distance = np.array([0.0, 50.0, 100.0])
    distance = np.linspace(0.0, 100.0, 101)
    interpolated = np.vstack(
        [np.interp(distance, known_distance, traces[:, index]) for index in range(traces.shape[1])]
    ).T
    fig, axis = plt.subplots(figsize=(13.5, 5.8), constrained_layout=True)
    image = axis.pcolormesh(time_us[mask], distance, interpolated, shading="auto", cmap="RdBu_r")
    fig.colorbar(image, ax=axis, label="Interpolated phase-A voltage [kV]")
    axis.set_xlabel("Time from impulse start [microseconds]")
    axis.set_ylabel("Distance from strike [km]")
    axis.set_title(
        "{} distance-time view | interpolation of retained 0/50/100 km channels".format(
            scenario.scenario_id
        )
    )
    fig.savefig(output, dpi=180)
    plt.close(fig)
    return output
