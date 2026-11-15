"""Capa de evasión de obstáculos: FTG, APF y su composición con cualquier controlador."""
import math

import numpy as np
import pytest

from bootstrap import (available_avoidance, build_simulation_factory, build_training_session,
                       load_training_session, save_training_session)
from config import load_config
from control.avoidance import discover_avoidance
from control.avoidance.apf import PotentialFields
from control.avoidance.base import AvoidanceController, ObstacleAvoider, intended_direction, with_avoidance
from control.avoidance.ftg import FollowTheGap
from control.controller import Action, Controller, Observation
from control.goal_controller import GoalSeekingController
from simulation.map_data import DynamicObstacleSpec
from simulation.vehicle import Status

from helpers import ConstantController, corridor_map

RANGE = 8.0


def observation(obstacles=(), bearing_deg=0.0, speed=2.0):
    """Observación con obstáculos dados como (ángulo relativo en grados, distancia)."""
    lidar = np.ones(72)
    for angle, distance in obstacles:
        lidar[int(round((angle % 360) / 5)) % 72] = distance / RANGE
    return Observation(
        lidar=lidar, lidar_previous=lidar, heading=0.0, speed=speed, max_speed=4.0, goal_distance=10.0,
        goal_bearing=math.radians(bearing_deg), waypoint_distance=5.0, waypoint_bearing=math.radians(bearing_deg),
        path_deviation=0.0, path_heading_error=0.0, navigation_mode="free", lidar_range=RANGE, time=0.0,
    )


def arc(start_deg, end_deg, distance):
    return [(angle, distance) for angle in range(start_deg, end_deg + 1, 5)]


def ftg(**settings):
    return FollowTheGap(num_rays=72, fov_deg=360.0, robot_radius=0.35, **settings)


def apf(**settings):
    return PotentialFields(num_rays=72, fov_deg=360.0, robot_radius=0.35, **settings)


STRAIGHT, FAST = Action(0.0, 1.0), Action(0.0, 1.0)


# --- registro ----------------------------------------------------------------------------------

def test_three_avoidance_choices_are_available_and_learned_comes_first():
    plugins = discover_avoidance()
    assert list(plugins) == ["learned", "apf", "ftg"]
    assert plugins["learned"].build(load_config()) is None            # la evasión la aporta el propio algoritmo
    assert isinstance(plugins["ftg"].build(load_config()), FollowTheGap)
    assert isinstance(plugins["apf"].build(load_config()), PotentialFields)
    assert all(p.label and p.short_label and p.description for p in plugins.values())
    assert available_avoidance().keys() == plugins.keys()


# --- composición ---------------------------------------------------------------------------------

class Swerve(ObstacleAvoider):
    def __init__(self):
        self.seen, self.resets = [], 0

    def reset(self):
        self.resets += 1

    def adjust(self, observation, proposal):
        self.seen.append(proposal)
        return Action(0.5, proposal.acceleration)


def test_avoidance_wraps_any_controller_and_adjusts_what_it_proposes():
    inner, avoider = ConstantController(0.2, 0.8), Swerve()
    controller = AvoidanceController(inner, avoider)
    assert isinstance(controller, Controller)
    controller.reset()
    assert controller.act(observation()) == Action(0.5, 0.8)
    assert avoider.seen == [Action(0.2, 0.8)] and avoider.resets == 1 and inner.resets == 1
    assert len(inner.observations) == 1


def test_wrapped_controller_keeps_exposing_the_route_of_the_inner_one():
    class Planner(ConstantController):
        planned_path = np.array([[0.0, 0.0], [1.0, 1.0]])

    assert AvoidanceController(Planner(), Swerve()).planned_path.shape == (2, 2)
    assert AvoidanceController(ConstantController(), Swerve()).planned_path is None


def test_with_avoidance_gives_each_controller_its_own_avoider():
    factory = with_avoidance(lambda solution, scenario: ConstantController(0.0, solution), Swerve)
    a, b = factory(1.0, None), factory(0.5, None)
    assert a.avoider is not b.avoider and a.inner.action.acceleration == 1.0


