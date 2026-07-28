"""Traceable Markdown report generation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping, Optional


def write_metrics(metrics: Mapping[str, object], destination: Path) -> Path:
    """Write deterministic JSON engineering metrics."""
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as stream:
        json.dump(dict(metrics), stream, indent=2, sort_keys=True, ensure_ascii=False)
        stream.write("\n")
    return output


def line_energization_report(
    config: Mapping[str, object],
    metrics: Mapping[str, object],
    destination: Path,
    waveform_figure: Optional[Path] = None,
    diagram_figure: Optional[Path] = None,
) -> Path:
    """Build a compact study report with assumptions, KPIs and provenance."""
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    study = config["study"]  # type: ignore[index]
    network = config["network"]  # type: ignore[index]
    simulation = config["simulation"]  # type: ignore[index]

    def relative(path: Optional[Path]) -> str:
        if path is None:
            return ""
        try:
            return str(Path(path).resolve().relative_to(output.parent.resolve())).replace("\\", "/")
        except ValueError:
            return str(Path(path).resolve()).replace("\\", "/")

    lines = [
        "# {}".format(study["title"]),  # type: ignore[index]
        "",
        "> Reporte generado automáticamente. Los valores son válidos únicamente para",
        "> la versión del modelo, parámetros y escenarios registrados en este caso.",
        "",
        "## Resumen ejecutivo",
        "",
        "- Sobretensión máxima: **{:.3f} pu** ({:.2f} kV pico fase-tierra).".format(
            float(metrics["voltage_peak_pu"]), float(metrics["voltage_kv_peak"])
        ),
        "- Instante del pico de tensión: **{:.6f} s**.".format(
            float(metrics["voltage_kv_peak_time_s"])
        ),
        "- Corriente máxima de cierre: **{:.3f} kA pico**.".format(
            float(metrics["current_ka_peak"])
        ),
        "",
        "## Sistema estudiado",
        "",
        "- Tensión nominal: {} kV RMS línea-línea.".format(network["nominal_voltage_kv"]),  # type: ignore[index]
        "- Longitud de línea: {} km.".format(network["line"]["length_km"]),  # type: ignore[index]
        "- Potencia de cortocircuito de la fuente: {} MVA.".format(  # type: ignore[index]
            network["source"]["short_circuit_mva"]  # type: ignore[index]
        ),
        "- Paso EMT: {} μs; paso de salida: {} μs.".format(
            float(simulation["step_s"]) * 1e6,  # type: ignore[index]
            float(simulation["output_step_s"]) * 1e6,  # type: ignore[index]
        ),
        "",
    ]
    if diagram_figure:
        lines.extend(
            [
                "## Diagrama unifilar",
                "",
                "![Diagrama unifilar]({})".format(relative(diagram_figure)),
                "",
            ]
        )
    if waveform_figure:
        lines.extend(
            [
                "## Resultados EMT",
                "",
                "![Formas de onda]({})".format(relative(waveform_figure)),
                "",
            ]
        )
    lines.extend(
        [
            "## Criterio de interpretación",
            "",
            "La tensión en pu se refiere al valor pico fase-tierra nominal:",
            r"$V_{base,pico}=V_{LL,rms}\sqrt{2/3}$.",
            "El resultado debe contrastarse con la coordinación de aislamiento específica",
            "del proyecto, las tolerancias de parámetros y el desempeño de descargadores.",
            "",
            "## Trazabilidad",
            "",
            "- Estudio: `{}`.".format(study["id"]),  # type: ignore[index]
            "- Modo de simulación: EMT instantáneo (`{}`).".format(simulation["mode_code"]),  # type: ignore[index]
            "- Archivo de configuración: `{}`.".format(config.get("_meta", {}).get("path", "n/a")),  # type: ignore[union-attr]
            "",
        ]
    )
    output.write_text("\n".join(lines), encoding="utf-8")
    return output
