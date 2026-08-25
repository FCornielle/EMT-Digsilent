"""End-to-end study workflows used by the CLI and PowerFactory scripts."""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

import pandas as pd

from pfemt.application import connect
from pfemt.builders.cable_energization import (
    apply_cable_bonding_scenario,
    build_cable_energization_model,
)
from pfemt.builders.line_energization import build_line_energization_model
from pfemt.builders.transformer_energization import build_transformer_energization_model
from pfemt.cable import (
    CableScenario,
    cable_energization_metrics,
    cable_scenarios,
    export_cable_scenario_manifest,
    inactive_ground_result_channels,
)
from pfemt.cable_plotting import plot_cable_emt_waveforms, plot_cable_sweep_summary
from pfemt.config import load_yaml, resolve_from_config, validate_study_config
from pfemt.diagram import export_powerfactory_diagram
from pfemt.errors import ResultFormatError
from pfemt.events import configure_switch_event
from pfemt.io import read_powerfactory_csv, write_normalized_csv
from pfemt.metrics import (
    compare_sweep_to_baseline,
    line_energization_derived_quantities,
    line_energization_metrics,
)
from pfemt.pfapi import set_attribute, unique_calc_object
from pfemt.plotting import (
    plot_line_energization,
    plot_overvoltage_envelope,
    plot_parameter_overview,
    plot_sweep_summary,
    plot_timestep_sensitivity,
    plot_travelling_wave_detail,
)
from pfemt.project import activate_project, activate_study_case, export_powerfactory_project
from pfemt.reporting import line_energization_report, write_metrics
from pfemt.results import export_csv, register_channels, result_object
from pfemt.scenarios import Scenario, export_manifest, point_on_wave_scenarios
from pfemt.simulation import configure_emt, run_emt, study_commands
from pfemt.transformer import (
    TransformerScenario,
    export_transformer_manifest,
    transformer_energization_metrics,
    transformer_scenarios,
)
from pfemt.transformer_plotting import (
    plot_transformer_design_basis,
    plot_transformer_heatmaps,
    plot_transformer_ranking,
    plot_transformer_sweep_summary,
    plot_transformer_waveforms,
)


def output_directory(config: Mapping[str, Any]) -> Path:
    """Resolve/create the configured output directory."""
    output = resolve_from_config(config, config["outputs"]["directory"])
    output.mkdir(parents=True, exist_ok=True)
    return output


def build(config: Mapping[str, Any], app: Optional[Any] = None) -> Dict[str, Any]:
    """Connect and dispatch to the configured study model builder."""
    validate_study_config(config)
    pf_app = app or connect(config)
    study_id = str(config["study"]["id"])
    if study_id.startswith("transformer_energization"):
        objects = build_transformer_energization_model(pf_app, config)
    elif "cable" in config.get("network", {}):
        objects = build_cable_energization_model(pf_app, config)
    else:
        objects = build_line_energization_model(pf_app, config)
    # Keep the engine-mode Application proxy alive while callers inspect the
    # returned PowerFactory objects.
    objects["application"] = pf_app
    return objects


def export_diagram(config: Mapping[str, Any], app: Optional[Any] = None) -> Path:
    """Build and export the linked PowerFactory one-line diagram."""
    validate_study_config(config)
    pf_app = app or connect(config)
    study_id = str(config["study"]["id"])
    if study_id.startswith("transformer_energization"):
        objects = build_transformer_energization_model(pf_app, config)
    elif "cable" in config.get("network", {}):
        objects = build_cable_energization_model(pf_app, config)
    else:
        objects = build_line_energization_model(pf_app, config)
    return export_powerfactory_diagram(
        pf_app,
        objects["diagram"],
        output_directory(config) / "figures" / "powerfactory_single_line.png",
    )


def archive_project(config: Mapping[str, Any], app: Optional[Any] = None) -> Path:
    """Build and archive the complete PowerFactory project beside its study."""
    validate_study_config(config)
    destination = config["outputs"].get("project_archive")
    if destination:
        archive_path = resolve_from_config(config, str(destination))
    else:
        config_directory = Path(str(config.get("_meta", {}).get("directory", ".")))
        archive_path = (
            config_directory.parent
            / "powerfactory"
            / "{}.pfd".format(config["powerfactory"]["project"])
        ).resolve()
    pf_app = app or connect(config)
    objects = build(config, pf_app)
    return export_powerfactory_project(
        pf_app,
        objects["project"],
        archive_path,
    )


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


