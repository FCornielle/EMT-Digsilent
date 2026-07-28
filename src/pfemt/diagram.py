"""Configuration-driven one-line diagram rendering."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle


def plot_line_energization_diagram(config: Mapping[str, object], destination: Path) -> Path:
    """Render the study topology used by the PowerFactory builder."""
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    network = config["network"]  # type: ignore[index]
    voltage_kv = float(network["nominal_voltage_kv"])  # type: ignore[index]
    length_km = float(network["line"]["length_km"])  # type: ignore[index]
    short_circuit_mva = float(network["source"]["short_circuit_mva"])  # type: ignore[index]

    figure, axis = plt.subplots(figsize=(11.0, 3.5), constrained_layout=True)
    axis.set_xlim(0, 11)
    axis.set_ylim(-1.8, 1.8)
    axis.axis("off")

    axis.add_patch(Circle((0.8, 0), 0.42, fill=False, linewidth=2, color="#333333"))
    axis.text(0.8, 0, "~", ha="center", va="center", fontsize=20)
    axis.text(
        0.8,
        -0.75,
        "Red equivalente\n{:.0f} MVA".format(short_circuit_mva),
        ha="center",
        va="top",
    )

    axis.plot([1.22, 2.0], [0, 0], color="#333333", linewidth=2)
    axis.plot([2.0, 2.0], [-0.65, 0.65], color="#0072B2", linewidth=5)
    axis.text(2.0, 0.92, "BUS ENVÍO\n{:.0f} kV".format(voltage_kv), ha="center")

    axis.plot([2.0, 3.25], [0, 0], color="#333333", linewidth=2)
    axis.plot([3.25, 3.55], [0, 0.25], color="#D55E00", linewidth=2)
    axis.plot([3.55, 3.85], [0, 0], color="#333333", linewidth=2)
    axis.add_patch(Rectangle((3.13, -0.32), 0.84, 0.64, fill=False, linestyle=":", color="#777777"))
    axis.text(3.55, -0.72, "CB-LINE\ncierre PoW", ha="center", va="top")

    axis.plot([3.85, 7.75], [0, 0], color="#333333", linewidth=2)
    axis.plot(
        [4.5, 4.8, 5.1, 5.4, 5.7, 6.0, 6.3, 6.6, 6.9, 7.2],
        [0, 0.18, -0.18, 0.18, -0.18, 0.18, -0.18, 0.18, -0.18, 0],
        color="#009E73",
        linewidth=2,
    )
    axis.text(5.85, 0.68, "Línea aérea {:.0f} km".format(length_km), ha="center")
    axis.text(5.85, -0.72, "Modelo EMT distribuido / dependiente de frecuencia", ha="center")

    axis.plot([7.75, 8.7], [0, 0], color="#333333", linewidth=2)
    axis.plot([8.7, 8.7], [-0.65, 0.65], color="#0072B2", linewidth=5)
    axis.text(8.7, 0.92, "BUS RECEPCIÓN\nextremo abierto", ha="center")
    axis.plot([8.7, 9.72], [0, 0], color="#777777", linewidth=1.2, linestyle=":")
    axis.add_patch(Circle((10.0, 0), 0.28, fill=False, linewidth=1.6, color="#555555"))
    axis.text(10.0, 0, "V", ha="center", va="center", fontsize=10)
    axis.text(10.0, 0.52, "Medición Vabc", ha="center")
    axis.set_title("Caso industrial: energización de línea de transmisión")
    figure.savefig(output, bbox_inches="tight")
    plt.close(figure)
    return output
