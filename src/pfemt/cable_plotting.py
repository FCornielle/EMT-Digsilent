"""Educational figures for the HV cable energization design basis."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Mapping

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap

from pfemt.cable import (
    cable_bonding_cases,
    cable_derived_quantities,
    cable_length_sensitivity,
    cable_scenarios,
)


def _style() -> None:
    plt.rcParams.update(
        {
            "axes.grid": True,
            "grid.alpha": 0.25,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "figure.dpi": 140,
        }
    )


def plot_cable_parameter_overview(config: Mapping[str, object], destination: Path) -> Path:
    """Plot the cable input basis and its first-order derived quantities."""
    _style()
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    cable = config["network"]["cable"]  # type: ignore[index]
    electrical = cable["electrical"]  # type: ignore[index]
    derived = cable_derived_quantities(config)
    figure, axes = plt.subplots(2, 2, figsize=(10.5, 7.2), constrained_layout=True)

    bars = axes[0, 0].bar(
        ("R1", "R0"),
        (electrical["r1_ohm_per_km"], electrical["r0_ohm_per_km"]),  # type: ignore[index]
        color=("#0072B2", "#D55E00"),
    )
    axes[0, 0].bar_label(bars, fmt="%.3g", padding=3)
    axes[0, 0].set_ylabel("Resistance [ohm/km]")
    axes[0, 0].set_title("Sequence resistance")

    bars = axes[0, 1].bar(
        ("L1", "L0"),
        (electrical["inductance_mh_per_km"], electrical["inductance0_mh_per_km"]),  # type: ignore[index]
        color=("#0072B2", "#D55E00"),
    )
    axes[0, 1].bar_label(bars, fmt="%.3g", padding=3)
    axes[0, 1].set_ylabel("Inductance [mH/km]")
    axes[0, 1].set_title("Sequence inductance")

    bars = axes[1, 0].bar(
        ("Core-screen", "Zero sequence"),
        (electrical["capacitance_uf_per_km"], electrical["capacitance0_uf_per_km"]),  # type: ignore[index]
        color=("#009E73", "#CC79A7"),
    )
    axes[1, 0].bar_label(bars, fmt="%.3g", padding=3)
    axes[1, 0].set_ylabel("Capacitance [uF/km]")
    axes[1, 0].set_title("Capacitive input basis")

    axes[1, 1].axis("off")
    axes[1, 1].text(
        0.03,
        0.97,
        "\n".join(
            (
                "Analytical design basis",
                "",
                "Voltage: {:.0f} kV LL RMS".format(config["network"]["nominal_voltage_kv"]),  # type: ignore[index]
                "Length: {:.1f} km".format(cable["length_km"]),  # type: ignore[index]
                "C total/phase: {:.2f} uF".format(
                    derived["total_capacitance_uf_per_phase"]
                ),
                "Charging current: {:.3f} kA".format(
                    derived["steady_state_charging_current_ka"]
                ),
                "Stored energy: {:.1f} kJ".format(derived["three_phase_stored_energy_kj"]),
                "Surge impedance: {:.1f} ohm".format(derived["surge_impedance_ohm"]),
                "One-way travel: {:.3f} ms".format(derived["one_way_travel_time_ms"]),
                "Samples/travel time: {:.0f}".format(derived["samples_per_travel_time"]),
            )
        ),
        va="top",
        family="monospace",
        bbox={"boxstyle": "round,pad=0.6", "facecolor": "#F4F6F7", "edgecolor": "#AAB7B8"},
    )
    figure.suptitle("Study 02 cable input basis — not EMT results", fontsize=13)
    figure.savefig(output, bbox_inches="tight")
    plt.close(figure)
    return output


def plot_cable_length_sensitivity(config: Mapping[str, object], destination: Path) -> Path:
    """Plot first-order cable charging quantities versus length."""
    _style()
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    frame = cable_length_sensitivity(config)
    base_length = float(config["network"]["cable"]["length_km"])  # type: ignore[index]
    base = cable_derived_quantities(config)
    figure, axes = plt.subplots(1, 2, figsize=(10.5, 4.4), constrained_layout=True)
    axes[0].plot(frame["length_km"], frame["charging_current_ka"], color="#0072B2")
    axes[0].scatter(
        [base_length], [base["steady_state_charging_current_ka"]], color="#D55E00", zorder=3
    )
    axes[0].set_xlabel("Cable length [km]")
    axes[0].set_ylabel("Steady-state charging current [kA]")
    axes[0].set_title("Capacitive current")

    axes[1].plot(frame["length_km"], frame["stored_energy_kj"], color="#009E73")
    axes[1].scatter(
        [base_length], [base["three_phase_stored_energy_kj"]], color="#D55E00", zorder=3
    )
    axes[1].set_xlabel("Cable length [km]")
    axes[1].set_ylabel("Three-phase stored energy [kJ]")
    axes[1].set_title("Electric-field energy at 1 pu")
    figure.suptitle("Study 02 analytical length sensitivity — not EMT results", fontsize=13)
    figure.savefig(output, bbox_inches="tight")
    plt.close(figure)
    return output


def plot_bonding_matrix(config: Mapping[str, object], destination: Path) -> Path:
    """Visualize the screen grounding/transposition states to be simulated."""
    _style()
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    cases = cable_bonding_cases(config)
    columns = ("grounded_sending", "grounded_receiving", "cross_bonded")
    labels = ("Grounded\nat sending end", "Grounded\nat receiving end", "Cross-bonded\nsections")
    values = np.asarray([[float(case[column]) for column in columns] for case in cases])
    figure, axis = plt.subplots(figsize=(9.0, 4.8), constrained_layout=True)
    image = axis.imshow(values, cmap="Blues", vmin=0.0, vmax=1.0, aspect="auto")
    del image
    for row in range(values.shape[0]):
        for column in range(values.shape[1]):
            axis.text(
                column,
                row,
                "YES" if values[row, column] else "NO",
                ha="center",
                va="center",
                color="white" if values[row, column] else "#333333",
                fontweight="bold",
            )
    axis.set_xticks(range(len(columns)), labels)
    axis.set_yticks(range(len(cases)), [str(case["label"]) for case in cases])
    axis.set_title("Study 02 metallic-screen bonding scenario matrix")
    axis.set_xlabel("Topology state to be implemented in the PowerFactory cable system")
    axis.grid(False)
    figure.savefig(output, bbox_inches="tight")
    plt.close(figure)
    return output


def plot_cable_scenario_coverage(config: Mapping[str, object], destination: Path) -> Path:
    """Show the deterministic bonding-by-angle execution matrix and event timing."""
    _style()
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    scenarios = cable_scenarios(config)
    bonding_cases = cable_bonding_cases(config)
    angles = [float(value) % 360.0 for value in config["sweep"]["angles_deg"]]  # type: ignore[index]
    matrix = np.arange(1, len(scenarios) + 1, dtype=float).reshape(
        len(bonding_cases), len(angles)
    )
    topology_groups = np.repeat(
        np.arange(len(bonding_cases), dtype=float)[:, np.newaxis], len(angles), axis=1
    )

    figure, axes = plt.subplots(
        1,
        2,
        figsize=(12.0, 4.9),
        gridspec_kw={"width_ratios": (1.7, 1.0)},
        constrained_layout=True,
    )
    axes[0].imshow(
        topology_groups,
        cmap=ListedColormap(("#0072B2", "#D55E00", "#009E73", "#6A3D9A")),
        vmin=-0.5,
        vmax=3.5,
        aspect="auto",
    )
    for row in range(matrix.shape[0]):
        for column in range(matrix.shape[1]):
            axes[0].text(
                column,
                row,
                "#{:02.0f}".format(matrix[row, column]),
                ha="center",
                va="center",
                color="white",
                fontweight="bold",
            )
    axes[0].set_xticks(range(len(angles)), ["{:g}".format(value) for value in angles])
    axes[0].set_yticks(
        range(len(bonding_cases)), [str(case["label"]) for case in bonding_cases]
    )
    axes[0].set_xlabel("Phase-A switching angle [degrees]")
    axes[0].set_title("24 scheduled cases")
    axes[0].grid(False)

    first_bonding = scenarios[: len(angles)]
    axes[1].plot(
        [scenario.switching_angle_deg for scenario in first_bonding],
        [scenario.switching_time_s * 1e3 for scenario in first_bonding],
        marker="o",
        color="#D55E00",
    )
    axes[1].set_xlabel("Phase-A switching angle [degrees]")
    axes[1].set_ylabel("Absolute breaker event time [ms]")
    axes[1].set_title("Angle-to-time conversion at 50 Hz")
    axes[1].text(
        0.04,
        0.96,
        "Each column is repeated for\nall four bonding topologies.",
        transform=axes[1].transAxes,
        va="top",
        bbox={"boxstyle": "round,pad=0.4", "facecolor": "#F4F6F7", "edgecolor": "#AAB7B8"},
    )
    figure.suptitle("Study 02 execution matrix — planned scenarios, not EMT results", fontsize=13)
    figure.savefig(output, bbox_inches="tight")
    plt.close(figure)
    return output


def generate_cable_design_figures(
    config: Mapping[str, object], destination: Path
) -> Dict[str, Path]:
    """Generate all versionable Study 02 engineering-basis figures."""
    output = Path(destination)
    return {
        "parameters": plot_cable_parameter_overview(config, output / "parameter_overview.png"),
        "length_sensitivity": plot_cable_length_sensitivity(
            config, output / "length_sensitivity.png"
        ),
        "bonding_matrix": plot_bonding_matrix(config, output / "bonding_matrix.png"),
        "scenario_coverage": plot_cable_scenario_coverage(
            config, output / "scenario_coverage.png"
        ),
    }
