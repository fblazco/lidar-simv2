"""Operaciones del editor de mapas (modelo, sin Pygame)."""
import math

import pytest

from editor.map_editor import MapEditor, line_cells


def editor():
    return MapEditor(cols=20, rows=12)


def test_line_cells_connects_two_cells_with_contiguous_steps():
    assert line_cells((2, 2), (6, 2)) == [(2, 2), (3, 2), (4, 2), (5, 2), (6, 2)]
    assert line_cells((1, 1), (4, 4)) == [(1, 1), (2, 2), (3, 3), (4, 4)]
    assert line_cells((3, 3), (3, 3)) == [(3, 3)]


def test_dragging_builds_an_ordered_route_without_gaps():
    ed = editor()
    ed.add_route_cell((2, 2))
    ed.add_route_cell((2, 2))          # el mouse sigue en la misma celda
    ed.add_route_cell((5, 2))          # salto rápido del mouse
    ed.add_route_cell((7, 4))
    assert ed.map.route == [(2, 2), (3, 2), (4, 2), (5, 2), (6, 3), (7, 4)]


def test_route_cells_outside_the_grid_are_ignored():
    ed = editor()
    ed.add_route_cell((-1, 3))
    ed.add_route_cell((99, 3))
    assert ed.map.route == []


def test_erase_removes_a_waypoint_and_keeps_the_order_of_the_rest():
    ed = editor()
    for cell in [(1, 1), (4, 1)]:
        ed.add_route_cell(cell)
    assert ed.erase((2, 1))
    assert ed.map.route == [(1, 1), (3, 1), (4, 1)]
    assert not ed.erase((10, 10))


def test_static_obstacles_are_added_once_and_erased():
    ed = editor()
    ed.add_static((5, 5))
    ed.add_static((5, 5))
    assert ed.map.static_obstacles == [(5, 5)]
    ed.erase((5, 5))
    assert ed.map.static_obstacles == []


def test_start_and_goal_cannot_share_a_cell_with_a_static_obstacle():
    ed = editor()
    ed.set_start((2, 2))
    ed.set_goal((9, 9))
    ed.add_static((2, 2))
    ed.add_static((9, 9))
    assert ed.map.static_obstacles == []
    ed.add_static((4, 4))
    ed.set_start((4, 4))
    assert ed.map.static_obstacles == [] and ed.map.start == (4, 4)


def test_start_orientation_can_be_set_by_pointing_at_a_cell():
    ed = editor()
    ed.set_start((5, 5))
    ed.point_start_towards((5, 8))
    assert ed.map.start_heading == pytest.approx(math.pi / 2)
    ed.point_start_towards((2, 5))
    assert abs(ed.map.start_heading) == pytest.approx(math.pi)


def test_dragging_a_horizontal_obstacle_defines_extremes_and_direction():
    ed = editor()
    spec = ed.add_dynamic("horizontal", (8, 3), (4, 3))
    assert (spec.x, spec.y) == (8.5, 3.5)
    assert (spec.range_min, spec.range_max) == (4.5, 8.5)
    assert spec.direction == -1
    assert ed.map.dynamic_obstacles == [spec]


def test_clicking_a_vertical_obstacle_gets_default_extremes_inside_the_map():
    ed = editor()
    spec = ed.add_dynamic("vertical", (3, 1), (3, 1))
    assert spec.range_min == 0.5 and spec.range_max == 4.5
    assert spec.x == 3.5


def test_dragging_a_circular_obstacle_defines_center_radius_and_start():
    ed = editor()
    spec = ed.add_dynamic("circular", (10, 6), (13, 6))
    assert (spec.center_x, spec.center_y) == (10.5, 6.5)
    assert spec.orbit_radius == pytest.approx(3.0)
    assert (spec.x, spec.y) == (13.5, 6.5)


def test_dynamic_obstacle_properties_can_be_edited_and_removed():
    ed = editor()
    ed.add_dynamic("horizontal", (8, 3), (4, 3))
    index = ed.dynamic_at((8, 3))
    assert index == 0
    ed.update_dynamic(index, speed=3.0, pause=1.5, direction=1)
    spec = ed.map.dynamic_obstacles[0]
    assert (spec.speed, spec.pause, spec.direction) == (3.0, 1.5, 1)
    ed.remove_dynamic(index)
    assert ed.map.dynamic_obstacles == [] and ed.dynamic_at((8, 3)) is None


def test_resize_drops_everything_that_falls_outside():
    ed = editor()
    ed.set_start((1, 1))
    ed.set_goal((18, 10))
    ed.add_static((15, 2))
    ed.add_route_cell((1, 1))
    ed.add_route_cell((12, 1))
    ed.add_dynamic("horizontal", (16, 5), (18, 5))
    ed.resize(10, 8)
    m = ed.map
    assert (m.cols, m.rows) == (10, 8)
    assert m.goal is None and m.start == (1, 1)
    assert m.static_obstacles == [] and m.dynamic_obstacles == []
    assert m.route == [(c, 1) for c in range(1, 10)]


def test_every_change_bumps_the_revision():
    ed = editor()
    before = ed.revision
    ed.add_static((3, 3))
    ed.set_navigation_mode("free")
    assert ed.revision == before + 2
    assert ed.map.navigation_mode == "free"
