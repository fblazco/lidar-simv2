"""Controlador por tabla de reglas: situación discreta -> maniobra."""
import math

import numpy as np
import pytest

from config import load_config
from control.controller import Action, Controller, Observation
from control.rule_controller import (ObservationDiscretizer, RuleControllerFactory, RuleTable,
                                     RuleTableController, build_rule_controller_factory, default_maneuvers)

RANGE = 8.0


def observation(obstacles=(), bearing_deg=0.0, num_rays=72):
    """Observación con obstáculos dados como (ángulo relativo en grados, distancia)."""
    lidar = np.ones(num_rays)
    for angle, distance in obstacles:
        lidar[int(round((angle % 360) / (360 / num_rays))) % num_rays] = distance / RANGE
    return Observation(
        lidar=lidar, lidar_previous=lidar, heading=0.0, speed=1.0, max_speed=4.0,
        goal_distance=10.0, goal_bearing=0.0, waypoint_distance=2.0,
        waypoint_bearing=math.radians(bearing_deg), path_deviation=0.0, path_heading_error=0.0,
        navigation_mode="route", lidar_range=RANGE, time=0.0,
    )


@pytest.fixture
def discretizer():
    return ObservationDiscretizer(num_rays=72, fov_deg=360.0, near_distance=1.0, mid_distance=2.5)


def test_situations_combine_target_bearing_with_three_lidar_sectors(discretizer):
    assert discretizer.size == 5 * 3 * 3 * 3
    states = {discretizer.encode(observation(bearing_deg=b)) for b in (-120, -30, 0, 30, 120)}
    assert len(states) == 5
    for state in range(discretizer.size):
        bearing, left, front, right = discretizer.decode(state)
        assert 0 <= bearing < 5 and all(0 <= level < 3 for level in (left, front, right))


def test_free_space_ahead_reads_as_all_sectors_free(discretizer):
    assert discretizer.decode(discretizer.encode(observation())) == (2, 2, 2, 2)


def test_obstacle_distance_sets_the_level_of_its_sector(discretizer):
    near_front = discretizer.decode(discretizer.encode(observation([(0, 0.8)])))
    mid_front = discretizer.decode(discretizer.encode(observation([(0, 2.0)])))
    far_front = discretizer.decode(discretizer.encode(observation([(0, 5.0)])))
    assert (near_front[2], mid_front[2], far_front[2]) == (0, 1, 2)


def test_obstacles_are_assigned_to_the_side_they_are_on(discretizer):
    # ángulos positivos = lado hacia el que gira una dirección positiva
    assert discretizer.decode(discretizer.encode(observation([(45, 0.8)]))) == (2, 2, 2, 0)
    assert discretizer.decode(discretizer.encode(observation([(-45, 0.8)]))) == (2, 0, 2, 2)
    assert discretizer.decode(discretizer.encode(observation([(180, 0.5)]))) == (2, 2, 2, 2)   # detrás no cuenta


def test_bearing_bins_go_from_far_left_to_far_right(discretizer):
    bins = [discretizer.decode(discretizer.encode(observation(bearing_deg=b)))[0] for b in (-120, -30, 0, 30, 120)]
    assert bins == [0, 1, 2, 3, 4]


def test_controller_applies_the_maneuver_of_the_current_situation_and_notes_the_visit(discretizer):
    maneuvers = default_maneuvers()
    table = RuleTable(np.zeros(discretizer.size, dtype=int))
    state = discretizer.encode(observation([(0, 0.8)]))
    table.actions[state] = 7
    controller = RuleTableController(table, discretizer, maneuvers)
    assert isinstance(controller, Controller)
    assert controller.act(observation([(0, 0.8)])) == maneuvers[7]
    assert controller.act(observation()) == maneuvers[0]
    assert table.visits[state] == 1 and table.visits.sum() == 2


def test_maneuvers_cover_left_right_and_accelerate_brake():
    maneuvers = default_maneuvers()
    assert len(maneuvers) == 15 and all(isinstance(m, Action) for m in maneuvers)
    assert {m.steering for m in maneuvers} == {-1.0, -0.5, 0.0, 0.5, 1.0}
    assert max(m.acceleration for m in maneuvers) == 1.0 and min(m.acceleration for m in maneuvers) == -1.0


def test_factory_builds_controllers_and_reports_the_table_dimensions():
    factory = build_rule_controller_factory(load_config())
    assert isinstance(factory, RuleControllerFactory)
    assert (factory.n_states, factory.n_actions) == (135, 15)
    controller = factory(RuleTable(np.full(135, 2, dtype=int)))
    assert controller.act(observation()) == factory.maneuvers[2]


def test_table_of_the_wrong_size_is_rejected():
    factory = build_rule_controller_factory(load_config())
    with pytest.raises(ValueError):
        factory(RuleTable(np.zeros(10, dtype=int)))
