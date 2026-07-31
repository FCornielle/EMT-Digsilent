"""Publication-style EMT plots with explicit units and event annotations."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PHASE_COLORS = ("#0072B2", "#D55E00", "#009E73")


def _style() -> None:
    plt.rcParams.update(
        {
            "figure.dpi": 120,
            "savefig.dpi": 180,
            "font.size": 10,
            "axes.grid": True,
            "grid.alpha": 0.25,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "legend.frameon": False,
        }
    )


def _output(destination: Path) -> Path:
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    return output


def plot_line_energization(
    frame: pd.DataFrame,
    metrics: Mapping[str, object],
    destination: Path,
    title: str,
    voltage_columns: Sequence[str] = ("v_recv_a_kv", "v_recv_b_kv", "v_recv_c_kv"),
    current_columns: Sequence[str] = ("i_send_a_ka", "i_send_b_ka", "i_send_c_ka"),
) -> Path:
    """Plot receiving-end voltage and sending-end current waveforms."""
    _style()
    output = _output(destination)
    time_ms = frame["time_s"] * 1000.0
    switching_ms = float(metrics["switching_time_s"]) * 1000.0
    figure, axes = plt.subplots(2, 1, figsize=(10.5, 7.0), sharex=True, constrained_layout=True)
    phase_names = ("Phase A", "Phase B", "Phase C")
    for index, column in enumerate(voltage_columns):
        axes[0].plot(time_ms, frame[column], color=PHASE_COLORS[index], label=phase_names[index])
    axes[0].axvline(switching_ms, color="#222222", linestyle="--", linewidth=1.0)
    axes[0].set_ylabel("Receiving-end phase-ground voltage [kV]")
    axes[0].legend(ncol=3, loc="upper right")
    axes[0].set_title(title)
    axes[0].text(
        0.01,
        0.04,
        "Peak = {:.3f} pu".format(float(metrics["voltage_peak_pu"])),
        transform=axes[0].transAxes,
        bbox={"facecolor": "white", "alpha": 0.85, "edgecolor": "none"},
    )
    for index, column in enumerate(current_columns):
        axes[1].plot(time_ms, frame[column], color=PHASE_COLORS[index], label=phase_names[index])
    axes[1].axvline(
        switching_ms,
        color="#222222",
        linestyle="--",
        linewidth=1.0,
        label="Breaker close",
    )
    axes[1].set_ylabel("Sending-end current [kA]")
    axes[1].set_xlabel("Time [ms]")
    axes[1].legend(ncol=4, loc="upper right")
    figure.savefig(output, bbox_inches="tight")
    plt.close(figure)
    return output


def plot_sweep_summary(
    frame: pd.DataFrame,
    destination: Path,
    title: str = "Point-on-wave sweep",
) -> Path:
    """Plot peak voltage and closing current versus switching angle."""
    _style()
    output = _output(destination)
    ranked = frame.sort_values("switching_angle_deg")
    figure, axes = plt.subplots(2, 1, figsize=(9.5, 7.2), sharex=True, constrained_layout=True)

    voltage_worst = ranked.loc[ranked["voltage_peak_pu"].idxmax()]
    axes[0].plot(
        ranked["switching_angle_deg"],
        ranked["voltage_peak_pu"],
        marker="o",
        color="#0072B2",
        linewidth=1.5,
    )
    axes[0].scatter(
        [voltage_worst["switching_angle_deg"]],
        [voltage_worst["voltage_peak_pu"]],
        color="#D55E00",
        zorder=3,
        label="Maximum overvoltage",
    )
    axes[0].set_ylabel("Peak phase-ground voltage [pu]")
    axes[0].set_title(title)
    axes[0].legend()

    current_worst = ranked.loc[ranked["current_ka_peak"].idxmax()]
    axes[1].plot(
        ranked["switching_angle_deg"],
        ranked["current_ka_peak"],
        marker="s",
        color="#009E73",
        linewidth=1.5,
    )
    axes[1].scatter(
        [current_worst["switching_angle_deg"]],
        [current_worst["current_ka_peak"]],
        color="#CC79A7",
        zorder=3,
        label="Maximum closing current",
    )
    axes[1].set_xlabel("Phase-A switching angle [degrees]")
    axes[1].set_ylabel("Peak sending-end current [kA]")
    axes[1].set_xticks(np.arange(0, 360, 30))
    axes[1].legend()
    figure.savefig(output, bbox_inches="tight")
    plt.close(figure)
    return output


def plot_parameter_overview(
    config: Mapping[str, object],
    derived: Mapping[str, float],
    destination: Path,
) -> Path:
    """Visualize the input basis and first-order travelling-wave quantities."""
    _style()
    output = _output(destination)
    network = config["network"]  # type: ignore[index]
    line = network["line"]  # type: ignore[index]
    parameters = line["sequence_parameters"]  # type: ignore[index]
    figure, axes = plt.subplots(2, 2, figsize=(10.5, 7.5), constrained_layout=True)
    pairs = (
        ("Resistance", "r1_ohm_per_km", "r0_ohm_per_km", "ohm/km"),
        ("Reactance", "x1_ohm_per_km", "x0_ohm_per_km", "ohm/km"),
        ("Susceptance", "b1_us_per_km", "b0_us_per_km", "uS/km"),
    )
    for axis, (title, positive, zero, unit) in zip(axes.flat[:3], pairs):
        values = [float(parameters[positive]), float(parameters[zero])]  # type: ignore[index]
        bars = axis.bar(
            ("Positive sequence", "Zero sequence"),
            values,
            color=("#0072B2", "#D55E00"),
        )
        axis.set_title(title)
        axis.set_ylabel(unit)
        axis.bar_label(bars, fmt="%.3g", padding=3)

    axes[1, 1].axis("off")
    text = "\n".join(
        (
            "System and derived checks",
            "",
            "Nominal voltage: {:.0f} kV LL RMS".format(float(network["nominal_voltage_kv"])),  # type: ignore[index]
            "Line length: {:.0f} km".format(float(line["length_km"])),  # type: ignore[index]
            "Source strength: {:.0f} MVA".format(float(network["source"]["short_circuit_mva"])),  # type: ignore[index]
            "Surge impedance: {:.1f} ohm".format(derived["surge_impedance_ohm"]),
            "Wave velocity: {:.0f} km/s".format(derived["propagation_velocity_km_per_s"]),
            "One-way travel time: {:.3f} ms".format(derived["one_way_travel_time_ms"]),
            "First-order surge current: {:.3f} kA".format(
                derived["first_order_surge_current_ka"]
            ),
        )
    )
    axes[1, 1].text(
        0.05,
        0.95,
        text,
        va="top",
        family="monospace",
        bbox={"boxstyle": "round,pad=0.6", "facecolor": "#F4F6F7", "edgecolor": "#AAB7B8"},
    )
    figure.suptitle("Study input parameters and analytical checks", fontsize=13)
    figure.savefig(output, bbox_inches="tight")
    plt.close(figure)
    return output


def plot_overvoltage_envelope(aligned: pd.DataFrame, destination: Path) -> Path:
    """Plot post-closing overvoltage envelopes aligned to the switching instant."""
    _style()
    output = _output(destination)
    figure, axis = plt.subplots(figsize=(10.0, 5.5), constrained_layout=True)
    angles = sorted(aligned["switching_angle_deg"].unique())
    colors = plt.cm.twilight(np.linspace(0.0, 1.0, len(angles), endpoint=False))
    for color, angle in zip(colors, angles):
        subset = aligned.loc[aligned["switching_angle_deg"] == angle]
        axis.plot(
            subset["relative_time_ms"],
            subset["voltage_envelope_pu"],
            color=color,
            linewidth=1.1,
            label="{:g} deg".format(angle),
        )
    axis.axhline(
        2.0,
        color="#444444",
        linestyle=":",
        linewidth=1.2,
        label="Ideal open-end step: 2 pu",
    )
    axis.set_xlim(0.0, float(aligned["relative_time_ms"].max()))
    axis.set_xlabel("Time after breaker close [ms]")
    axis.set_ylabel("max(|Va|, |Vb|, |Vc|) [pu]")
    axis.set_title("Receiving-end overvoltage envelope for all switching angles")
    axis.legend(ncol=4, fontsize=8, loc="upper right")
    figure.savefig(output, bbox_inches="tight")
    plt.close(figure)
    return output


def plot_travelling_wave_detail(
    frame: pd.DataFrame,
    metrics: Mapping[str, object],
    travel_time_ms: float,
    destination: Path,
) -> Path:
    """Zoom into the first travelling-wave arrivals for the selected scenario."""
    _style()
    output = _output(destination)
    switching_time = float(metrics["switching_time_s"])
    phase_peak = float(metrics["nominal_phase_peak_kv"])
    relative_ms = (frame["time_s"] - switching_time) * 1000.0
    mask = (relative_ms >= -0.25) & (relative_ms <= 5.0)
    figure, axis = plt.subplots(figsize=(10.0, 5.3), constrained_layout=True)
    for color, phase, column in zip(
        PHASE_COLORS,
        ("Phase A", "Phase B", "Phase C"),
        ("v_recv_a_kv", "v_recv_b_kv", "v_recv_c_kv"),
    ):
        axis.plot(relative_ms[mask], frame.loc[mask, column] / phase_peak, color=color, label=phase)
    axis.axvline(0.0, color="#222222", linestyle="--", linewidth=1.0, label="Breaker close")
    axis.axvline(
        travel_time_ms,
        color="#CC79A7",
        linestyle="--",
        linewidth=1.2,
        label="Analytical one-way travel time",
    )
    axis.axhline(2.0, color="#777777", linestyle=":", linewidth=1.0)
    axis.axhline(-2.0, color="#777777", linestyle=":", linewidth=1.0)
    axis.set_xlabel("Time relative to breaker close [ms]")
    axis.set_ylabel("Receiving-end phase-ground voltage [pu peak base]")
    axis.set_title("Travelling-wave detail for the worst point-on-wave scenario")
    axis.legend(ncol=3, fontsize=8)
    figure.savefig(output, bbox_inches="tight")
    plt.close(figure)
    return output


def plot_timestep_sensitivity(frame: pd.DataFrame, destination: Path) -> Path:
    """Plot peak metrics and deviations against EMT time step."""
    _style()
    output = _output(destination)
    ranked = frame.sort_values("time_step_us")
    reference = ranked.iloc[0]
    voltage_deviation = (
        (ranked["voltage_peak_pu"] - reference["voltage_peak_pu"]).abs()
        / reference["voltage_peak_pu"]
        * 100.0
    )
    current_deviation = (
        (ranked["current_ka_peak"] - reference["current_ka_peak"]).abs()
        / reference["current_ka_peak"]
        * 100.0
    )
    figure, axes = plt.subplots(1, 2, figsize=(10.5, 4.5), constrained_layout=True)
    axes[0].plot(ranked["time_step_us"], ranked["voltage_peak_pu"], marker="o", color="#0072B2")
    axes[0].set_xlabel("EMT time step [us]")
    axes[0].set_ylabel("Peak voltage [pu]")
    axes[0].set_title("Peak-value convergence")
    current_axis = axes[0].twinx()
    current_axis.plot(
        ranked["time_step_us"], ranked["current_ka_peak"], marker="s", color="#D55E00"
    )
    current_axis.set_ylabel("Peak current [kA]", color="#D55E00")
    axes[1].plot(ranked["time_step_us"], voltage_deviation, marker="o", label="Voltage")
    axes[1].plot(ranked["time_step_us"], current_deviation, marker="s", label="Current")
    axes[1].set_xlabel("EMT time step [us]")
    axes[1].set_ylabel("Deviation from finest step [%]")
    axes[1].set_title("Numerical sensitivity")
    axes[1].legend()
    figure.suptitle("Time-step sensitivity at the worst switching angle")
    figure.savefig(output, bbox_inches="tight")
    plt.close(figure)
    return output
