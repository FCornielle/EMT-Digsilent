"""Educational plots for transformer energization and residual-flux studies."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from pfemt.transformer import (
    TransformerScenario,
    reconstruct_flux_proxy,
    transformer_derived_quantities,
)


def plot_transformer_waveforms(
    frame: pd.DataFrame,
    scenario: TransformerScenario,
    metrics: Mapping[str, object],
    config: Mapping[str, object],
    destination: Path,
) -> Path:
    """Plot currents, reconstructed flux, voltages, and early harmonic spectrum."""
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    network = config["network"]  # type: ignore[index]
    frequency_hz = float(network["frequency_hz"])  # type: ignore[index]
    flux = reconstruct_flux_proxy(
        frame,
        scenario.switching_time_s,
        frequency_hz,
        float(network["transformer"]["hv_voltage_kv"]),  # type: ignore[index]
        (
            scenario.residual_flux_a_pu,
            scenario.residual_flux_b_pu,
            scenario.residual_flux_c_pu,
        ),
    )
    relative_ms = (frame["time_s"] - scenario.switching_time_s) * 1000.0
    mask = (relative_ms >= -5.0) & (relative_ms <= 100.0)
    fig, axes = plt.subplots(2, 2, figsize=(15.5, 9.5), constrained_layout=True)
    colors = ("#0072B2", "#D55E00", "#009E73")
    for color, phase, column in zip(colors, "ABC", ("i_hv_a_ka", "i_hv_b_ka", "i_hv_c_ka")):
        axes[0, 0].plot(
            relative_ms[mask],
            frame.loc[mask, column],
            color=color,
            label="Phase " + phase,
        )
    axes[0, 0].set_title("HV inrush current | peak {:.3f} kA ({:.2f} pu)".format(
        float(metrics["current_peak_ka"]), float(metrics["current_peak_pu"])
    ))
    axes[0, 0].set_ylabel("Current [kA]")
    axes[0, 0].legend(ncol=3)

    for color, phase, column in zip(colors, "ABC", ("flux_a_pu", "flux_b_pu", "flux_c_pu")):
        axes[0, 1].plot(
            relative_ms[mask],
            flux.loc[mask, column],
            color=color,
            label="Phase " + phase,
        )
    knee_flux_pu = float(network["transformer"]["saturation"]["knee_flux_pu"])  # type: ignore[index]
    axes[0, 1].axhline(
        knee_flux_pu,
        color="#555555",
        linestyle="--",
        label="Declared knee",
    )
    axes[0, 1].axhline(-knee_flux_pu, color="#555555", linestyle="--")
    axes[0, 1].set_title("Voltage-integral flux proxy | peak {:.3f} pu".format(
        float(metrics["flux_proxy_peak_pu"])
    ))
    axes[0, 1].set_ylabel("Flux proxy [pu]")
    axes[0, 1].legend(ncol=2)

    for color, phase, column in zip(colors, "ABC", ("v_lv_a_kv", "v_lv_b_kv", "v_lv_c_kv")):
        axes[1, 0].plot(
            relative_ms[mask],
            frame.loc[mask, column],
            color=color,
            label="Phase " + phase,
        )
    axes[1, 0].set_title("Open-circuit LV terminal voltage")
    axes[1, 0].set_ylabel("Voltage [kV]")

    post = frame.loc[
        (frame["time_s"] >= scenario.switching_time_s)
        & (frame["time_s"] <= scenario.switching_time_s + 0.1)
    ]
    values = post[str(metrics["current_peak_phase"])].to_numpy(dtype=float)
    if len(values) > 3:
        dt = float(np.median(np.diff(post["time_s"].to_numpy(dtype=float))))
        spectrum = np.abs(np.fft.rfft(values - np.mean(values))) * 2.0 / len(values)
        frequencies = np.fft.rfftfreq(len(values), dt)
        harmonic_orders = np.arange(1, 11)
        magnitudes = np.asarray(
            [
                spectrum[int(np.argmin(np.abs(frequencies - order * frequency_hz)))]
                for order in harmonic_orders
            ]
        )
        axes[1, 1].bar(harmonic_orders, magnitudes, color="#6A3D9A")
    axes[1, 1].set_title("First 100 ms current spectrum | I2/I1 {:.1%}".format(
        float(metrics["second_harmonic_ratio"])
    ))
    axes[1, 1].set_xlabel("Harmonic order")
    axes[1, 1].set_ylabel("Peak current [kA]")
    axes[1, 1].set_xticks(range(1, 11))

    for axis in axes.flat:
        axis.grid(True, alpha=0.25)
    for axis in axes[0, :]:
        axis.set_xlabel("Time relative to closing [ms]")
    axes[1, 0].set_xlabel("Time relative to closing [ms]")
    fig.suptitle(
        "{} | {} | phase-A close at {:.0f} degrees".format(
            scenario.scenario_id,
            scenario.residual_label,
            scenario.switching_angle_deg,
        ),
        fontsize=15,
    )
    fig.savefig(output, dpi=180)
    plt.close(fig)
    return output


def plot_transformer_sweep_summary(summary: pd.DataFrame, destination: Path) -> Path:
    """Compare inrush and flux-proxy severity across angle and residual state."""
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.2), constrained_layout=True)
    panels = (
        ("current_peak_pu", "HV inrush current [pu peak]"),
        ("flux_proxy_peak_pu", "Flux proxy [pu peak]"),
        ("second_harmonic_ratio", "Second harmonic / fundamental"),
    )
    for _residual_id, group in summary.groupby("residual_id", sort=False):
        ordered = group.sort_values("switching_angle_deg")
        label = str(ordered.iloc[0]["residual_label"])
        for axis, (column, ylabel) in zip(axes, panels):
            axis.plot(
                ordered["switching_angle_deg"],
                ordered[column],
                marker="o",
                linewidth=2,
                label=label,
            )
            axis.set_xlabel("Phase-A closing angle [degrees]")
            axis.set_ylabel(ylabel)
            axis.grid(True, alpha=0.25)
    axes[0].legend(fontsize=8)
    fig.suptitle("Study 03 transformer inrush: point on wave and residual flux")
    fig.savefig(output, dpi=180)
    plt.close(fig)
    return output


def plot_transformer_heatmaps(summary: pd.DataFrame, destination: Path) -> Path:
    """Plot angle-by-residual-state severity maps for current and flux."""
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.6), constrained_layout=True)
    panels = (
        ("current_peak_pu", "Peak HV inrush current [pu]", "magma"),
        ("flux_proxy_peak_pu", "Peak voltage-integral flux proxy [pu]", "viridis"),
    )
    residual_order = list(dict.fromkeys(summary["residual_label"].astype(str)))
    angle_order = sorted(summary["switching_angle_deg"].astype(float).unique())
    for axis, (column, title, cmap) in zip(axes, panels):
        matrix = (
            summary.pivot(
                index="residual_label",
                columns="switching_angle_deg",
                values=column,
            )
            .reindex(index=residual_order, columns=angle_order)
            .to_numpy(dtype=float)
        )
        image = axis.imshow(matrix, aspect="auto", cmap=cmap)
        axis.set_xticks(range(len(angle_order)), ["{:g}".format(x) for x in angle_order])
        axis.set_yticks(range(len(residual_order)), residual_order)
        axis.set_xlabel("Phase-A closing angle [degrees]")
        axis.set_title(title)
        for row in range(matrix.shape[0]):
            for column_index in range(matrix.shape[1]):
                axis.text(
                    column_index,
                    row,
                    "{:.2f}".format(matrix[row, column_index]),
                    ha="center",
                    va="center",
                    color="white" if matrix[row, column_index] > np.nanmean(matrix) else "black",
                    fontsize=8,
                )
        fig.colorbar(image, ax=axis, shrink=0.85)
    fig.suptitle("Study 03 severity map from executed PowerFactory EMT scenarios")
    fig.savefig(output, dpi=180)
    plt.close(fig)
    return output


def plot_transformer_ranking(summary: pd.DataFrame, destination: Path) -> Path:
    """Rank the governing inrush cases and compare current against flux proxy."""
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    ordered = summary.sort_values("current_peak_pu", ascending=False)
    top = ordered.head(10).sort_values("current_peak_pu")
    fig, axes = plt.subplots(1, 2, figsize=(15, 6.5), constrained_layout=True)
    axes[0].barh(top["scenario_id"], top["current_peak_pu"], color="#8B1A1A")
    axes[0].set_xlabel("Peak HV current [pu]")
    axes[0].set_title("Ten highest-current scenarios")
    axes[0].grid(True, axis="x", alpha=0.25)
    colors = {name: color for name, color in zip(
        dict.fromkeys(ordered["residual_label"].astype(str)),
        ("#0072B2", "#D55E00", "#009E73"),
    )}
    for residual, group in ordered.groupby("residual_label", sort=False):
        axes[1].scatter(
            group["flux_proxy_peak_pu"],
            group["current_peak_pu"],
            s=55,
            label=str(residual),
            color=colors[str(residual)],
        )
    axes[1].set_xlabel("Peak voltage-integral flux proxy [pu]")
    axes[1].set_ylabel("Peak HV current [pu]")
    axes[1].set_title("Flux excursion governs saturation severity")
    axes[1].grid(True, alpha=0.25)
    axes[1].legend(fontsize=8)
    fig.suptitle("Study 03 governing-case ranking")
    fig.savefig(output, dpi=180)
    plt.close(fig)
    return output


def plot_transformer_design_basis(config: Mapping[str, object], destination: Path) -> Path:
    """Plot the declared nonlinear model inputs and transformer rated bases."""
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    network = config["network"]  # type: ignore[index]
    transformer = network["transformer"]  # type: ignore[index]
    saturation = transformer["saturation"]  # type: ignore[index]
    derived = transformer_derived_quantities(config)
    flux = np.linspace(0.0, 1.5, 400)
    no_load_current_pu = float(transformer["no_load_current_pct"]) / 100.0
    no_load_loss_pu = float(transformer["no_load_losses_kw"]) / (
        float(transformer["rated_power_mva"]) * 1000.0
    )
    magnetizing_current_pu = np.sqrt(
        max(no_load_current_pu**2 - no_load_loss_pu**2, 0.0)
    )
    linear_reactance_pu = 1.0 / magnetizing_current_pu
    knee = float(saturation["knee_flux_pu"])
    air_core_reactance_pu = float(saturation["air_core_reactance_pu"])
    linear_current = flux / linear_reactance_pu
    knee_current = knee / linear_reactance_pu
    current = np.where(
        flux <= knee,
        linear_current,
        knee_current + (flux - knee) / air_core_reactance_pu,
    )
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.2), constrained_layout=True)
    axes[0].plot(current, flux, color="#0072B2", marker="o", linewidth=2)
    axes[0].axhline(float(saturation["knee_flux_pu"]), color="#D55E00", linestyle="--")
    axes[0].set_xlabel("Magnetizing current [pu peak]")
    axes[0].set_ylabel("Flux [pu peak]")
    axes[0].set_title("Declared equivalent saturation basis")
    axes[0].grid(True, alpha=0.25)
    axes[1].axis("off")
    lines = [
        "100 MVA, 230/34.5 kV, YN-D benchmark",
        "HV rated current: {:.3f} kA".format(derived["rated_hv_current_ka"]),
        "LV rated current: {:.3f} kA".format(derived["rated_lv_current_ka"]),
        "HV base impedance: {:.1f} ohm".format(derived["hv_base_impedance_ohm"]),
        "Leakage impedance: {:.1f} ohm".format(derived["leakage_impedance_ohm"]),
        "Knee flux: {:.2f} pu".format(float(saturation["knee_flux_pu"])),
        "Polynomial exponent: {:d}".format(int(saturation["saturation_exponent"])),
        "Air-core reactance: {:.2f} pu".format(float(saturation["air_core_reactance_pu"])),
        "Example inputs: replace with factory test data",
    ]
    axes[1].text(0.03, 0.95, "\n".join(lines), va="top", fontsize=12, linespacing=1.6)
    fig.suptitle("Study 03 transformer parameter basis — not EMT results")
    fig.savefig(output, dpi=180)
    plt.close(fig)
    return output
