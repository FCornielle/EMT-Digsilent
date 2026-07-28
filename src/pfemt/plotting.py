"""Publication-style EMT plots with explicit units and event annotation."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
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
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    time_ms = frame["time_s"] * 1000.0
    switching_ms = float(metrics["switching_time_s"]) * 1000.0
    figure, axes = plt.subplots(2, 1, figsize=(10.5, 7.0), sharex=True, constrained_layout=True)
    phase_names = ("A", "B", "C")
    for index, column in enumerate(voltage_columns):
        axes[0].plot(time_ms, frame[column], color=PHASE_COLORS[index], label=phase_names[index])
    axes[0].axvline(switching_ms, color="#222222", linestyle="--", linewidth=1.0)
    axes[0].set_ylabel("Voltaje fase-tierra [kV]")
    axes[0].legend(ncol=3, loc="upper right")
    axes[0].set_title(title)
    peak_text = "Pico = {:.3f} pu".format(float(metrics["voltage_peak_pu"]))
    axes[0].text(
        0.01,
        0.04,
        peak_text,
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
        label="Cierre",
    )
    axes[1].set_ylabel("Corriente de envío [kA]")
    axes[1].set_xlabel("Tiempo [ms]")
    axes[1].legend(ncol=4, loc="upper right")
    figure.savefig(output, bbox_inches="tight")
    plt.close(figure)
    return output


def plot_sweep_summary(
    frame: pd.DataFrame,
    destination: Path,
    title: str = "Barrido de punto sobre onda",
) -> Path:
    """Plot peak overvoltage versus switching angle."""
    _style()
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    ranked = frame.sort_values("switching_angle_deg")
    figure, axis = plt.subplots(figsize=(9.0, 4.8), constrained_layout=True)
    axis.plot(
        ranked["switching_angle_deg"],
        ranked["voltage_peak_pu"],
        marker="o",
        color="#0072B2",
        linewidth=1.5,
    )
    worst_index = ranked["voltage_peak_pu"].idxmax()
    worst = ranked.loc[worst_index]
    axis.scatter(
        [worst["switching_angle_deg"]],
        [worst["voltage_peak_pu"]],
        color="#D55E00",
        zorder=3,
        label="Peor caso",
    )
    axis.set_xlabel("Ángulo de cierre fase A [°]")
    axis.set_ylabel("Sobretensión pico [pu]")
    axis.set_title(title)
    axis.legend()
    figure.savefig(output, bbox_inches="tight")
    plt.close(figure)
    return output

