"""Ruta ordenada de waypoints y seguimiento de navegación (libre y por ruta)."""
import math

import numpy as np
import pytest

from control.controller import FREE_NAVIGATION, ROUTE_FOLLOWING
from simulation.navigation import Navigator, Route

L_ROUTE = Route(np.array([[0.0, 0.0], [10.0, 0.0], [10.0, 5.0]]))


def test_route_length_and_points_follow_waypoint_order():
    assert L_ROUTE.length == pytest.approx(15.0)
    assert L_ROUTE.point_at(4.0) == pytest.approx((4.0, 0.0))
    assert L_ROUTE.point_at(12.0) == pytest.approx((10.0, 2.0))
    assert L_ROUTE.point_at(99.0) == pytest.approx((10.0, 5.0))


def test_projection_gives_arc_length_signed_deviation_and_heading():
    s, deviation, heading = L_ROUTE.project(3.0, 1.0)
    assert s == pytest.approx(3.0)
    assert deviation == pytest.approx(1.0)
    assert heading == pytest.approx(0.0)
    s, deviation, heading = L_ROUTE.project(3.0, -1.0)
    assert deviation == pytest.approx(-1.0)
    s, deviation, heading = L_ROUTE.project(11.0, 2.0)
    assert s == pytest.approx(12.0)
    assert heading == pytest.approx(math.pi / 2)


def test_route_navigator_reports_progress_target_and_deviation():
    nav = Navigator(ROUTE_FOLLOWING, L_ROUTE, goal=(10.0, 5.0), lookahead=2.0)
    info = nav.reset(0.0, 0.0)
    assert info.progress == pytest.approx(0.0)
    nav.update(2.5, 0.0)
    info = nav.update(5.0, 0.5)
    assert info.progress == pytest.approx(5.0 / 15.0)
    assert info.target == pytest.approx((7.0, 0.0))
    assert info.deviation == pytest.approx(0.5)
    assert info.goal_distance == pytest.approx(math.hypot(5.0, 4.5))


def test_route_progress_does_not_jump_to_a_later_part_of_the_route():
    # Ruta en U: el tramo de vuelta pasa cerca del de ida.
    route = Route(np.array([[0.0, 0.0], [20.0, 0.0], [20.0, 2.0], [0.0, 2.0]]))
    nav = Navigator(ROUTE_FOLLOWING, route, goal=(0.0, 2.0), lookahead=2.0)
    nav.reset(0.0, 0.0)
    info = nav.update(2.0, 1.2)  # más cerca del tramo de vuelta, pero aún al inicio
    assert info.progress < 0.2


def test_best_progress_never_decreases_when_going_backwards():
    nav = Navigator(ROUTE_FOLLOWING, L_ROUTE, goal=(10.0, 5.0), lookahead=2.0)
    nav.reset(0.0, 0.0)
    nav.update(3.0, 0.0)
    nav.update(6.0, 0.0)
    info = nav.update(4.0, 0.0)
    assert info.progress == pytest.approx(6.0 / 15.0)


def test_free_navigation_measures_progress_as_distance_gained_to_goal():
    route = Route(np.array([[0.0, 0.0], [10.0, 0.0]]))
    nav = Navigator(FREE_NAVIGATION, route, goal=(10.0, 0.0), lookahead=2.0)
    nav.reset(0.0, 0.0)
    info = nav.update(4.0, 3.0)
    assert info.goal_distance == pytest.approx(math.hypot(6.0, 3.0))
    assert info.progress == pytest.approx(1.0 - math.hypot(6.0, 3.0) / 10.0)
    assert info.deviation == 0.0
    assert info.target == pytest.approx((10.0, 0.0))
