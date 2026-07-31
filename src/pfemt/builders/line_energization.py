"""API builder for the 230 kV line-energization benchmark."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from pfemt.diagram import ensure_line_energization_diagram
from pfemt.errors import PowerFactoryExecutionError
from pfemt.pfapi import create_or_get, set_attribute


def _connect(element: Any, terminal: Any, side: str, name: str) -> Any:
    cubicle = create_or_get(terminal, "StaCubic", name)
    set_attribute(element, side, cubicle)
    return cubicle


def _create_or_activate_project(app: Any, project_name: str, grid_name: str) -> Any:
    user = app.GetCurrentUser()
    existing = list(user.GetContents("{}.IntPrj".format(project_name)) or [])
    if existing:
        code = app.ActivateProject(project_name)
        if code not in (None, 0):
            raise PowerFactoryExecutionError(
                "Could not activate existing project {!r}".format(project_name)
            )
        return existing[0]
    project = app.CreateProject(project_name, grid_name)
    if project is None:
        raise PowerFactoryExecutionError(
            "Application.CreateProject could not create {!r}".format(project_name)
        )
    # Application.ActivateProject is more reliable in engine mode than invoking
    # IntPrj.Activate immediately after Application.CreateProject.
    code = app.ActivateProject(project_name)
    if code not in (None, 0):
        raise PowerFactoryExecutionError("New project could not be activated")
    return project


def _grid(app: Any, grid_name: str) -> Any:
    grids = list(app.GetCalcRelevantObjects("{}.ElmNet".format(grid_name)) or [])
    if len(grids) != 1:
        folder = app.GetProjectFolder("netmod", 1)
        direct = list(folder.GetContents("{}.ElmNet".format(grid_name), 1) or [])
        grids = direct
    if len(grids) != 1:
        raise PowerFactoryExecutionError(
            "Expected one grid {!r}; found {}".format(grid_name, len(grids))
        )
    return grids[0]


def _line_type(app: Any, config: Mapping[str, Any]) -> Any:
    network = config["network"]
    line_data = network["line"]
    parameters = line_data["sequence_parameters"]
    folder = app.GetProjectFolder("equip", 1)
    line_type = create_or_get(folder, "TypLne", line_data["type_name"])
    values = {
        "uline": float(network["nominal_voltage_kv"]),
        "sline": float(line_data["rated_current_ka"]),
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
    for name, value in values.items():
        set_attribute(line_type, name, value)
    return line_type


def _study_case(app: Any, name: str) -> Dict[str, Any]:
    folder = app.GetProjectFolder("study", 1)
    case = create_or_get(folder, "IntCase", name)
    active = app.GetActiveStudyCase()
    is_active = (
        active is not None
        and active.GetFullName() == case.GetFullName()
    )
    if not is_active:
        code = case.Activate()
        if code not in (None, 0):
            raise PowerFactoryExecutionError(
                "Could not activate Study Case {!r}".format(name)
            )
    result = create_or_get(case, "ElmRes", "EMT Results")
    events = create_or_get(case, "IntEvt", "Simulation Events")
    initial_conditions = create_or_get(case, "ComInc", "Initial Conditions - EMT")
    simulation = create_or_get(case, "ComSim", "Run EMT Simulation")
    export = create_or_get(case, "ComRes", "Export EMT Results")
    set_attribute(initial_conditions, "p_resvar", result)
    set_attribute(initial_conditions, "p_event", events)
    set_attribute(export, "pResult", result)
    return {
        "study_case": case,
        "result": result,
        "events": events,
        "initial_conditions": initial_conditions,
        "simulation": simulation,
        "export": export,
    }


def build_line_energization_model(app: Any, config: Mapping[str, Any]) -> Dict[str, Any]:
    """Build or update the complete network and Study Case through the API.

    The supplied benchmark uses sequence parameters in ``TypLne`` for portability.
    For an insulation-coordination deliverable, replace this type with the actual
    tower/conductor geometry and soil-resistivity data, as recommended by DIgSILENT.
    """
    pf_config = config["powerfactory"]
    names = config["objects"]
    network = config["network"]
    source_data = network["source"]
    line_data = network["line"]

    project = _create_or_activate_project(
        app,
        pf_config["project"],
        pf_config["grid"],
    )
    grid = _grid(app, pf_config["grid"])
    line_type = _line_type(app, config)

    sending = create_or_get(grid, "ElmTerm", names["sending_bus"])
    line_side = create_or_get(grid, "ElmTerm", names["line_bus"])
    receiving = create_or_get(grid, "ElmTerm", names["receiving_bus"])
    for terminal in (sending, line_side, receiving):
        set_attribute(terminal, "uknom", float(network["nominal_voltage_kv"]))

    source = create_or_get(grid, "ElmXnet", names["source"])
    set_attribute(source, "bustp", "SL", required=False)
    set_attribute(source, "usetp", float(source_data["voltage_pu"]))
    set_attribute(source, "snss", float(source_data["short_circuit_mva"]))
    set_attribute(source, "rntxn", float(source_data["r_over_x"]))
    set_attribute(source, "xntrn", float(source_data.get("x0_over_x1", 1.0)), required=False)
    set_attribute(source, "r0tx0", float(source_data.get("r0_over_x0", 0.1)), required=False)
    _connect(source, sending, "bus1", "CUB_{}".format(names["source"]))

    breaker = create_or_get(grid, "ElmCoup", names["breaker"])
    set_attribute(breaker, "on_off", 0)
    _connect(breaker, sending, "bus1", "CUB_{}_1".format(names["breaker"]))
    _connect(breaker, line_side, "bus2", "CUB_{}_2".format(names["breaker"]))

    line = create_or_get(grid, "ElmLne", names["line"])
    set_attribute(line, "typ_id", line_type)
    set_attribute(line, "dline", float(line_data["length_km"]))
    set_attribute(line, "i_dist", 1)
    set_attribute(line, "i_model", int(line_data.get("frequency_dependent_model", 1)))
    set_attribute(line, "fmin", float(line_data.get("fit_frequency_min_hz", 10.0)), required=False)
    set_attribute(
        line,
        "fmax",
        float(line_data.get("fit_frequency_max_hz", 10000.0)),
        required=False,
    )
    set_attribute(
        line,
        "ftau",
        float(line_data.get("main_transient_frequency_hz", 1000.0)),
        required=False,
    )
    _connect(line, line_side, "bus1", "CUB_{}_1".format(names["line"]))
    _connect(line, receiving, "bus2", "CUB_{}_2".format(names["line"]))

    feasibility = line.AreDistParamsPossible()
    if feasibility != 0:
        raise PowerFactoryExecutionError(
            "Distributed line parameters are not feasible; AreDistParamsPossible={}".format(
                feasibility
            )
        )
    fit_result = line.FitParams(0, 1)
    if fit_result not in (None, 0):
        raise PowerFactoryExecutionError(
            "Frequency-dependent line parameter fitting failed: {}".format(fit_result)
        )

    study = _study_case(app, pf_config["study_case"])
    if not grid.IsCalcRelevant():
        grid_code = grid.Activate()
        if grid_code not in (None, 0):
            raise PowerFactoryExecutionError(
                "Could not activate grid {!r} in Study Case {!r}".format(
                    pf_config["grid"],
                    pf_config["study_case"],
                )
            )
    diagram = ensure_line_energization_diagram(app, grid)
    writer = getattr(project, "WriteChangesToDb", None)
    if callable(writer):
        writer()
    return {
        "project": project,
        "grid": grid,
        "sending_bus": sending,
        "line_bus": line_side,
        "receiving_bus": receiving,
        "source": source,
        "breaker": breaker,
        "line": line,
        "line_type": line_type,
        "diagram": diagram,
        **study,
    }