def test_intended_direction_reads_steering_as_where_the_controller_wants_to_go():
    assert intended_direction(Action(0.0, 1.0)) == 0.0
    assert intended_direction(Action(1.0, 1.0)) == pytest.approx(math.pi / 2)
    assert intended_direction(Action(-0.5, 1.0)) == pytest.approx(-math.pi / 4)


# --- Follow the Gap ----------------------------------------------------------------------------

def test_ftg_does_not_interfere_in_free_space():
    assert ftg().adjust(observation(), STRAIGHT) == STRAIGHT
    assert ftg().adjust(observation(), Action(0.4, 0.6)).steering > 0
    assert ftg().adjust(observation(), Action(-0.4, 0.6)).steering < 0


def test_ftg_steers_into_the_gap_beside_an_obstacle_ahead():
    left_blocked = ftg().adjust(observation(arc(-40, 5, 1.4)), STRAIGHT)       # obstáculo al frente y a la izquierda
    right_blocked = ftg().adjust(observation(arc(-5, 40, 1.4)), STRAIGHT)
    assert left_blocked.steering > 0.2 and right_blocked.steering < -0.2
    assert left_blocked.acceleration < 1.0                                       # y reduce la velocidad


def test_ftg_turns_harder_the_closer_the_obstacle_is():
    # Con alfa = 1 la ponderación se ve sin saturar la dirección.
    far = ftg(alpha=1.0).adjust(observation(arc(-40, 5, 2.2)), STRAIGHT)
    near = ftg(alpha=1.0).adjust(observation(arc(-40, 5, 0.9)), STRAIGHT)
    assert near.steering > far.steering > 0


def test_ftg_brakes_when_there_is_no_gap():
    assert ftg().adjust(observation(arc(-180, 175, 0.6)), FAST).acceleration == -1.0


def test_ftg_ignores_obstacles_beyond_its_free_distance_and_behind():
    assert ftg(free_distance=2.5).adjust(observation(arc(-20, 20, 4.0)), STRAIGHT) == STRAIGHT
    assert ftg().adjust(observation(arc(150, 210, 0.8)), STRAIGHT).steering == 0.0


# --- Campos potenciales ----------------------------------------------------------------------------

def test_apf_follows_the_attraction_in_free_space():
    assert apf().adjust(observation(), STRAIGHT) == STRAIGHT
    assert apf().adjust(observation(), Action(0.4, 0.6)).steering > 0


def test_apf_is_pushed_away_from_obstacles():
    assert apf().adjust(observation(arc(-60, -20, 1.2)), STRAIGHT).steering > 0     # obstáculo a la izquierda
    assert apf().adjust(observation(arc(20, 60, 1.2)), STRAIGHT).steering < 0


def test_apf_repulsion_grows_as_the_obstacle_gets_closer():
    far = apf().adjust(observation(arc(-60, -20, 2.0)), STRAIGHT)
    near = apf().adjust(observation(arc(-60, -20, 0.8)), STRAIGHT)
    assert near.steering > far.steering > 0


def test_apf_cancels_out_between_symmetric_obstacles_and_slows_down_in_front_of_one():
    corridor = apf().adjust(observation(arc(-105, -75, 1.2) + arc(75, 105, 1.2)), STRAIGHT)   # paredes a ambos lados
    assert corridor.steering == pytest.approx(0.0, abs=1e-6)
    assert apf().adjust(observation(arc(-10, 10, 0.9)), FAST).acceleration < 1.0


def test_apf_ignores_obstacles_outside_its_influence_distance():
    assert apf(influence_distance=2.5).adjust(observation(arc(-30, 30, 4.0)), STRAIGHT) == STRAIGHT


# --- referencia sin aprendizaje ----------------------------------------------------------------------

def test_goal_seeker_points_at_the_waypoint_and_speeds_up():
    seeker = GoalSeekingController()
    assert isinstance(seeker, Controller)
    assert seeker.act(observation(bearing_deg=40, speed=0.0)).steering > 0
    assert seeker.act(observation(bearing_deg=-40, speed=0.0)).steering < 0
    assert seeker.act(observation(speed=0.0)) == Action(0.0, 1.0)
    assert intended_direction(seeker.act(observation(bearing_deg=40))) == pytest.approx(math.radians(40))


# --- en el simulador ----------------------------------------------------------------------------------

