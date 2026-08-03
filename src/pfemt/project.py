"""Project and Study Case activation helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pfemt.errors import PowerFactoryExecutionError
from pfemt.pfapi import execute, object_path


def activate_project(app: Any, project_name: str) -> Any:
    """Activate a project by its exact PowerFactory name."""
    code = app.ActivateProject(project_name)
    if code not in (None, 0):
        raise PowerFactoryExecutionError(
            "Could not activate project {!r}; return code {}".format(project_name, code)
        )
    project = app.GetActiveProject()
    if project is None:
        raise PowerFactoryExecutionError(
            "Project {!r} did not become active".format(project_name)
        )
    return project


def activate_study_case(app: Any, study_case_name: str) -> Any:
    """Activate a Study Case below the active project."""
    folder = app.GetProjectFolder("study")
    if folder is None:
        raise PowerFactoryExecutionError("Active project has no Study Cases folder")
    matches = list(folder.GetContents("{}.IntCase".format(study_case_name)) or [])
    if len(matches) != 1:
        raise PowerFactoryExecutionError(
            "Expected Study Case {!r}; found {}".format(study_case_name, len(matches))
        )
    active = app.GetActiveStudyCase()
    is_active = (
        active is not None
        and active.GetFullName() == matches[0].GetFullName()
    )
    if not is_active:
        code = matches[0].Activate()
        if code not in (None, 0):
            raise PowerFactoryExecutionError(
                "Could not activate Study Case {!r}; return code {}".format(
                    study_case_name, code
                )
            )
    return matches[0]


def _set_transfer_attribute(command: Any, name: str, value: Any) -> None:
    """Set a ComPfdexport transfer attribute across Python API variants."""
    setter = getattr(command, "SetAttribute", None)
    if not callable(setter):
        raise PowerFactoryExecutionError(
            "{} does not expose SetAttribute()".format(object_path(command))
        )
    errors = []
    for candidate in (name, "e:{}".format(name)):
        try:
            code = setter(candidate, value)
            if code in (None, 0):
                return
            errors.append("{} returned {}".format(candidate, code))
        except Exception as exc:
            errors.append("{}: {}".format(candidate, exc))
    raise PowerFactoryExecutionError(
        "Could not set {} on {} ({})".format(name, object_path(command), "; ".join(errors))
    )


def export_powerfactory_project(
    app: Any,
    project: Any,
    destination: Path,
    reactivate: bool = True,
) -> Path:
    """Export one inactive PowerFactory project to an atomic ``.pfd`` archive."""
    output = Path(destination).expanduser().resolve()
    if output.suffix.casefold() != ".pfd":
        raise PowerFactoryExecutionError(
            "PowerFactory project archive must use the .pfd extension: {}".format(output)
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name("{}.partial.pfd".format(output.stem))
    if temporary.exists():
        temporary.unlink()

    project_name = str(getattr(project, "loc_name", ""))
    active = app.GetActiveProject()
    should_reactivate = active is not None and reactivate
    active_name = str(getattr(active, "loc_name", project_name))
    if active is not None:
        deactivate = getattr(active, "Deactivate", None)
        if not callable(deactivate):
            raise PowerFactoryExecutionError(
                "Active project {!r} does not expose Deactivate()".format(active_name)
            )
        code = deactivate()
        if code not in (None, 0):
            raise PowerFactoryExecutionError(
                "Could not deactivate project {!r} before PFD export; return code {}".format(
                    active_name, code
                )
            )

    command = None
    try:
        user = app.GetCurrentUser()
        command = user.CreateObject("ComPfdexport", "PFEMT Project Archive")
        if command is None:
            raise PowerFactoryExecutionError("Could not create ComPfdexport command")
        _set_transfer_attribute(command, "g_objects", [project])
        _set_transfer_attribute(command, "g_file", str(temporary))
        execute(command, "PowerFactory PFD project export")
        if not temporary.is_file() or temporary.stat().st_size == 0:
            raise PowerFactoryExecutionError(
                "PowerFactory completed the PFD export but did not create {}".format(temporary)
            )
        temporary.replace(output)
    finally:
        if command is not None:
            delete = getattr(command, "Delete", None)
            if callable(delete):
                delete()
        if should_reactivate:
            code = app.ActivateProject(active_name)
            if code not in (None, 0):
                raise PowerFactoryExecutionError(
                    "PFD was exported, but project {!r} could not be reactivated".format(
                        active_name
                    )
                )
    return output
