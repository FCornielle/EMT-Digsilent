from pathlib import Path
from types import SimpleNamespace

from pfemt.diagram import (
    CABLE_DIAGRAM_NAME,
    CABLE_ENERGIZATION_LAYOUT,
    CABLE_GENERATED_LAYER_NAME,
    DIAGRAM_NAME,
    LINE_ENERGIZATION_LAYOUT,
    _claim_diagram_name,
    _linked_diagrams,
    _padded_points,
    export_powerfactory_diagram,
    remove_generated_cable_annotations,
)


class _Diagram:
    def __init__(self, object_names: list[str]) -> None:
        self.graphics = [
            SimpleNamespace(pDataObj=SimpleNamespace(loc_name=name)) for name in object_names
        ]

    def GetContents(self, pattern: str) -> list[object]:
        assert pattern == "*.IntGrf"
        return self.graphics


class _Folder:
    def __init__(self, diagrams: list[_Diagram]) -> None:
        self.diagrams = diagrams

    def GetContents(self, pattern: str) -> list[_Diagram]:
        assert pattern == "*.IntGrfnet"
        return self.diagrams


def test_native_diagram_layout_is_complete_and_horizontal() -> None:
    expected_order = [
        "GRID_EQUIVALENT",
        "BUS_SENDING_230",
        "CB_LINE_230",
        "BUS_LINE_SIDE_230",
        "LINE_230KV_150KM",
        "BUS_RECEIVING_230",
    ]
    assert DIAGRAM_NAME == "EMT Line Energization 230 kV"
    assert list(LINE_ENERGIZATION_LAYOUT) == expected_order
    x_coordinates = [LINE_ENERGIZATION_LAYOUT[name][0] for name in expected_order]
    y_coordinates = [LINE_ENERGIZATION_LAYOUT[name][1] for name in expected_order]
    assert x_coordinates == sorted(x_coordinates)
    assert len(set(y_coordinates)) == 1
    assert all(
        LINE_ENERGIZATION_LAYOUT[name][2] == 90
        for name in ("BUS_SENDING_230", "BUS_LINE_SIDE_230", "BUS_RECEIVING_230")
    )
    assert min(right - left for left, right in zip(x_coordinates, x_coordinates[1:])) >= 20.0


def test_powerfactory_connection_vectors_have_fixed_length() -> None:
    points = _padded_points([1.0, 2.0, 3.0])
    assert points[:3] == [1.0, 2.0, 3.0]
    assert points[3:] == [-1.0] * 17


def test_cable_diagram_separates_core_and_sheath_circuits() -> None:
    assert CABLE_DIAGRAM_NAME == "EMT Cable Energization 220 kV"
    core_names = (
        "BUS_CABLE_LINE_SIDE_220",
        "CABLE_CORE_220KV_40KM",
        "BUS_CABLE_RECEIVING_220",
    )
    sheath_names = (
        "BUS_SHEATH_SENDING_220",
        "CABLE_SHEATH_220KV_40KM",
        "BUS_SHEATH_RECEIVING_220",
    )
    assert len(CABLE_ENERGIZATION_LAYOUT) == 11
    assert {CABLE_ENERGIZATION_LAYOUT[name][1] for name in core_names} == {92.0}
    assert {CABLE_ENERGIZATION_LAYOUT[name][1] for name in sheath_names} == {52.0}
    assert [CABLE_ENERGIZATION_LAYOUT[name][0] for name in core_names] == [108.0, 160.0, 215.0]
    assert [CABLE_ENERGIZATION_LAYOUT[name][0] for name in sheath_names] == [
        108.0,
        160.0,
        215.0,
    ]
    assert CABLE_ENERGIZATION_LAYOUT["GND_SHEATH_SENDING_220"] == (108.0, 35.0, 0)
    assert CABLE_ENERGIZATION_LAYOUT["GND_SHEATH_RECEIVING_220"] == (215.0, 35.0, 0)


def test_existing_autolayout_diagram_is_detected_by_linked_objects() -> None:
    complete = _Diagram(list(LINE_ENERGIZATION_LAYOUT))
    incomplete = _Diagram(list(LINE_ENERGIZATION_LAYOUT)[:-1])
    assert _linked_diagrams(_Folder([incomplete, complete])) == [complete]


def test_complete_diagram_claims_canonical_name_without_deleting_legacy() -> None:
    class _NamedDiagram:
        def __init__(self, name: str, path: str) -> None:
            self.loc_name = name
            self.path = path

        def GetFullName(self) -> str:
            return self.path

        def HasAttribute(self, name: str) -> int:
            return int(name == "loc_name")

        def SetAttribute(self, name: str, value: object) -> None:
            setattr(self, name, value)

    legacy = _NamedDiagram(CABLE_DIAGRAM_NAME, "legacy.IntGrfnet")
    complete = _NamedDiagram("{}(1)".format(CABLE_DIAGRAM_NAME), "complete.IntGrfnet")
    folder = _Folder([legacy, complete])

    assert _claim_diagram_name(folder, complete, CABLE_DIAGRAM_NAME) is complete
    assert complete.loc_name == CABLE_DIAGRAM_NAME
    assert legacy.loc_name == "Legacy - {}".format(CABLE_DIAGRAM_NAME)


def test_export_uses_powerfactory_graphic_tab_api(tmp_path: Path) -> None:
    output = tmp_path / "native_diagram.png"
    diagram = SimpleNamespace(loc_name=CABLE_DIAGRAM_NAME)
    page = SimpleNamespace(loc_name=CABLE_DIAGRAM_NAME)

    class _Board:
        def __init__(self) -> None:
            self.shown = None

        def GetContents(self, pattern: str) -> list[object]:
            assert pattern == "*.SetDeskpage"
            return [page]

        def Show(self, selected: object) -> int:
            self.shown = selected
            return 0

    class _Writer:
        def __init__(self) -> None:
            self.exported = None

        def ExportGraphicTab(self, selected: object, filename: str) -> int:
            self.exported = (selected, filename)
            Path(filename).write_bytes(b"powerfactory-png")
            return 0

    board = _Board()
    writer = _Writer()
    app = SimpleNamespace(
        GetGraphicsBoard=lambda: board,
        GetFromStudyCase=lambda class_name: writer if class_name == "ComWr" else None,
    )

    assert export_powerfactory_diagram(app, diagram, output) == output.resolve()
    assert board.shown is page
    assert writer.exported == (page, str(output.resolve()))


def test_retired_generated_annotations_are_cleared_and_hidden() -> None:
    class _Layer:
        loc_name = CABLE_GENERATED_LAYER_NAME

        def __init__(self) -> None:
            self.cleared = 0

        def ClearData(self) -> None:
            self.cleared += 1

    class _AnnotatedDiagram:
        def __init__(self) -> None:
            self.layer = _Layer()
            self.visible = None

        def GetContents(self, pattern: str) -> list[object]:
            assert pattern == "*.IntGrflayer"
            return [self.layer]

        def SetLayerVisibility(self, layer_name: str, visible: int) -> None:
            self.visible = (layer_name, visible)

    diagram = _AnnotatedDiagram()
    assert remove_generated_cable_annotations(diagram) is diagram
    assert diagram.layer.cleared == 1
    assert diagram.visible == (CABLE_GENERATED_LAYER_NAME, 0)
