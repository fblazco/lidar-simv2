"""Función de fitness sobre las métricas de un episodio."""
import pytest

from optimization.fitness import EpisodeMetrics, FitnessFunction, FitnessWeights

fitness = FitnessFunction(FitnessWeights())


def metrics(**overrides):
    data = dict(progress=0.5, reached_goal=False, collided=False, stalled=False, time=20.0, time_limit=40.0,
                distance=10.0, mean_deviation=0.0, steering_change=0.0, acceleration_change=0.0,
                reference_length=10.0, min_clearance=1.0)
    data.update(overrides)
    return EpisodeMetrics(**data)


def test_more_progress_towards_the_goal_scores_higher():
    assert fitness(metrics(progress=0.8)) > fitness(metrics(progress=0.3))


def test_reaching_the_goal_is_worth_far_more_than_just_surviving():
    survived = fitness(metrics(progress=0.99, time=40.0))
    arrived = fitness(metrics(progress=1.0, reached_goal=True, time=40.0))
    assert arrived > 3 * survived


def test_arriving_sooner_scores_higher():
    assert fitness(metrics(progress=1.0, reached_goal=True, time=10.0)) > \
        fitness(metrics(progress=1.0, reached_goal=True, time=30.0))


def test_collision_is_penalized():
    assert fitness(metrics(collided=True)) < fitness(metrics())


def test_a_vehicle_that_stays_still_does_not_get_a_high_fitness():
    stopped = fitness(metrics(progress=0.0, stalled=True, distance=0.0, time=4.0))
    crashed_after_advancing = fitness(metrics(progress=0.3, collided=True))
    assert stopped < 0
    assert stopped < crashed_after_advancing
    assert stopped < fitness(metrics(progress=0.0, collided=True, time=1.0))


def test_deviation_from_the_path_is_penalized_up_to_a_limit():
    on_path, off_path, far_off = (fitness(metrics(mean_deviation=d)) for d in (0.0, 1.0, 50.0))
    assert on_path > off_path > far_off
    assert far_off == pytest.approx(on_path - FitnessWeights().deviation)


def test_jerky_control_is_penalized():
    assert fitness(metrics(steering_change=0.8, acceleration_change=0.8)) < fitness(metrics())


def test_aggregate_is_the_mean_over_scenarios():
    assert fitness.aggregate([10.0, 20.0, 60.0]) == pytest.approx(30.0)


def test_weights_come_from_configuration():
    custom = FitnessFunction(FitnessWeights.from_dict(
        {"progress": 10.0, "goal": 0.0, "time_bonus": 0.0, "efficiency": 0.0}))
    assert custom(metrics(progress=1.0, reached_goal=True)) == pytest.approx(10.0)


def test_path_efficiency_compares_the_distance_driven_with_the_shortest_path():
    assert metrics(reached_goal=True, distance=10.0, reference_length=10.0).path_efficiency == 1.0
    assert metrics(reached_goal=True, distance=20.0, reference_length=10.0).path_efficiency == 0.5
    assert metrics(reached_goal=True, distance=9.0, reference_length=10.0).path_efficiency == 1.0   # nunca más de 1
    assert metrics(reached_goal=False, distance=10.0, reference_length=10.0).path_efficiency == 0.0


def test_a_shorter_path_to_the_goal_scores_higher():
    direct = fitness(metrics(progress=1.0, reached_goal=True, distance=10.0, reference_length=10.0))
    detour = fitness(metrics(progress=1.0, reached_goal=True, distance=25.0, reference_length=10.0))
    assert direct - detour == pytest.approx(FitnessWeights().efficiency * 0.6)
    assert FitnessWeights().efficiency > 0
