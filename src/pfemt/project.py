"""Project and Study Case activation helpers."""

from __future__ import annotations

from typing import Any

from pfemt.errors import PowerFactoryExecutionError


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
