"""PowerFactory-native single-line diagram generation and export."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping, Sequence, Tuple

from pfemt.errors import PowerFactoryExecutionError
from pfemt.pfapi import execute, set_attribute

LINE_DIAGRAM_NAME = "EMT Line Energization 230 kV"
CABLE_DIAGRAM_NAME = "EMT Cable Energization 220 kV"
# Reserved name from the retired SVG overlay. The builder removes only this
# generated layer and never touches annotations or layout work created by a user.
CABLE_GENERATED_LAYER_NAME = "PFEMT Study Guide"
# Backwards-compatible public name used by Study 01 tests and scripts.
DIAGRAM_NAME = LINE_DIAGRAM_NAME

# Coordinates are stored in PowerFactory diagram units. They deliberately form
# a horizontal engineering one-line, rather than a presentation-only drawing.
LINE_ENERGIZATION_LAYOUT: Mapping[str, Tuple[float, float, int]] = {
    "GRID_EQUIVALENT": (20.0, 60.0, 270),
    "BUS_SENDING_230": (45.0, 60.0, 90),
    "CB_LINE_230": (65.0, 60.0, 90),
    "BUS_LINE_SIDE_230": (85.0, 60.0, 90),
    "LINE_230KV_150KM": (120.0, 60.0, 90),
    "BUS_RECEIVING_230": (155.0, 60.0, 90),
}

CABLE_ENERGIZATION_LAYOUT: Mapping[str, Tuple[float, float, int]] = {
    # PowerFactory's diagram y-axis is visually bottom-to-top. Use the larger
    # coordinate for the primary circuit so it appears above the sheath row.
    "GRID_EQUIVALENT": (20.0, 92.0, 270),
    "BUS_CABLE_SENDING_220": (50.0, 92.0, 90),
    "CB_CABLE_220": (78.0, 92.0, 90),
    "BUS_CABLE_LINE_SIDE_220": (108.0, 92.0, 90),
    "CABLE_CORE_220KV_40KM": (160.0, 92.0, 90),
    "BUS_CABLE_RECEIVING_220": (215.0, 92.0, 90),
    "BUS_SHEATH_SENDING_220": (108.0, 52.0, 90),
    "CABLE_SHEATH_220KV_40KM": (160.0, 52.0, 90),
    "BUS_SHEATH_RECEIVING_220": (215.0, 52.0, 90),
    "GND_SHEATH_SENDING_220": (108.0, 35.0, 0),
    "GND_SHEATH_RECEIVING_220": (215.0, 35.0, 0),
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


def _linked_diagrams_for(folder: Any, expected: set[str]) -> list[Any]:
    """Return diagrams that already represent every expected network object."""
    diagrams = list(folder.GetContents("*.IntGrfnet") or [])
    return [diagram for diagram in diagrams if expected.issubset(_graphic_objects(diagram))]


def ensure_study_diagram(
    app: Any,
    grid: Any,
    diagram_name: str,
    expected_objects: Sequence[str],
) -> Any:
    """Create a linked native diagram once and preserve later manual layout work."""
    folder = app.GetProjectFolder("dia", 1)
    expected = set(expected_objects)
    linked = _linked_diagrams_for(folder, expected)
    if linked:
        preferred = next(
            (diagram for diagram in linked if diagram.loc_name == diagram_name),
            linked[0],
        )
        return _claim_diagram_name(folder, preferred, diagram_name)

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
    candidates.extend(
        diagram for diagram in _linked_diagrams_for(folder, expected) if diagram not in candidates
    )
    for candidate in candidates:
        if expected.issubset(_graphic_objects(candidate)):
            return _claim_diagram_name(folder, candidate, diagram_name)
    raise PowerFactoryExecutionError(
        "Diagram Layout Tool did not create the expected linked diagram {!r}".format(
            diagram_name
        )
    )


def _linked_diagrams(folder: Any) -> list[Any]:
    """Return diagrams that already represent every Study 01 object."""
    return _linked_diagrams_for(folder, set(LINE_ENERGIZATION_LAYOUT))


def _claim_diagram_name(folder: Any, preferred: Any, canonical_name: str) -> Any:
    """Give the complete diagram its stable name while retaining older drawings."""
    preferred_path = preferred.GetFullName()
    for diagram in list(folder.GetContents("*.IntGrfnet") or []):
        if diagram.GetFullName() == preferred_path:
            continue
        if diagram.loc_name == canonical_name:
            set_attribute(diagram, "loc_name", "Legacy - {}".format(canonical_name))
    set_attribute(preferred, "loc_name", canonical_name)
    return preferred


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
    _set_connection(source_connection, (24.375, 45.0), (60.0, 60.0))

    breaker_connections = _connections(graphics["CB_LINE_230"])
    _set_connection(breaker_connections[0], (62.8125, 45.0, 45.0), (60.0, 60.0, 60.0))
    _set_connection(breaker_connections[1], (67.1875, 85.0, 85.0), (60.0, 60.0, 60.0))

    line_connections = _connections(graphics["LINE_230KV_150KM"])
    _set_connection(line_connections[0], (120.0, 85.0, 85.0), (60.0, 60.0, 60.0))
    _set_connection(line_connections[1], (120.0, 155.0, 155.0), (60.0, 60.0, 60.0))

    set_attribute(diagram, "loc_name", LINE_DIAGRAM_NAME)
    for name, value in (
        ("rLBotX", 10.0),
        ("rLBotY", 45.0),
        ("rRTopX", 165.0),
        ("rRTopY", 75.0),
    ):
        set_attribute(diagram, name, value, required=False)
    return diagram


def ensure_line_energization_diagram(app: Any, grid: Any) -> Any:
    """Create, link, and arrange the native PowerFactory one-line diagram."""
    folder = app.GetProjectFolder("dia", 1)
    linked = _linked_diagrams(folder)
    if linked:
        preferred = next(
            (diagram for diagram in linked if diagram.loc_name == LINE_DIAGRAM_NAME),
            linked[0],
        )
        return apply_line_energization_layout(preferred)

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
    candidates.extend(
        diagram for diagram in _linked_diagrams(folder) if diagram not in candidates
    )
    expected = set(LINE_ENERGIZATION_LAYOUT)
    for candidate in candidates:
        if expected.issubset(_graphic_objects(candidate)):
            return apply_line_energization_layout(candidate)
    raise PowerFactoryExecutionError(
        "Diagram Layout Tool completed but did not create the expected linked one-line diagram"
    )


def apply_cable_energization_layout(diagram: Any) -> Any:
    """Arrange the explicit core and metallic-sheath circuits in two rows."""
    graphics = _graphic_objects(diagram)
    missing = sorted(set(CABLE_ENERGIZATION_LAYOUT) - set(graphics))
    if missing:
        raise PowerFactoryExecutionError(
            "PowerFactory cable diagram is missing graphical objects: {}".format(missing)
        )
    for object_name, (x_coord, y_coord, rotation) in CABLE_ENERGIZATION_LAYOUT.items():
        graphic = graphics[object_name]
        set_attribute(graphic, "rCenterX", x_coord)
        set_attribute(graphic, "rCenterY", y_coord)
        set_attribute(graphic, "iRot", rotation)

    source_connection = _connections(graphics["GRID_EQUIVALENT"])[0]
    _set_connection(source_connection, (24.375, 50.0), (92.0, 92.0))

    breaker_connections = _connections(graphics["CB_CABLE_220"])
    _set_connection(breaker_connections[0], (75.8125, 50.0, 50.0), (92.0, 92.0, 92.0))
    _set_connection(breaker_connections[1], (80.1875, 108.0, 108.0), (92.0, 92.0, 92.0))

    core_connections = _connections(graphics["CABLE_CORE_220KV_40KM"])
    _set_connection(core_connections[0], (160.0, 108.0, 108.0), (92.0, 92.0, 92.0))
    _set_connection(core_connections[1], (160.0, 215.0, 215.0), (92.0, 92.0, 92.0))

    sheath_connections = _connections(graphics["CABLE_SHEATH_220KV_40KM"])
    _set_connection(sheath_connections[0], (160.0, 108.0, 108.0), (52.0, 52.0, 52.0))
    _set_connection(sheath_connections[1], (160.0, 215.0, 215.0), (52.0, 52.0, 52.0))

    set_font = getattr(diagram, "SetFontFor", None)
    if callable(set_font):
        for nodes_or_branches in (0, 1):
            set_font(0, nodes_or_branches, "Segoe UI", 9, 0)

    set_attribute(diagram, "loc_name", CABLE_DIAGRAM_NAME)
    for name, value in (
        ("rLBotX", 10.0),
        ("rLBotY", 35.0),
        ("rRTopX", 230.0),
        ("rRTopY", 110.0),
    ):
        set_attribute(diagram, name, value, required=False)
    return diagram


def remove_generated_cable_annotations(diagram: Any) -> Any:
    """Remove the retired PFEMT overlay without touching user-created layers."""
    layers = list(diagram.GetContents("*.IntGrflayer") or [])
    generated = [item for item in layers if item.loc_name == CABLE_GENERATED_LAYER_NAME]
    for layer in generated:
        clear = getattr(layer, "ClearData", None)
        if callable(clear):
            clear()
    set_visibility = getattr(diagram, "SetLayerVisibility", None)
    if callable(set_visibility):
        set_visibility(CABLE_GENERATED_LAYER_NAME, 0)
    return diagram


def ensure_cable_energization_diagram(app: Any, grid: Any) -> Any:
    """Create, link, and arrange the native explicit-sheath cable diagram."""
    folder = app.GetProjectFolder("dia", 1)
    expected = set(CABLE_ENERGIZATION_LAYOUT)
    linked = _linked_diagrams_for(folder, expected)
    if linked:
        preferred = next(
            (diagram for diagram in linked if diagram.loc_name == CABLE_DIAGRAM_NAME),
            linked[0],
        )
        _claim_diagram_name(folder, preferred, CABLE_DIAGRAM_NAME)
        # An existing diagram may contain carefully placed symbols and labels.
        # Preserve that engineering drawing across idempotent API rebuilds.
        return remove_generated_cable_annotations(preferred)

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
    candidates.extend(
        diagram
        for diagram in _linked_diagrams_for(folder, expected)
        if diagram not in candidates
    )
    for candidate in candidates:
        if expected.issubset(_graphic_objects(candidate)):
            _claim_diagram_name(folder, candidate, CABLE_DIAGRAM_NAME)
            apply_cable_energization_layout(candidate)
            return remove_generated_cable_annotations(candidate)
    raise PowerFactoryExecutionError(
        "Diagram Layout Tool completed but did not create the expected cable diagram"
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
    export_tab = getattr(command, "ExportGraphicTab", None)
    if callable(export_tab):
        export_code = export_tab(page, str(output))
        if export_code not in (None, 0):
            raise PowerFactoryExecutionError(
                "PowerFactory could not export diagram {!r} to {}".format(
                    diagram.loc_name, output
                )
            )
    else:
        # Compatibility path for PowerFactory releases that pre-date the
        # explicit ComWr.ExportGraphicTab API.
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
