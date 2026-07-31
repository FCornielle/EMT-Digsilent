"""Shared PowerFactory builder primitives."""

from __future__ import annotations

from typing import Any, Dict

from pfemt.errors import PowerFactoryExecutionError
from pfemt.pfapi import create_or_get, set_attribute


def connect(element: Any, terminal: Any, side: str, name: str) -> Any:
    """Connect an element side to a terminal through an idempotent cubicle."""
    cubicle = create_or_get(terminal, "StaCubic", name)
    set_attribute(element, side, cubicle)
    return cubicle


def create_or_activate_project(app: Any, project_name: str, grid_name: str) -> Any:
    """Create a project once, or activate the existing project on later runs."""
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
    code = app.ActivateProject(project_name)
    if code not in (None, 0):
        raise PowerFactoryExecutionError("New project could not be activated")
    return project


def grid(app: Any, grid_name: str) -> Any:
    """Resolve exactly one project grid by its stable API name."""
    grids = list(app.GetCalcRelevantObjects("{}.ElmNet".format(grid_name)) or [])
    if len(grids) != 1:
        folder = app.GetProjectFolder("netmod", 1)
        grids = list(folder.GetContents("{}.ElmNet".format(grid_name), 1) or [])
    if len(grids) != 1:
        raise PowerFactoryExecutionError(
            "Expected one grid {!r}; found {}".format(grid_name, len(grids))
        )
    return grids[0]


def study_case(app: Any, name: str) -> Dict[str, Any]:
    """Create and activate the shared EMT Study Case command set."""
    folder = app.GetProjectFolder("study", 1)
    case = create_or_get(folder, "IntCase", name)
    active = app.GetActiveStudyCase()
    is_active = active is not None and active.GetFullName() == case.GetFullName()
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
