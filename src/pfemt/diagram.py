"""PowerFactory-native single-line diagram generation and export."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping, Sequence, Tuple

from pfemt.errors import PowerFactoryExecutionError
from pfemt.pfapi import execute, set_attribute

DIAGRAM_NAME = "EMT Line Energization 230 kV"

# Coordinates are stored in PowerFactory diagram units. They deliberately form
# a horizontal engineering one-line, rather than a presentation-only drawing.
LINE_ENERGIZATION_LAYOUT: Mapping[str, Tuple[float, float, int]] = {
    "GRID_EQUIVALENT": (20.0, 60.0, 270),
    "BUS_SENDING_230": (40.0, 60.0, 0),
    "CB_LINE_230": (60.0, 60.0, 90),
    "BUS_LINE_SIDE_230": (80.0, 60.0, 0),
    "LINE_230KV_150KM": (110.0, 60.0, 90),
    "BUS_RECEIVING_230": (140.0, 60.0, 0),
}


def _padded_points(values: Sequence[float], length: int = 20) -> list[float]:
    """Return the fixed-length point vector used by ``IntGrfcon``."""
    if len(values) > length:
        raise ValueError("A graphical connection cannot exceed {} points".format(length))
    return [float(value) for value in values] + [-1.0] * (length - len(values))


def _graphic_objects(diagram: Any) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for graphic in list(diagram.GetContents("*.IntGrf") or []):
        data_object = getattr(graphic, "pDataObj", None)
        if data_object is not None:
            result[str(data_object.loc_name)] = graphic
    return result


def _connections(graphic: Any) -> Dict[int, Any]:
    return {
        int(connection.iDatConNr): connection
        for connection in list(graphic.GetContents("*.IntGrfcon") or [])
    }


def _set_connection(connection: Any, x_values: Sequence[float], y_values: Sequence[float]) -> None:
    set_attribute(connection, "rX", _padded_points(x_values))
    set_attribute(connection, "rY", _padded_points(y_values))


def apply_line_energization_layout(diagram: Any) -> Any:
    """Apply a deterministic horizontal layout to linked PowerFactory graphics."""
    graphics = _graphic_objects(diagram)
    missing = sorted(set(LINE_ENERGIZATION_LAYOUT) - set(graphics))
    if missing:
        raise PowerFactoryExecutionError(
            "PowerFactory diagram is missing graphical objects: {}".format(missing)
        )

    for object_name, (x_coord, y_coord, rotation) in LINE_ENERGIZATION_LAYOUT.items():
        graphic = graphics[object_name]
        set_attribute(graphic, "rCenterX", x_coord)
        set_attribute(graphic, "rCenterY", y_coord)
        set_attribute(graphic, "iRot", rotation)

    source_connection = _connections(graphics["GRID_EQUIVALENT"])[0]
    _set_connection(source_connection, (24.375, 40.0), (60.0, 60.0))

    breaker_connections = _connections(graphics["CB_LINE_230"])
    _set_connection(breaker_connections[0], (57.8125, 40.0, 40.0), (60.0, 60.0, 60.0))
    _set_connection(breaker_connections[1], (62.1875, 80.0, 80.0), (60.0, 60.0, 60.0))

    line_connections = _connections(graphics["LINE_230KV_150KM"])
    _set_connection(line_connections[0], (110.0, 80.0, 80.0), (60.0, 60.0, 60.0))
    _set_connection(line_connections[1], (110.0, 140.0, 140.0), (60.0, 60.0, 60.0))

    set_attribute(diagram, "loc_name", DIAGRAM_NAME)
    for name, value in (
        ("rLBotX", 10.0),
        ("rLBotY", 45.0),
        ("rRTopX", 150.0),
        ("rRTopY", 75.0),
    ):
        set_attribute(diagram, name, value, required=False)
    return diagram


def ensure_line_energization_diagram(app: Any, grid: Any) -> Any:
    """Create, link, and arrange the native PowerFactory one-line diagram."""
    folder = app.GetProjectFolder("dia", 1)
    matches = list(folder.GetContents("{}.IntGrfnet".format(DIAGRAM_NAME), 1) or [])
    if matches:
        return apply_line_energization_layout(matches[0])

    before = {item.GetFullName() for item in list(folder.GetContents("*.IntGrfnet") or [])}
    command = app.GetFromStudyCase("ComSgllayout")
    if command is None:
        raise PowerFactoryExecutionError("The active Study Case has no Diagram Layout Tool")
    set_attribute(command, "iAction", 0)
    set_attribute(command, "pGrids", grid)
    execute(command, "PowerFactory Diagram Layout Tool")

    candidates = [
        item
        for item in list(folder.GetContents("*.IntGrfnet") or [])
        if item.GetFullName() not in before
    ]
    expected = set(LINE_ENERGIZATION_LAYOUT)
    for candidate in candidates:
        if expected.issubset(_graphic_objects(candidate)):
            return apply_line_energization_layout(candidate)
    raise PowerFactoryExecutionError(
        "Diagram Layout Tool completed but did not create the expected linked one-line diagram"
    )


def export_powerfactory_diagram(app: Any, diagram: Any, destination: Path) -> Path:
    """Export the native PowerFactory diagram currently shown on the Graphics Board.

    PowerFactory only exposes a Graphics Board from an interactive session. Run
    this function from the supplied ``ComPython`` entry point, not engine mode.
    """
    output = Path(destination).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    board = app.GetGraphicsBoard()
    if board is None:
        raise PowerFactoryExecutionError(
            "PowerFactory Graphics Board is unavailable. Run export_diagram_inside_powerfactory.py "
            "from a ComPython object in the interactive application."
        )

    pages = list(board.GetContents("*.SetDeskpage") or [])
    page = next((item for item in pages if item.loc_name == diagram.loc_name), None)
    if page is None:
        show_code = diagram.Show()
        if show_code not in (None, 0):
            raise PowerFactoryExecutionError(
                "Could not show PowerFactory diagram {!r}".format(diagram.loc_name)
            )
        board = app.GetGraphicsBoard()
        pages = list(board.GetContents("*.SetDeskpage") or [])
        page = next((item for item in pages if item.loc_name == diagram.loc_name), None)
    if page is None:
        raise PowerFactoryExecutionError(
            "Diagram {!r} is not present on the active Graphics Board".format(diagram.loc_name)
        )

    show = getattr(board, "Show", None)
    if callable(show):
        show_code = show(page)
        if show_code not in (None, 0):
            raise PowerFactoryExecutionError("Could not activate the PowerFactory diagram page")

    command = app.GetFromStudyCase("ComWr")
    if command is None:
        raise PowerFactoryExecutionError("The active Study Case has no Save File command")
    set_attribute(command, "iopt_rd", "png")
    set_attribute(command, "iopt_savas", 0)
    set_attribute(command, "f", str(output))
    set_attribute(command, "drawPageFrame", 1, required=False)
    execute(command, "PowerFactory diagram export")
    if not output.is_file() or output.stat().st_size == 0:
        raise PowerFactoryExecutionError(
            "PowerFactory completed the diagram export but did not create {}".format(output)
        )
    return output
