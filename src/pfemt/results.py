"""Result-variable registration and CSV export."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping, Tuple

from pfemt.errors import PowerFactoryExecutionError
from pfemt.pfapi import execute, set_attribute, unique_calc_object

Channel = Tuple[str, str]


def result_object(app: Any) -> Any:
    """Return the result file configured in the active Study Case."""
    result = app.GetFromStudyCase("ElmRes")
    if result is None:
        initial_conditions = app.GetFromStudyCase("ComInc")
        result = getattr(initial_conditions, "p_resvar", None)
    if result is None:
        raise PowerFactoryExecutionError("The active Study Case has no ElmRes result file")
    return result


def register_channels(app: Any, result: Any, channels: Iterable[Mapping[str, str]]) -> None:
    """Clear and register result channels declared by object pattern and variable."""
    reset = getattr(app, "ResetCalculation", None)
    if callable(reset):
        reset()
    release = getattr(result, "Release", None)
    if callable(release):
        release()
    clear = getattr(result, "Clear", None)
    if callable(clear):
        clear()
    for monitor in list(result.GetContents("*.IntMon") or []):
        code = monitor.Delete()
        if code not in (None, 0):
            raise PowerFactoryExecutionError(
                "Could not remove prior result monitor {}".format(monitor.loc_name)
            )
    for channel in channels:
        obj = unique_calc_object(app, channel["object"])
        code = result.AddVariable(obj, channel["variable"])
        if code not in (None, 0):
            raise PowerFactoryExecutionError(
                "Could not register {} on {}".format(channel["variable"], channel["object"])
            )


def export_csv(app: Any, result: Any, output: Path) -> Path:
    """Export the complete ElmRes data set to a PowerFactory text/CSV file."""
    destination = Path(output).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    command = app.GetFromStudyCase("ComRes")
    if command is None:
        study_case = app.GetActiveStudyCase()
        command = study_case.CreateObject("ComRes", "Export EMT Results")
    set_attribute(command, "pResult", result)
    set_attribute(command, "f_name", str(destination))
    # PowerFactory enumeration 6 is CSV. This follows DIgSILENT's official
    # ComRes Python example rather than relying on locale-dependent ASCII mode.
    set_attribute(command, "iopt_exp", 6)
    set_attribute(command, "iopt_csel", 0)
    set_attribute(command, "iopt_tsel", 0)
    set_attribute(command, "iopt_locn", 2)
    set_attribute(command, "iopt_head", 1, required=False)
    set_attribute(command, "iopt_honly", 0, required=False)
    set_attribute(command, "iopt_sep", 1, required=False)
    execute(command, "CSV result export")
    if not destination.is_file():
        raise PowerFactoryExecutionError(
            "ComRes completed but did not create {}".format(destination)
        )
    return destination
