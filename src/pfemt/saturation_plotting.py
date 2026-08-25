"""Summary plots for transformer magnetic-parameter sensitivity."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from pfemt.saturation import SaturationScenario


def plot_saturation_curves(
    scenarios: Iterable[SaturationScenario], destination: Path
) -> Path:
    """Overlay transparent two-slope envelopes for all declared variants."""
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    flux = np.linspace(0.0, 1.5, 500)
    linear_reactance = 168.168
    fig, axis = plt.subplots(figsize=(9.5, 6.2), constrained_layout=True)
    for scenario in scenarios:
        knee_current = scenario.knee_flux_pu / linear_reactance
        current = np.where(
            flux <= scenario.knee_flux_pu,
            flux / linear_reactance,
            knee_current
            + (flux - scenario.knee_flux_pu) / scenario.air_core_reactance_pu,
        )
        axis.plot(current, flux, linewidth=2, label=scenario.label)
    axis.set_xlabel("Magnetizing current [pu peak]")
    axis.set_ylabel("Flux [pu peak]")
    axis.set_title("Declared magnetic sensitivity envelopes")
    axis.grid(True, alpha=0.25)
    axis.legend(fontsize=7, ncol=2)
    fig.savefig(output, dpi=180)
    plt.close(fig)
    return output


def plot_saturation_summary(summary: pd.DataFrame, destination: Path) -> Path:
    """Plot current/flux response and a baseline-relative tornado ranking."""
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    baseline = summary.loc[summary["scenario_id"] == "baseline"].iloc[0]
    ordered = summary.copy()
    ordered["current_change_pct"] = (
        ordered["current_peak_pu"] / float(baseline["current_peak_pu"]) - 1.0
    ) * 100.0
    tornado = ordered.loc[ordered["scenario_id"] != "baseline"].sort_values(
        "current_change_pct"
    )
    fig, axes = plt.subplots(1, 2, figsize=(15, 6.4), constrained_layout=True)
    axes[0].scatter(
        ordered["flux_proxy_peak_pu"],
        ordered["current_peak_pu"],
        c=ordered["knee_flux_pu"],
        cmap="viridis",
        s=80,
    )
    for _, row in ordered.iterrows():
        axes[0].annotate(
            row["scenario_id"],
            (row["flux_proxy_peak_pu"], row["current_peak_pu"]),
            xytext=(4, 4),
            textcoords="offset points",
            fontsize=7,
        )
    axes[0].set_xlabel("Peak voltage-integral flux proxy [pu]")
    axes[0].set_ylabel("Peak HV current [pu]")
    axes[0].set_title("Executed magnetic variants")
    axes[0].grid(True, alpha=0.25)
    colors = np.where(tornado["current_change_pct"] >= 0.0, "#B22222", "#0072B2")
    axes[1].barh(tornado["label"], tornado["current_change_pct"], color=colors)
    axes[1].axvline(0.0, color="#333333", linewidth=1)
    axes[1].set_xlabel("Change in peak HV current from baseline [%]")
    axes[1].set_title("One-at-a-time sensitivity ranking")
    axes[1].grid(True, axis="x", alpha=0.25)
    fig.suptitle("Study 05 transformer saturation sensitivity")
    fig.savefig(output, dpi=180)
    plt.close(fig)
    return output
