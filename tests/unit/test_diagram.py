from pfemt.diagram import DIAGRAM_NAME, LINE_ENERGIZATION_LAYOUT, _padded_points


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


def test_powerfactory_connection_vectors_have_fixed_length() -> None:
    points = _padded_points([1.0, 2.0, 3.0])
    assert points[:3] == [1.0, 2.0, 3.0]
    assert points[3:] == [-1.0] * 17