def run_cable_scenario(
    app: Any,
    config: Mapping[str, Any],
    objects: Mapping[str, Any],
    scenario: CableScenario,
    destination: Path,
) -> Path:
    """Apply one cable bonding/point-on-wave case, run EMT, and export CSV."""
    configure_emt(objects["initial_conditions"], objects["simulation"], config)
    register_channels(app, objects["result"], config["results"]["channels"])
    set_attribute(objects["source"], "usetp", scenario.source_voltage_pu)
    for line_name in ("core_line", "sheath_line"):
        set_attribute(objects[line_name], "dline", scenario.cable_length_km)
    set_attribute(objects["breaker"], "on_off", 0)
    apply_cable_bonding_scenario(objects, scenario)
    closing = config["events"]["closing"]
    configure_switch_event(
        objects["initial_conditions"],
        objects["breaker"],
        closing["name"],
        scenario.switching_time_s,
        int(closing.get("action", 1)),
    )
    run_emt(objects["initial_conditions"], objects["simulation"])
    return export_csv(app, objects["result"], destination)


def run_cable_sweep(config: Mapping[str, Any], app: Optional[Any] = None) -> Path:
    """Run the full bonding-by-point-on-wave cable campaign."""
    validate_study_config(config)
    pf_app = app or connect(config)
    objects = build_cable_energization_model(pf_app, config)
    output = output_directory(config)
    scenarios = cable_scenarios(config)
    export_cable_scenario_manifest(scenarios, output / "scenario_manifest.csv")
    raw = output / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    signature_payload = {key: value for key, value in config.items() if key != "_meta"}
    campaign_signature = hashlib.sha256(
        json.dumps(signature_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest().upper()
    checkpoint_path = raw / ".campaign_state.json"
    completed = set()
    if checkpoint_path.is_file():
        checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        if checkpoint.get("configuration_sha256") == campaign_signature:
            completed = set(checkpoint.get("completed_scenarios", []))
    try:
        for index, scenario in enumerate(scenarios, start=1):
            scenario_output = raw / "{}.csv".format(scenario.scenario_id)
            progress = "PFEMT Study 02: case {}/{} - {}".format(
                index, len(scenarios), scenario.scenario_id
            )
            if scenario.scenario_id in completed and scenario_output.is_file():
                print("{} [cached]".format(progress), flush=True)
                continue
            print(progress, flush=True)
            pf_app.PrintPlain(progress)
            run_cable_scenario(
                pf_app,
                config,
                objects,
                scenario,
                scenario_output,
            )
            completed.add(scenario.scenario_id)
            checkpoint = {
                "configuration_sha256": campaign_signature,
                "completed_scenarios": sorted(completed),
                "updated_utc": datetime.now(timezone.utc).isoformat(),
            }
            checkpoint_temporary = checkpoint_path.with_suffix(".partial.json")
            checkpoint_temporary.write_text(
                json.dumps(checkpoint, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            checkpoint_temporary.replace(checkpoint_path)
    finally:
        isolated = next(
            scenario for scenario in scenarios if scenario.bonding_id == "isolated"
        )
        apply_cable_bonding_scenario(objects, isolated)
        set_attribute(objects["breaker"], "on_off", 0)
    write_run_metadata(
        config,
        output / "run_metadata.json",
        {
            "engine": "DIgSILENT PowerFactory",
            "simulation_type": "EMT",
            "execution_status": "executed",
            "powerfactory_release": "2024 SP2",
            "completed_utc": datetime.now(timezone.utc).isoformat(),
            "python_version": sys.version.split()[0],
            "platform": platform.platform(),
            "powerfactory_user": pf_app.GetCurrentUser().loc_name,
            "project": config["powerfactory"]["project"],
            "study_case": config["powerfactory"]["study_case"],
            "scenario_count": len(scenarios),
            "campaign": "bonding_by_point_on_wave",
        },
    )
    return output


def run_transformer_scenario(
    app: Any,
    config: Mapping[str, Any],
    objects: Mapping[str, Any],
    scenario: TransformerScenario,
    destination: Path,
) -> Path:
    """Apply residual flux and point on wave, then execute one inrush case."""
    configure_emt(objects["initial_conditions"], objects["simulation"], config)
    register_channels(app, objects["result"], config["results"]["channels"])
    set_attribute(objects["source"], "usetp", scenario.source_voltage_pu)
    set_attribute(objects["breaker"], "on_off", 0)
    set_attribute(objects["transformer"], "iResFlux", 1)
    for attribute, value in (
        ("PsiresA", scenario.residual_flux_a_pu),
        ("PsiresB", scenario.residual_flux_b_pu),
        ("PsiresC", scenario.residual_flux_c_pu),
    ):
        set_attribute(objects["transformer"], attribute, value)
    closing = config["events"]["closing"]
    configure_switch_event(
        objects["initial_conditions"],
        objects["breaker"],
        closing["name"],
        scenario.switching_time_s,
        int(closing.get("action", 1)),
    )
    run_emt(objects["initial_conditions"], objects["simulation"])
    return export_csv(app, objects["result"], destination)


def run_transformer_sweep(config: Mapping[str, Any], app: Optional[Any] = None) -> Path:
    """Run the complete transformer point-on-wave by residual-flux campaign."""
    validate_study_config(config)
    pf_app = app or connect(config)
    objects = build_transformer_energization_model(pf_app, config)
    output = output_directory(config)
    scenarios = transformer_scenarios(config)
    export_transformer_manifest(scenarios, output / "scenario_manifest.csv")
    raw = output / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    signature_payload = {key: value for key, value in config.items() if key != "_meta"}
    campaign_signature = hashlib.sha256(
        json.dumps(signature_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest().upper()
    checkpoint_path = raw / ".campaign_state.json"
    completed = set()
    if checkpoint_path.is_file():
        checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        if checkpoint.get("configuration_sha256") == campaign_signature:
            completed = set(checkpoint.get("completed_scenarios", []))
    try:
        for index, scenario in enumerate(scenarios, start=1):
            destination = raw / "{}.csv".format(scenario.scenario_id)
            progress = "PFEMT Study 03: case {}/{} - {}".format(
                index, len(scenarios), scenario.scenario_id
            )
            if scenario.scenario_id in completed and destination.is_file():
                print(progress + " [cached]", flush=True)
                continue
            print(progress, flush=True)
            pf_app.PrintPlain(progress)
            run_transformer_scenario(pf_app, config, objects, scenario, destination)
            completed.add(scenario.scenario_id)
            checkpoint = {
                "configuration_sha256": campaign_signature,
                "completed_scenarios": sorted(completed),
                "updated_utc": datetime.now(timezone.utc).isoformat(),
            }
            temporary = checkpoint_path.with_suffix(".partial.json")
            temporary.write_text(
                json.dumps(checkpoint, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            temporary.replace(checkpoint_path)
    finally:
        set_attribute(objects["breaker"], "on_off", 0)
        for attribute in ("PsiresA", "PsiresB", "PsiresC"):
            set_attribute(objects["transformer"], attribute, 0.0)
    write_run_metadata(
        config,
        output / "run_metadata.json",
        {
            "engine": "DIgSILENT PowerFactory",
            "simulation_type": "EMT",
            "execution_status": "executed",
            "powerfactory_release": "2024 SP2",
            "completed_utc": datetime.now(timezone.utc).isoformat(),
            "python_version": sys.version.split()[0],
            "platform": platform.platform(),
            "powerfactory_user": pf_app.GetCurrentUser().loc_name,
            "project": config["powerfactory"]["project"],
            "study_case": config["powerfactory"]["study_case"],
            "scenario_count": len(scenarios),
            "campaign": "point_on_wave_by_residual_flux",
        },
    )
    return output


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
        "{} — phase-A close at {:.0f} degrees".format(
            config["study"]["title"], scenario.switching_angle_deg
        ),
    )
    diagram = output / "figures" / "powerfactory_single_line.png"
    report = line_energization_report(
        config,
        metrics,
        output / "reports" / "{}.md".format(scenario.scenario_id),
        figure,
        diagram if diagram.is_file() else None,
    )
    return {
        **metrics,
        "normalized_csv": str(normalized_csv),
        "metrics_file": str(metrics_file),
        "figure": str(figure),
        "report": str(report),
    }


def analyse_cable_csv(
    config: Mapping[str, Any],
    source_csv: Path,
    scenario: CableScenario,
    destination: Optional[Path] = None,
) -> Dict[str, object]:
    """Normalize and analyse one Study 02 PowerFactory CSV export."""
    output = destination or output_directory(config)
    column_map = dict(config["analysis"]["column_map"])
    zero_channels = inactive_ground_result_channels(scenario)
    for column in zero_channels:
        column_map.pop(column)
    frame = read_powerfactory_csv(
        source_csv,
        column_map,
        config["analysis"].get("decimal", "."),
    )
    for column in zero_channels:
        frame[column] = 0.0
    normalized_csv = write_normalized_csv(
        frame,
        output / "normalized" / "{}.csv".format(scenario.scenario_id),
    )
    metrics = cable_energization_metrics(
        frame,
        float(config["network"]["nominal_voltage_kv"]),
        scenario.switching_time_s,
    )
    row: Dict[str, object] = {
        "scenario_id": scenario.scenario_id,
        "bonding_id": scenario.bonding_id,
        "bonding_label": scenario.bonding_label,
        "switching_angle_deg": scenario.switching_angle_deg,
        "switching_time_s": scenario.switching_time_s,
        "grounded_sending": scenario.grounded_sending,
        "grounded_receiving": scenario.grounded_receiving,
        "cross_bonded": scenario.cross_bonded,
        **metrics,
    }
    metrics_file = write_metrics(
        row,
        output / "metrics" / "{}.json".format(scenario.scenario_id),
    )
    figure = plot_cable_emt_waveforms(
        frame,
        scenario,
        row,
        output / "figures" / "{}_waveforms.png".format(scenario.scenario_id),
    )
    return {
        **row,
        "normalized_csv": str(normalized_csv),
        "metrics_file": str(metrics_file),
        "figure": str(figure),
    }


def analyse_cable_sweep(
    config: Mapping[str, Any], directory: Optional[Path] = None
) -> Path:
    """Analyse all 24 cable cases and rank their conductor/sheath stresses."""
    output = directory or output_directory(config)
    rows = [
        analyse_cable_csv(
            config,
            output / "raw" / "{}.csv".format(scenario.scenario_id),
            scenario,
            output,
        )
        for scenario in cable_scenarios(config)
    ]
    summary = (
        pd.DataFrame(rows)
        .drop(columns=["normalized_csv", "metrics_file", "figure"])
        .sort_values("core_voltage_peak_pu", ascending=False)
    )
    destination = output / "sweep_summary.csv"
    summary.to_csv(destination, index=False, float_format="%.10g")
    plot_cable_sweep_summary(summary, output / "figures" / "bonding_pow_comparison.png")
    write_metrics(
        summary.iloc[0].to_dict(),
        output / "metrics" / "worst_case.json",
    )
    return destination


def analyse_transformer_csv(
    config: Mapping[str, Any],
    source_csv: Path,
    scenario: TransformerScenario,
    destination: Optional[Path] = None,
) -> Dict[str, object]:
    """Normalize and analyse one Study 03 PowerFactory EMT export."""
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
    metrics = transformer_energization_metrics(frame, scenario, config)
    row: Dict[str, object] = {
        "scenario_id": scenario.scenario_id,
        "switching_angle_deg": scenario.switching_angle_deg,
        "switching_time_s": scenario.switching_time_s,
        "residual_id": scenario.residual_id,
        "residual_label": scenario.residual_label,
        "residual_flux_a_pu": scenario.residual_flux_a_pu,
        "residual_flux_b_pu": scenario.residual_flux_b_pu,
        "residual_flux_c_pu": scenario.residual_flux_c_pu,
        **metrics,
    }
    metrics_file = write_metrics(
        row,
        output / "metrics" / "{}.json".format(scenario.scenario_id),
    )
    figure = plot_transformer_waveforms(
        frame,
        scenario,
        row,
        config,
        output / "figures" / "{}_waveforms.png".format(scenario.scenario_id),
    )
    return {
        **row,
        "normalized_csv": str(normalized_csv),
        "metrics_file": str(metrics_file),
        "figure": str(figure),
    }


def analyse_transformer_sweep(
    config: Mapping[str, Any], directory: Optional[Path] = None
) -> Path:
    """Analyse and rank every transformer energization scenario."""
    output = directory or output_directory(config)
    rows = [
        analyse_transformer_csv(
            config,
            output / "raw" / "{}.csv".format(scenario.scenario_id),
            scenario,
            output,
        )
        for scenario in transformer_scenarios(config)
    ]
    summary = (
        pd.DataFrame(rows)
        .drop(columns=["normalized_csv", "metrics_file", "figure"])
        .sort_values("current_peak_pu", ascending=False)
    )
    destination = output / "sweep_summary.csv"
    summary.to_csv(destination, index=False, float_format="%.10g")
    plot_transformer_sweep_summary(
        summary,
        output / "figures" / "inrush_pow_residual_comparison.png",
    )
    plot_transformer_heatmaps(summary, output / "figures" / "inrush_severity_heatmaps.png")
    plot_transformer_ranking(summary, output / "figures" / "inrush_case_ranking.png")
    plot_transformer_design_basis(config, output / "figures" / "transformer_design_basis.png")
    write_metrics(summary.iloc[0].to_dict(), output / "metrics" / "worst_case.json")
    return destination


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

    derived = line_energization_derived_quantities(config)
    write_metrics(derived, output / "validation" / "analytical_checks.json")
    plot_parameter_overview(config, derived, output / "figures" / "parameter_overview.png")

    nominal_peak = derived["nominal_phase_peak_kv"]
    aligned_rows = []
    for row in rows:
        normalized = pd.read_csv(row["normalized_csv"])
        relative_ms = (normalized["time_s"] - float(row["switching_time_s"])) * 1000.0
        mask = (relative_ms >= 0.0) & (relative_ms <= 10.0)
        voltage_envelope = (
            normalized.loc[mask, ["v_recv_a_kv", "v_recv_b_kv", "v_recv_c_kv"]]
            .abs()
            .max(axis=1)
            / nominal_peak
        )
        aligned_rows.append(
            pd.DataFrame(
                {
                    "switching_angle_deg": float(row["switching_angle_deg"]),
                    "relative_time_ms": relative_ms.loc[mask].to_numpy(),
                    "voltage_envelope_pu": voltage_envelope.to_numpy(),
                }
            )
        )
    aligned = pd.concat(aligned_rows, ignore_index=True)
    plot_overvoltage_envelope(aligned, output / "figures" / "overvoltage_envelope.png")

    worst_id = str(summary.iloc[0]["scenario_id"])
    worst = next(row for row in rows if row["scenario_id"] == worst_id)
    worst_frame = pd.read_csv(worst["normalized_csv"])
    plot_travelling_wave_detail(
        worst_frame,
        worst,
        derived["one_way_travel_time_ms"],
        output / "figures" / "travelling_wave_detail.png",
    )

    validation = config.get("validation", {})
    baseline_value = validation.get("baseline")
    if baseline_value:
        baseline_path = resolve_from_config(config, str(baseline_value))
        baseline = load_yaml(baseline_path)
        comparison = compare_sweep_to_baseline(summary, baseline)
        write_metrics(comparison, output / "validation" / "baseline_comparison.json")
        if comparison["status"] != "pass":
            raise ResultFormatError(
                "Sweep results are outside the versioned regression tolerances; "
                "inspect validation/baseline_comparison.json"
            )
    return summary_path


def run_timestep_sensitivity(
    config: Mapping[str, Any],
    app: Optional[Any] = None,
) -> Path:
    """Run the declared worst-angle case with several EMT time steps."""
    validate_study_config(config)
    settings = config["time_step_sensitivity"]
    angle = float(settings["switching_angle_deg"])
    scenarios = point_on_wave_scenarios(config)
    scenario = next(item for item in scenarios if item.switching_angle_deg == angle)
    pf_app = app or connect(config)
    build_line_energization_model(pf_app, config)
    output = output_directory(config) / "time_step_sensitivity"
    rows = []
    for step_us in settings["steps_us"]:
        study_config = deepcopy(config)
        step_s = float(step_us) * 1e-6
        study_config["simulation"]["step_s"] = step_s
        study_config["simulation"]["output_step_s"] = step_s
        raw = run_scenario(
            pf_app,
            study_config,
            scenario,
            output / "raw" / "step_{:g}us.csv".format(float(step_us)),
        )
        frame = read_powerfactory_csv(
            raw,
            config["analysis"]["column_map"],
            config["analysis"].get("decimal", "."),
        )
        metrics = line_energization_metrics(
            frame,
            float(config["network"]["nominal_voltage_kv"]),
            scenario.switching_time_s,
        )
        rows.append(
            {
                "time_step_us": float(step_us),
                "switching_angle_deg": angle,
                "voltage_peak_pu": float(metrics["voltage_peak_pu"]),
                "voltage_peak_kv": float(metrics["voltage_kv_peak"]),
                "current_ka_peak": float(metrics["current_ka_peak"]),
            }
        )
    summary = pd.DataFrame(rows).sort_values("time_step_us")
    destination = output / "timestep_sensitivity.csv"
    destination.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(destination, index=False, float_format="%.10g")
    plot_timestep_sensitivity(summary, output / "timestep_sensitivity.png")
    return destination


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
