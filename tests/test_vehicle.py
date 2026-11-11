"""Movimiento continuo del vehículo (modelo cinemático)."""
import math

import pytest

from control.controller import Action
from simulation.vehicle import Mobile, VehicleParams

DT = 0.05


def drive(mobile, action, steps):
    for _ in range(steps):
        mobile.apply(action, DT)


def test_full_throttle_moves_straight_along_heading():
    mobile = Mobile(VehicleParams())
    mobile.reset(2.0, 3.0, 0.0)
    drive(mobile, Action(0.0, 1.0), 20)
    assert mobile.state.speed > 0
    assert mobile.state.x > 2.0
    assert mobile.state.y == pytest.approx(3.0)
    assert mobile.state.heading == pytest.approx(0.0)


def test_heading_defines_direction_of_travel():
    mobile = Mobile(VehicleParams())
    mobile.reset(0.0, 0.0, math.pi / 2)
    drive(mobile, Action(0.0, 1.0), 20)
    assert mobile.state.x == pytest.approx(0.0, abs=1e-9)
    assert mobile.state.y > 0


def test_speed_is_capped_at_max_speed():
    params = VehicleParams(max_speed=3.0)
    mobile = Mobile(params)
    mobile.reset(0.0, 0.0, 0.0)
    drive(mobile, Action(0.0, 1.0), 400)
    assert mobile.state.speed <= 3.0 + 1e-9
    assert mobile.state.speed > 2.0


def test_braking_stops_without_reversing_when_reverse_is_disabled():
    mobile = Mobile(VehicleParams(max_reverse_speed=0.0))
    mobile.reset(0.0, 0.0, 0.0)
    drive(mobile, Action(0.0, 1.0), 20)
    drive(mobile, Action(0.0, -1.0), 200)
    assert mobile.state.speed == pytest.approx(0.0)


def test_steering_has_no_effect_while_stopped():
    mobile = Mobile(VehicleParams())
    mobile.reset(0.0, 0.0, 0.0)
    drive(mobile, Action(1.0, 0.0), 20)
    assert mobile.state.heading == pytest.approx(0.0)


def test_steering_sign_sets_turn_direction():
    left, right = Mobile(VehicleParams()), Mobile(VehicleParams())
    for mobile, steering in ((left, -1.0), (right, 1.0)):
        mobile.reset(0.0, 0.0, 0.0)
        drive(mobile, Action(steering, 1.0), 10)
    assert right.state.heading > 0 > left.state.heading


def test_distance_traveled_accumulates_path_length():
    mobile = Mobile(VehicleParams())
    mobile.reset(0.0, 0.0, 0.0)
    drive(mobile, Action(0.0, 1.0), 40)
    assert mobile.distance_traveled == pytest.approx(mobile.state.x, rel=1e-6)


def test_drag_slows_the_vehicle_when_coasting():
    mobile = Mobile(VehicleParams(drag=0.5))
    mobile.reset(0.0, 0.0, 0.0)
    drive(mobile, Action(0.0, 1.0), 20)
    cruising = mobile.state.speed
    drive(mobile, Action(0.0, 0.0), 20)
    assert 0 < mobile.state.speed < cruising


def test_actions_outside_range_are_clipped():
    a, b = Mobile(VehicleParams()), Mobile(VehicleParams())
    a.reset(0, 0, 0)
    b.reset(0, 0, 0)
    drive(a, Action(5.0, 9.0), 10)
    drive(b, Action(1.0, 1.0), 10)
    assert a.state.x == pytest.approx(b.state.x)
    assert a.state.heading == pytest.approx(b.state.heading)