def drive(map_data, controller):
    sim = build_simulation_factory(load_config()).create(map_data, [controller])
    while not sim.done:
        sim.step()
    return sim.mobiles[0]


def blocked_map(**overrides):
    """Navegación libre con un obstáculo fijo justo sobre la recta al destino."""
    return corridor_map(navigation_mode="free", route=[], static_obstacles=[(10, 5)], **overrides)


def avoider(name):
    return discover_avoidance()[name].build(load_config())


def test_going_straight_at_the_goal_crashes_without_avoidance():
    assert drive(blocked_map(), GoalSeekingController()).status is Status.COLLIDED


@pytest.mark.parametrize("name", ["ftg", "apf"])
def test_classic_avoidance_gets_the_goal_seeker_around_a_static_obstacle(name):
    mobile = drive(blocked_map(), AvoidanceController(GoalSeekingController(), avoider(name)))
    assert mobile.status is Status.REACHED_GOAL
    assert mobile.distance_traveled < 1.5 * 17.0          # rodea sin perderse


@pytest.mark.parametrize("name", ["ftg", "apf"])
def test_classic_avoidance_survives_an_obstacle_crossing_the_way(name):
    crossing = DynamicObstacleSpec(kind="vertical", x=9.5, y=2.5, speed=1.5, range_min=2.5, range_max=8.5)
    world = corridor_map(navigation_mode="free", route=[], dynamic_obstacles=[crossing])
    mobile = drive(world, AvoidanceController(GoalSeekingController(), avoider(name)))
    assert mobile.status is Status.REACHED_GOAL


# --- en el entrenamiento --------------------------------------------------------------------------------

def tiny(**training):
    return load_config(overrides={
        "map": {"cols": 16, "rows": 10}, "simulation": {"max_time": 8.0}, "policy": {"hidden_layers": [4]},
        "generator": {"static_obstacles": [1, 2], "dynamic_obstacles": [1, 1]},
        "training": {"population_size": 6, "visible_agents": 0, "scenarios_per_candidate": 2,
                     "validation_scenarios": 2, "stall_time": 1.5, "resample_scenarios_every": 0, **training},
    })


def test_reference_strategy_evaluates_one_fixed_controller_each_iteration():
    session = build_training_session(tiny(strategy="reactive", avoidance="ftg"))
    assert session.strategy.name == "reactive" and session.avoidance == "ftg"
    candidates = session.strategy.ask()
    assert len(candidates) == 1
    stats = session.run_iteration()
    assert stats.evaluations == 1 and stats.iteration_episodes == 2 and session.strategy.iteration == 1
    controller = session.best_controller(blocked_map())
    assert isinstance(controller, AvoidanceController)
    assert isinstance(controller.inner, GoalSeekingController) and isinstance(controller.avoider, FollowTheGap)


def test_avoidance_is_learned_by_default_and_nothing_is_wrapped():
    session = build_training_session(tiny())
    session.run_iteration()
    assert session.avoidance == "learned"
    assert type(session.best_controller(blocked_map())).__name__ == "PolicyController"


@pytest.mark.parametrize("strategy,avoidance", [("genetic", "apf"), ("aco_rules", "ftg"), ("aco_routes", "ftg")])
def test_any_algorithm_trains_with_any_avoidance_and_resumes_identically(strategy, avoidance, tmp_path):
    config = tiny(strategy=strategy, avoidance=avoidance)
    straight = build_training_session(config)
    expected = [s.best_fitness for s in (straight.run_iteration(), straight.run_iteration())]
    first = build_training_session(config)
    first.run_iteration()
    resumed, _ = load_training_session(save_training_session(first, tmp_path / "c.npz", config))
    assert resumed.avoidance == avoidance
    assert resumed.run_iteration().best_fitness == expected[1]


def test_route_colony_still_shows_its_routes_when_wrapped_by_an_avoider():
    session = build_training_session(tiny(strategy="aco_routes", avoidance="apf"))
    session.begin_iteration()
    run = session.evaluator.start(session.strategy.ask()[0], session.scenarios.training_set(0))
    assert run.controller.planned_path.shape[1] == 2


def test_unknown_avoidance_is_reported_with_the_available_choices():
    with pytest.raises(ValueError, match="ftg"):
        build_training_session(tiny(avoidance="dwa"))
