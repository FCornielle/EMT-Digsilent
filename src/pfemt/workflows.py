"""End-to-end study workflows used by the CLI and PowerFactory scripts."""

from __future__ import annotations

import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

import pandas as pd

from pfemt.application import connect
from pfemt.builders.line_energization import build_line_energization_model
from pfemt.config import resolve_from_config, validate_study_config
from pfemt.diagram import plot_line_energization_diagram
from pfemt.events import configure_switch_event
from pfemt.io import read_powerfactory_csv, write_normalized_csv
from pfemt.metrics import line_energization_metrics
from pfemt.pfapi import set_attribute, unique_calc_object
from pfemt.plotting import plot_line_energization, plot_sweep_summary
from pfemt.project import activate_project, activate_study_case
from pfemt.reporting import line_energization_report, write_metrics
from pfemt.results import export_csv, register_channels, result_object
from pfemt.scenarios import Scenario, export_manifest, point_on_wave_scenarios
from pfemt.simulation import configure_emt, run_emt, study_commands


def output_directory(config: Mapping[str, Any]) -> Path:
    """Resolve/create the configured output directory."""
    output = resolve_from_config(config, config["outputs"]["directory"])
    output.mkdir(parents=True, exist_ok=True)
    return output


def build(config: Mapping[str, Any], app: Optional[Any] = None) -> Dict[str, Any]:
    """Connect and build the line-energization model."""
    validate_study_config(config)
    pf_app = app or connect(config)
    objects = build_line_energization_model(pf_app, config)
    # Keep the engine-mode Application proxy alive while callers inspect the
    # returned PowerFactory objects.
    objects["application"] = pf_app
    return objects


def _prepare_active_study(app: Any, config: Mapping[str, Any]) -> Dict[str, Any]:
    activate_project(app, config["powerfactory"]["project"])
    activate_study_case(app, config["powerfactory"]["study_case"])
    initial_conditions, simulation = study_commands(app)
    configure_emt(initial_conditions, simulation, config)
    result = result_object(app)
    register_channels(app, result, config["results"]["channels"])
    return {
        "initial_conditions": initial_conditions,
        "simulation": simulation,
        "result": result,
    }


def run_scenario(
    app: Any,
    config: Mapping[str, Any],
    scenario: Scenario,
    destination: Path,
) -> Path:
    """Apply, simulate and export one switching scenario."""
    active = _prepare_active_study(app, config)
    names = config["objects"]
    source = unique_calc_object(app, "{}.ElmXnet".format(names["source"]))
    line = unique_calc_object(app, "{}.ElmLne".format(names["line"]))
    breaker = unique_calc_object(app, "{}.ElmCoup".format(names["breaker"]))
    set_attribute(source, "usetp", scenario.source_voltage_pu)
    set_attribute(line, "dline", scenario.line_length_km)
    fit_result = line.FitParams(0, 1)
    if fit_result not in (None, 0):
        raise RuntimeError("Line parameter fitting failed for {}".format(scenario.scenario_id))
    set_attribute(breaker, "on_off", 0)
    configure_switch_event(
        active["initial_conditions"],
        breaker,
        config["events"]["closing"]["name"],
        scenario.switching_time_s,
        int(config["events"]["closing"].get("action", 1)),
    )
    run_emt(active["initial_conditions"], active["simulation"])
    return export_csv(app, active["result"], destination)


def run_point_on_wave_sweep(
    config: Mapping[str, Any],
    app: Optional[Any] = None,
) -> Path:
    """Run all point-on-wave cases and write their raw CSV manifest."""
    validate_study_config(config)
    pf_app = app or connect(config)
    output = output_directory(config)
    scenarios = point_on_wave_scenarios(config)
    export_manifest(scenarios, output / "scenario_manifest.csv")
    raw = output / "raw"
    for scenario in scenarios:
        run_scenario(pf_app, config, scenario, raw / "{}.csv".format(scenario.scenario_id))
    write_run_metadata(
        config,
        output / "run_metadata.json",
        {
            "completed_utc": datetime.now(timezone.utc).isoformat(),
            "python_version": sys.version.split()[0],
            "platform": platform.platform(),
            "powerfactory_user": pf_app.GetCurrentUser().loc_name,
            "emt_licence_available": bool(pf_app.LicenceHasModule("stabemt")),
            "project": config["powerfactory"]["project"],
            "study_case": config["powerfactory"]["study_case"],
            "scenario_count": len(scenarios),
        },
    )
    return output


def analyse_csv(
    config: Mapping[str, Any],
    source_csv: Path,
    scenario: Scenario,
    destination: Optional[Path] = None,
) -> Dict[str, object]:
    """Normalize one PowerFactory CSV and generate metrics/figure/report."""
    output = destination or output_directory(config)
    frame = read_powerfactory_csv(
        source_csv,
        config["analysis"]["column_map"],
        config["analysis"].get("decimal", "."),
    )
    normalized_csv = write_normalized_csv(
        frame,
        output / "normalized" / "{}.csv".format(scenario.scenario_id),
    )
    metrics = line_energization_metrics(
        frame,
        float(config["network"]["nominal_voltage_kv"]),
        scenario.switching_time_s,
    )
    metrics = {
        "scenario_id": scenario.scenario_id,
        "switching_angle_deg": scenario.switching_angle_deg,
        "source_voltage_pu": scenario.source_voltage_pu,
        "line_length_km": scenario.line_length_km,
        **metrics,
    }
    metrics_file = write_metrics(
        metrics,
        output / "metrics" / "{}.json".format(scenario.scenario_id),
    )
    figure = plot_line_energization(
        frame,
        metrics,
        output / "figures" / "{}_waveforms.png".format(scenario.scenario_id),
        "{} — {}".format(config["study"]["title"], scenario.scenario_id),
    )
    diagram = plot_line_energization_diagram(
        config,
        output / "figures" / "single_line_diagram.png",
    )
    report = line_energization_report(
        config,
        metrics,
        output / "reports" / "{}.md".format(scenario.scenario_id),
        figure,
        diagram,
    )
    return {
        **metrics,
        "normalized_csv": str(normalized_csv),
        "metrics_file": str(metrics_file),
        "figure": str(figure),
        "report": str(report),
    }


def analyse_sweep(config: Mapping[str, Any], directory: Optional[Path] = None) -> Path:
    """Analyse every declared point-on-wave CSV and create a ranking table."""
    output = directory or output_directory(config)
    rows = []
    for scenario in point_on_wave_scenarios(config):
        raw = output / "raw" / "{}.csv".format(scenario.scenario_id)
        rows.append(analyse_csv(config, raw, scenario, output))
    summary = pd.DataFrame(rows).sort_values("voltage_peak_pu", ascending=False)
    summary_path = output / "sweep_summary.csv"
    summary.to_csv(summary_path, index=False, float_format="%.10g")
    plot_sweep_summary(summary, output / "figures" / "point_on_wave_sweep.png")
    return summary_path


def write_run_metadata(
    config: Mapping[str, Any],
    destination: Path,
    data: Mapping[str, Any],
) -> Path:
    """Persist machine-readable provenance without secrets."""
    payload = {
        "study_id": config["study"]["id"],
        "configuration": config.get("_meta", {}).get("path"),
        **dict(data),
    }
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return output
