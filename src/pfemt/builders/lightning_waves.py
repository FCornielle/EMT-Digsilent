"""PowerFactory API builder for a native impulse and distributed-line benchmark."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from pfemt.builders.common import connect, create_or_activate_project, grid, study_case
from pfemt.diagram import ensure_study_diagram
from pfemt.errors import PowerFactoryExecutionError
from pfemt.pfapi import create_or_get, set_attribute


def _line_type(app: Any, config: Mapping[str, Any]) -> Any:
    network = config["network"]
    line = network["line"]
    parameters = line["sequence_parameters"]
    line_type = create_or_get(app.GetProjectFolder("equip", 1), "TypLne", line["type_name"])
    values = {
        "uline": float(network["nominal_voltage_kv"]),
        "sline": float(line["rated_current_ka"]),
        "nlnph": 3,
        "nneutral": 0,
        "rline": float(parameters["r1_ohm_per_km"]),
        "xline": float(parameters["x1_ohm_per_km"]),
        "bline": float(parameters["b1_us_per_km"]),
        "rline0": float(parameters["r0_ohm_per_km"]),
        "xline0": float(parameters["x0_ohm_per_km"]),
        "bline0": float(parameters["b0_us_per_km"]),
        "frnom": float(network["frequency_hz"]),
    }
    for attribute, value in values.items():
        set_attribute(line_type, attribute, value)
    return line_type


def build_lightning_wave_model(app: Any, config: Mapping[str, Any]) -> Dict[str, Any]:
    """Build a phase-A native impulse feeding two 50 km distributed sections."""
    pf_config = config["powerfactory"]
    names = config["objects"]
    network = config["network"]
    line_data = network["line"]
    project = create_or_activate_project(app, pf_config["project"], pf_config["grid"])
    grid_model = grid(app, pf_config["grid"])
    line_type = _line_type(app, config)
    buses = {
        key: create_or_get(grid_model, "ElmTerm", names[key])
        for key in ("strike_bus", "midpoint_bus", "remote_bus", "reference_bus")
    }
    for bus in buses.values():
        set_attribute(bus, "uknom", float(network["nominal_voltage_kv"]))

    lines: Dict[str, Any] = {}
    for key, bus1, bus2 in (
        ("line_section_1", "strike_bus", "midpoint_bus"),
        ("line_section_2", "midpoint_bus", "remote_bus"),
    ):
        line = create_or_get(grid_model, "ElmLne", names[key])
        set_attribute(line, "typ_id", line_type)
        set_attribute(line, "dline", float(line_data["section_length_km"]))
        set_attribute(line, "i_dist", 1)
        set_attribute(line, "i_model", int(line_data["frequency_dependent_model"]))
        set_attribute(line, "fmin", float(line_data["fit_frequency_min_hz"]), required=False)
        set_attribute(line, "fmax", float(line_data["fit_frequency_max_hz"]), required=False)
        set_attribute(line, "ftau", float(line_data["main_transient_frequency_hz"]), required=False)
        connect(line, buses[bus1], "bus1", "CUB_{}_1".format(names[key]))
        connect(line, buses[bus2], "bus2", "CUB_{}_2".format(names[key]))
        if line.AreDistParamsPossible() != 0:
            raise PowerFactoryExecutionError(
                "Distributed parameters are not feasible for {}".format(names[key])
            )
        if line.FitParams(0, 1) not in (None, 0):
            raise PowerFactoryExecutionError(
                "Frequency-dependent fitting failed for {}".format(names[key])
            )
        lines[key] = line

    termination = create_or_get(grid_model, "ElmZpu", names["termination"])
    termination_data = network["termination"]
    for attribute in ("Sn", "r_pu", "x_pu", "r0_pu", "x0_pu"):
        set_attribute(termination, attribute, float(termination_data[attribute]))
    set_attribute(termination, "nphases", 3)
    connect(termination, buses["remote_bus"], "bus1", "CUB_{}_1".format(names["termination"]))
    connect(
        termination,
        buses["reference_bus"],
        "bus2",
        "CUB_{}_2".format(names["termination"]),
    )

    reference = create_or_get(grid_model, "ElmXnet", names["reference"])
    set_attribute(reference, "bustp", "SL", required=False)
    set_attribute(reference, "usetp", float(network["reference"]["voltage_pu"]))
    set_attribute(reference, "snss", float(network["reference"]["short_circuit_mva"]))
    set_attribute(reference, "rntxn", float(network["reference"]["r_over_x"]))
    connect(reference, buses["reference_bus"], "bus1", "CUB_{}".format(names["reference"]))

    impulse = create_or_get(grid_model, "ElmImpulse", names["impulse"])
    baseline = config["sweep"]["waveforms"][0]
    for attribute, value in (
        ("waveform", int(baseline["waveform_code"])),
        ("I0", float(baseline["peak_current_ka"])),
        ("k", float(baseline.get("correction_factor", 1.0))),
        ("tau1", float(baseline["front_time_us"])),
        ("tau2", float(baseline["tail_time_us"])),
        ("n", int(baseline.get("steepness_factor", 10))),
        ("Sm", float(baseline.get("maximum_steepness_ka_per_us", 0.0))),
        ("Gi", 0.0),
        ("Ci", 0.0),
    ):
        set_attribute(impulse, attribute, value)
    connect(impulse, buses["strike_bus"], "bus1", "CUB_{}".format(names["impulse"]))

    study = study_case(app, pf_config["study_case"])
    load_flow = app.GetFromStudyCase("ComLdf")
    if load_flow is None:
        load_flow = create_or_get(study["study_case"], "ComLdf", "Load Flow Calculation")
    set_attribute(load_flow, "iopt_net", 1)
    set_attribute(
        study["initial_conditions"],
        "iopt_net",
        config["simulation"]["network_representation_code"],
    )
    if not grid_model.IsCalcRelevant():
        grid_model.Activate()
    diagram = ensure_study_diagram(
        app, grid_model, config["diagram"]["name"], list(names.values())
    )
    writer = getattr(project, "WriteChangesToDb", None)
    if callable(writer):
        writer()
    return {
        "project": project,
        "grid": grid_model,
        "line_type": line_type,
        "termination": termination,
        "reference": reference,
        "impulse": impulse,
        "load_flow": load_flow,
        "diagram": diagram,
        **buses,
        **lines,
        **study,
    }
