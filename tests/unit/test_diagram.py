from types import SimpleNamespace

from pfemt.diagram import (
    DIAGRAM_NAME,
    LINE_ENERGIZATION_LAYOUT,
    _linked_diagrams,
    _padded_points,
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


def test_existing_autolayout_diagram_is_detected_by_linked_objects() -> None:
    complete = _Diagram(list(LINE_ENERGIZATION_LAYOUT))
    incomplete = _Diagram(list(LINE_ENERGIZATION_LAYOUT)[:-1])
    assert _linked_diagrams(_Folder([incomplete, complete])) == [complete]
