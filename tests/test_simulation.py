"""Simulación completa: mundo + móviles + controladores inyectados."""
import pytest

from control.controller import FREE_NAVIGATION, ROUTE_FOLLOWING
from control.manual_controller import ManualController
from simulation.map_data import DynamicObstacleSpec
from simulation.vehicle import Status

from helpers import ConstantController, corridor_map, make_factory


def run(sim, max_steps=2000):
    steps = 0
    while not sim.done and steps < max_steps:
        sim.step()
        steps += 1
    return steps


def test_vehicle_driving_straight_reaches_the_goal():
    sim = make_factory().create(corridor_map(), [ConstantController()])
    run(sim)
    mobile = sim.mobiles[0]
    assert mobile.status is Status.REACHED_GOAL
    assert mobile.navigation.progress == pytest.approx(1.0, abs=0.05)
    assert mobile.distance_traveled == pytest.approx(17.0, abs=1.0)


def test_static_obstacle_on_the_way_causes_a_collision():
    sim = make_factory().create(corridor_map(static_obstacles=[(10, 5)]), [ConstantController()])
    run(sim)
    mobile = sim.mobiles[0]
    assert mobile.status is Status.COLLIDED
    assert mobile.state.x < 10.0


def test_dynamic_obstacle_crossing_the_route_causes_a_collision():
    blocker = DynamicObstacleSpec(kind="vertical", x=9.5, y=5.5, speed=0.0, range_min=5.5, range_max=5.5)
    sim = make_factory().create(corridor_map(dynamic_obstacles=[blocker]), [ConstantController()])
    run(sim)
    assert sim.mobiles[0].status is Status.COLLIDED


def test_lidar_detects_static_and_dynamic_obstacles():
    moving = DynamicObstacleSpec(kind="vertical", x=1.5, y=8.5, speed=0.0, range_min=8.5, range_max=8.5, radius=0.4)
    sim = make_factory().create(
        corridor_map(static_obstacles=[(5, 5)], dynamic_obstacles=[moving]), [ConstantController(0.0, 0.0)]
    )
    scan = sim.mobiles[0].scan
    assert scan.shape == (72,)
    assert scan[0] == pytest.approx(3.5 / 8.0)           # celda X al frente (x=5.0), vehículo en x=1.5
    assert scan[18] == pytest.approx((3.0 - 0.4) / 8.0)  # obstáculo dinámico a 90° (abajo)


def test_time_limit_ends_the_episode_as_timed_out():
    sim = make_factory(max_time=1.0).create(corridor_map(), [ConstantController(0.0, 0.0)])
    steps = run(sim)
    assert sim.mobiles[0].status is Status.TIMED_OUT
    assert steps == 20
    assert sim.time == pytest.approx(1.0)


def test_mobiles_with_different_controllers_run_independently():
    manual = ManualController()
    sim = make_factory().create(corridor_map(), [ConstantController(), manual])
    for _ in range(40):
        sim.step()
    driven, parked = sim.mobiles
    assert driven.state.x > parked.state.x
    assert parked.state.speed == 0.0
    assert driven.scan is not parked.scan
    manual.set_command(steering=0.0, acceleration=1.0)
    for _ in range(40):
        sim.step()
    assert parked.state.speed > 0.0


def test_a_finished_mobile_does_not_stop_the_others():
    sim = make_factory().create(
        corridor_map(static_obstacles=[(4, 5)]), [ConstantController(), ConstantController(0.0, 0.0)]
    )
    for _ in range(100):
        sim.step()
    crashed, idle = sim.mobiles
    assert crashed.status is Status.COLLIDED
    assert idle.status is Status.ACTIVE
    assert not sim.done


def test_controller_receives_numeric_observation_with_mode_and_targets():
    controller = ConstantController()
    sim = make_factory().create(corridor_map(), [controller])
    sim.step()
    obs = controller.observations[0]
    assert obs.lidar.shape == (72,) and obs.lidar_previous.shape == (72,)
    assert obs.navigation_mode == ROUTE_FOLLOWING
    assert obs.goal_distance == pytest.approx(17.0)
    assert obs.goal_bearing == pytest.approx(0.0)
    assert obs.waypoint_bearing == pytest.approx(0.0)
    assert obs.path_deviation == pytest.approx(0.0)
    assert obs.speed == 0.0


def test_free_navigation_uses_the_same_simulation_and_reaches_the_goal():
    controller = ConstantController()
    sim = make_factory().create(corridor_map(navigation_mode=FREE_NAVIGATION, route=[]), [controller])
    run(sim)
    assert controller.observations[0].navigation_mode == FREE_NAVIGATION
    assert sim.mobiles[0].status is Status.REACHED_GOAL


def test_reset_restores_start_pose_time_and_controller():
    controller = ConstantController()
    sim = make_factory().create(corridor_map(), [controller])
    resets_after_create = controller.resets
    for _ in range(30):
        sim.step()
    sim.reset()
    mobile = sim.mobiles[0]
    assert sim.time == 0.0
    assert (mobile.state.x, mobile.state.y, mobile.state.speed) == (1.5, 5.5, 0.0)
    assert mobile.status is Status.ACTIVE
    assert controller.resets == resets_after_create + 1


def test_simulation_is_deterministic():
    def trajectory():
        spec = DynamicObstacleSpec(kind="circular", x=12.0, y=3.0, speed=1.5, center_x=10.0, center_y=3.0, orbit_radius=2.0)
        sim = make_factory().create(corridor_map(dynamic_obstacles=[spec]), [ConstantController(0.2, 0.6)])
        out = []
        for _ in range(120):
            sim.step()
            s = sim.mobiles[0].state
            out.append((s.x, s.y, s.heading, s.speed, tuple(sim.mobiles[0].scan)))
        return out

    assert trajectory() == trajectory()
