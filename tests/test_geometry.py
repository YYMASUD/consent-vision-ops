from app.services.zones.geometry import point_in_polygon, bbox_center, bbox_bottom_center

def test_point_in_polygon_inside_outside_and_degenerate():
    square = [[0, 0], [10, 0], [10, 10], [0, 10]]
    assert point_in_polygon((5, 5), square)
    assert not point_in_polygon((15, 5), square)
    assert not point_in_polygon((1, 1), [[0, 0], [1, 1]])

def test_bbox_centers_support_width_aliases():
    box = {"x": 2, "y": 4, "width": 6, "height": 8}
    assert bbox_center(box) == (5.0, 8.0)
    assert bbox_bottom_center(box) == (5.0, 12.0)

