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
        "> Automatically generated engineering report. Values are valid only for",
        "> the recorded model version, parameters, and scenario.",
        "",
        "## Executive summary",
        "",
        "- Maximum overvoltage: **{:.3f} pu** ({:.2f} kV phase-ground peak).".format(
            float(metrics["voltage_peak_pu"]), float(metrics["voltage_kv_peak"])
        ),
        "- Voltage-peak time: **{:.6f} s**.".format(
            float(metrics["voltage_kv_peak_time_s"])
        ),
        "- Maximum closing current: **{:.3f} kA peak**.".format(
            float(metrics["current_ka_peak"])
        ),
        "",
        "## System under study",
        "",
        "- Nominal voltage: {} kV line-line RMS.".format(network["nominal_voltage_kv"]),  # type: ignore[index]
        "- Line length: {} km.".format(network["line"]["length_km"]),  # type: ignore[index]
        "- Source short-circuit power: {} MVA.".format(  # type: ignore[index]
            network["source"]["short_circuit_mva"]  # type: ignore[index]
        ),
        "- EMT time step: {} us; output step: {} us.".format(
            float(simulation["step_s"]) * 1e6,  # type: ignore[index]
            float(simulation["output_step_s"]) * 1e6,  # type: ignore[index]
        ),
        "",
        "## Method",
        "",
        "1. Activate the versioned project and Study Case.",
        "2. Configure the distributed, frequency-dependent line model.",
        "3. Apply the three-pole breaker-closing event at the requested point on wave.",
        "4. Run EMT initial conditions and time-domain simulation.",
        "5. Export instantaneous Vabc/Iabc channels through ElmRes and ComRes.",
        "6. Normalize the CSV, calculate peak metrics, and compare the regression baseline.",
        "",
    ]
    if diagram_figure:
        lines.extend(
            [
                "## PowerFactory single-line diagram",
                "",
                "![PowerFactory single-line diagram]({})".format(relative(diagram_figure)),
                "",
            ]
        )
    if waveform_figure:
        lines.extend(
            [
                "## EMT waveforms",
                "",
                "![EMT waveforms]({})".format(relative(waveform_figure)),
                "",
            ]
        )
    lines.extend(
        [
            "## Interpretation",
            "",
            "The per-unit voltage uses nominal phase-ground peak as its base:",
            r"$V_{base,peak}=V_{LL,rms}\sqrt{2/3}$.",
            "The result must be assessed against project-specific insulation coordination,",
            "parameter tolerances, switching statistics, and surge-arrester performance.",
            "",
            "## Traceability",
            "",
            "- Study: `{}`.".format(study["id"]),  # type: ignore[index]
            "- Simulation mode: instantaneous EMT (`{}`).".format(simulation["mode_code"]),  # type: ignore[index]
            "- Configuration file: `{}`.".format(config.get("_meta", {}).get("path", "n/a")),  # type: ignore[union-attr]
            "",
        ]
    )
    output.write_text("\n".join(lines), encoding="utf-8")
    return output
