"""Evaluación de candidatos: independiente del algoritmo que los genera."""
import pytest

from optimization.evaluation import EvaluationSettings, Evaluator, Scenario
from optimization.fitness import FitnessFunction, FitnessWeights
from optimization.strategy import Candidate

from helpers import ConstantController, corridor_map, make_factory

SCENARIOS = [
    Scenario(corridor_map(), label="libre"),
    Scenario(corridor_map(static_obstacles=[(10, 5)]), label="bloqueado"),
]


def make_evaluator(**settings):
    # La "solución" de estos candidatos de prueba es simplemente la aceleración constante.
    return Evaluator(
        make_factory(max_time=20.0),
        controller_factory=lambda throttle, scenario: ConstantController(0.0, throttle),
        fitness=FitnessFunction(FitnessWeights()),
        settings=EvaluationSettings(stall_time=2.0, stall_distance=0.5, **settings),
    )


def test_each_candidate_runs_every_scenario_in_order():
    result = make_evaluator().evaluate([Candidate(0, 1.0)], SCENARIOS)[0]
    assert len(result.episodes) == 2
    assert result.episodes[0].reached_goal and not result.episodes[0].collided
    assert result.episodes[1].collided and not result.episodes[1].reached_goal


def test_fitness_is_the_aggregate_of_the_episode_scores():
    evaluator = make_evaluator()
    result = evaluator.evaluate([Candidate(0, 1.0)], SCENARIOS)[0]
    scores = [evaluator.fitness(m) for m in result.episodes]
    assert result.fitness == pytest.approx(sum(scores) / 2)


def test_metrics_describe_the_episode():
    episode = make_evaluator().evaluate([Candidate(0, 1.0)], SCENARIOS[:1])[0].episodes[0]
    assert episode.progress == 1.0
    assert episode.distance == pytest.approx(17.0, abs=1.0)
    assert 0 < episode.time < 20.0
    assert episode.time_limit == 20.0
    assert episode.mean_deviation == pytest.approx(0.0, abs=1e-9)
    assert episode.steering_change == 0.0


def test_a_stopped_vehicle_is_cut_short_as_stalled():
    episode = make_evaluator().evaluate([Candidate(0, 0.0)], SCENARIOS[:1])[0].episodes[0]
    assert episode.stalled and not episode.collided and not episode.reached_goal
    assert episode.time == pytest.approx(2.0, abs=0.1)


def test_better_candidates_get_better_fitness_on_the_same_scenarios():
    stopped, driver = make_evaluator().evaluate([Candidate(0, 0.0), Candidate(1, 1.0)], SCENARIOS)
    assert driver.fitness > stopped.fitness
    assert driver.candidate.id == 1


def test_identical_candidates_get_identical_results():
    a, b = make_evaluator().evaluate([Candidate(0, 0.7), Candidate(1, 0.7)], SCENARIOS)
    assert a.fitness == b.fitness and a.episodes == b.episodes


def test_stepwise_evaluation_matches_blocking_evaluation():
    evaluator = make_evaluator()
    blocking = evaluator.evaluate([Candidate(0, 1.0)], SCENARIOS)[0]
    run = evaluator.start(Candidate(0, 1.0), SCENARIOS)
    partials = []
    while not run.done:
        run.step()
        partials.append(run.partial_fitness)
    assert run.result().fitness == blocking.fitness
    assert partials[-1] == pytest.approx(blocking.fitness)
    assert all(isinstance(p, float) for p in partials)


def test_a_running_evaluation_exposes_its_own_simulation_for_display():
    evaluator = make_evaluator()
    first = evaluator.start(Candidate(0, 1.0), SCENARIOS)
    second = evaluator.start(Candidate(1, 1.0), SCENARIOS)
    assert first.simulation is not second.simulation
    assert first.simulation.world is not second.simulation.world
    assert first.episode_index == 0 and first.episode_count == 2


def test_controller_factory_receives_the_scenario_of_each_episode():
    seen = []

    def factory(throttle, scenario):
        seen.append(scenario.label)
        return ConstantController(0.0, throttle)

    evaluator = Evaluator(make_factory(max_time=20.0), factory, FitnessFunction(FitnessWeights()),
                          EvaluationSettings(stall_time=2.0))
    evaluator.evaluate([Candidate(0, 1.0)], SCENARIOS)
    assert seen == ["libre", "bloqueado"]


def test_result_keeps_the_score_of_each_episode_in_scenario_order():
    evaluator = make_evaluator()
    result = evaluator.evaluate([Candidate(0, 1.0)], SCENARIOS)[0]
    assert result.scores == [evaluator.fitness(m) for m in result.episodes]
    assert result.scores[0] > result.scores[1]


def test_scenario_key_identifies_the_map_content_not_its_name():
    same = Scenario(corridor_map(name="otro_nombre"), seed=5)
    assert same.key == SCENARIOS[0].key
    assert SCENARIOS[1].key != SCENARIOS[0].key
    assert Scenario(corridor_map(start_heading=0.3)).key != SCENARIOS[0].key
