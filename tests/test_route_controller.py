"""Controlador que sigue una ruta de waypoints y frena ante lo que detecta el LiDAR."""
import numpy as np
import pytest

from control.controller import Controller
from control.route_controller import RouteController
from sensors.lidar import Lidar
from simulation.environment import SimulationConfig
from simulation.factory import SimulationFactory
from simulation.map_data import DynamicObstacleSpec
from simulation.vehicle import Status, VehicleParams

from helpers import corridor_map

STRAIGHT = [(c + 0.5, 5.5) for c in range(1, 19)]


def follower(waypoints, **settings):
    return RouteController(waypoints, num_rays=72, fov_deg=360.0, **settings)


def drive(map_data, controller, max_time=40.0):
    factory = SimulationFactory(VehicleParams(), lambda: Lidar(72, 360.0, 8.0),
                                SimulationConfig(dt=0.05, max_time=max_time, goal_radius=0.6))
    sim = factory.create(map_data, [controller])
    while not sim.done:
        sim.step()
    return sim


def test_is_a_controller_and_exposes_its_planned_path():
    controller = follower(STRAIGHT)
    assert isinstance(controller, Controller)
    assert controller.planned_path.shape == (18, 2)
    assert tuple(controller.planned_path[0]) == (1.5, 5.5)


def test_follows_a_straight_route_to_the_goal():
    sim = drive(corridor_map(navigation_mode="free", route=[]), follower(STRAIGHT))
    assert sim.mobiles[0].status is Status.REACHED_GOAL
    assert sim.time < 12.0


def test_follows_a_route_with_turns():
    cells = [(c, 5) for c in range(1, 9)] + [(8, r) for r in range(4, 1, -1)] + [(c, 2) for c in range(9, 16)]
    waypoints = [(c + 0.5, r + 0.5) for c, r in cells]
    sim = drive(corridor_map(navigation_mode="free", route=[], goal=(15, 2)), follower(waypoints))
    mobile = sim.mobiles[0]
    assert mobile.status is Status.REACHED_GOAL
    assert mobile.distance_traveled < 1.4 * (len(cells) - 1)        # sin rodeos ni vueltas en círculo


def test_waits_for_a_moving_obstacle_instead_of_crashing_into_it():
    # El obstáculo ocupa el camino durante 3 s y después se aparta.
    blocker = DynamicObstacleSpec(kind="vertical", x=9.5, y=5.5, speed=2.0, pause=3.0, direction=1,
                                  range_min=1.5, range_max=5.5)
    free = drive(corridor_map(navigation_mode="free", route=[]), follower(STRAIGHT))
    blocked = drive(corridor_map(navigation_mode="free", route=[], dynamic_obstacles=[blocker]), follower(STRAIGHT))
    assert blocked.mobiles[0].status is Status.REACHED_GOAL
    assert blocked.time > free.time + 0.5


def test_reset_starts_again_from_the_first_waypoint():
    controller = follower(STRAIGHT)
    drive(corridor_map(navigation_mode="free", route=[]), controller)
    controller.reset()
    sim = drive(corridor_map(navigation_mode="free", route=[]), controller)
    assert sim.mobiles[0].status is Status.REACHED_GOAL


def test_route_needs_at_least_one_waypoint():
    with pytest.raises(ValueError):
        follower([])
