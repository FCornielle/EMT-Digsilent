"""Command-line entry point for the EMT study repository."""

from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path
from typing import Optional, Sequence

from pfemt.application import installation_report
from pfemt.cable import cable_scenarios, export_cable_scenario_manifest
from pfemt.capacitor import capacitor_scenarios, export_capacitor_manifest
from pfemt.config import load_yaml, validate_study_config
from pfemt.errors import PFEMTError
from pfemt.faults import export_fault_manifest, fault_scenarios
from pfemt.saturation import export_saturation_manifest, saturation_scenarios
from pfemt.scenarios import export_manifest, point_on_wave_scenarios
from pfemt.transformer import export_transformer_manifest, transformer_scenarios
from pfemt.workflows import (
    analyse_cable_sweep,
    analyse_capacitor_sweep,
    analyse_fault_sweep,
    analyse_saturation_sweep,
    analyse_sweep,
    analyse_transformer_sweep,
    archive_project,
    build,
    export_diagram,
    output_directory,
    run_cable_sweep,
    run_capacitor_sweep,
    run_fault_sweep,
    run_point_on_wave_sweep,
    run_saturation_sweep,
    run_timestep_sensitivity,
    run_transformer_sweep,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pfemt",
        description="Reproducible industrial EMT studies with PowerFactory",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    doctor = subcommands.add_parser("doctor", help="Inspect Python and PowerFactory installation")
    doctor.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    for name, help_text in (
        ("validate", "Validate a study YAML"),
        ("build", "Build the PowerFactory project through the API"),
        ("sweep", "Run the complete point-on-wave sweep"),
        ("analyse", "Analyse all exported sweep CSV files"),
        ("diagram", "Export the native PowerFactory one-line diagram"),
        ("archive", "Build and export the PowerFactory project as a PFD archive"),
        ("manifest", "Generate the deterministic scenario manifest"),
        ("sensitivity", "Run the configured EMT time-step sensitivity"),
    ):
        command = subcommands.add_parser(name, help=help_text)
        command.add_argument("config", type=Path)
    return parser


def _doctor(as_json: bool) -> int:
    report = {
        "python": sys.version.split()[0],
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "powerfactory_installations": installation_report(),
    }
    if as_json:
        print(json.dumps(report, indent=2))
    else:
        print("Python: {} ({})".format(report["python"], report["python_executable"]))
        if report["powerfactory_installations"]:
            for item in report["powerfactory_installations"]:
                print("PowerFactory: {home} | module: {python_module}".format(**item))
        else:
            print("PowerFactory: no compatible installation found")
    return 0 if report["powerfactory_installations"] else 1


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the CLI and return a shell-compatible status code."""
    arguments = _parser().parse_args(argv)
    try:
        if arguments.command == "doctor":
            return _doctor(arguments.json)
        config = load_yaml(arguments.config)
        validate_study_config(config)
        if arguments.command == "validate":
            print("Valid configuration: {}".format(arguments.config.resolve()))
        elif arguments.command == "build":
            objects = build(config)
            print("PowerFactory model ready: {}".format(objects["project"].loc_name))
        elif arguments.command == "sweep":
            study_id = str(config["study"]["id"])
            if study_id.startswith("transformer_saturation_sensitivity"):
                print(run_saturation_sweep(config))
            elif study_id.startswith(("circuit_breaker_trv", "faults_variable_clearing")):
                print(run_fault_sweep(config))
            elif study_id.startswith("capacitor_bank_energization"):
                print(run_capacitor_sweep(config))
            elif study_id.startswith("transformer_energization"):
                print(run_transformer_sweep(config))
            elif "cable" in config["network"]:
                print(run_cable_sweep(config))
            else:
                print(run_point_on_wave_sweep(config))
        elif arguments.command == "analyse":
            study_id = str(config["study"]["id"])
            if study_id.startswith("transformer_saturation_sensitivity"):
                print(analyse_saturation_sweep(config))
            elif study_id.startswith(("circuit_breaker_trv", "faults_variable_clearing")):
                print(analyse_fault_sweep(config))
            elif study_id.startswith("capacitor_bank_energization"):
                print(analyse_capacitor_sweep(config))
            elif study_id.startswith("transformer_energization"):
                print(analyse_transformer_sweep(config))
            elif "cable" in config["network"]:
                print(analyse_cable_sweep(config))
            else:
                print(analyse_sweep(config))
        elif arguments.command == "diagram":
            print(export_diagram(config))
        elif arguments.command == "archive":
            print(archive_project(config))
        elif arguments.command == "manifest":
            destination = output_directory(config) / "scenario_manifest.csv"
            study_id = str(config["study"]["id"])
            if study_id.startswith("transformer_saturation_sensitivity"):
                print(export_saturation_manifest(saturation_scenarios(config), destination))
            elif study_id.startswith(("circuit_breaker_trv", "faults_variable_clearing")):
                print(export_fault_manifest(fault_scenarios(config), destination))
            elif study_id.startswith("capacitor_bank_energization"):
                print(export_capacitor_manifest(capacitor_scenarios(config), destination))
            elif study_id.startswith("transformer_energization"):
                print(export_transformer_manifest(transformer_scenarios(config), destination))
            elif "cable" in config["network"]:
                print(export_cable_scenario_manifest(cable_scenarios(config), destination))
            else:
                print(export_manifest(point_on_wave_scenarios(config), destination))
        elif arguments.command == "sensitivity":
            print(run_timestep_sensitivity(config))
        return 0
    except (PFEMTError, KeyError, ValueError) as exc:
        print("ERROR: {}".format(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
