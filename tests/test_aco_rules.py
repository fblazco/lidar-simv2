"""Colonia de hormigas que asigna una maniobra a cada situación (sin simulador)."""
import numpy as np
import pytest

from control.rule_controller import RuleTable
from optimization.aco_rules.colony import ACORulesConfig, RuleColony
from optimization.aco_rules.heuristic import build_heuristic
from optimization.strategy import CandidateResult, LearningStrategy

STATES, ACTIONS = 8, 4
TARGET = np.array([0, 1, 2, 3, 0, 1, 2, 3])


def make_colony(seed=3, ants=12, heuristic=None, **config):
    heuristic = np.ones((STATES, ACTIONS)) if heuristic is None else heuristic
    return RuleColony(heuristic, ants=ants, config=ACORulesConfig(**config), seed=seed)


def matches(table):
    """Fitness de juguete: cuántas situaciones tienen la maniobra correcta."""
    return float(np.sum(table.actions == TARGET))


def evaluate(colony, visited=None):
    results = []
    for candidate in colony.ask():
        candidate.solution.visits[:] = 0
        candidate.solution.visits[slice(None) if visited is None else visited] = 1
        results.append(CandidateResult(candidate, matches(candidate.solution), []))
    return results


def test_is_a_learning_strategy_whose_ants_are_rule_tables():
    colony = make_colony()
    assert isinstance(colony, LearningStrategy) and colony.name == "aco_rules" and colony.generalizes
    ants = colony.ask()
    assert [a.id for a in ants] == list(range(12))
    for ant in ants:
        assert isinstance(ant.solution, RuleTable)
        assert ant.solution.actions.shape == (STATES,)
        assert np.all((ant.solution.actions >= 0) & (ant.solution.actions < ACTIONS))


def test_asking_twice_returns_the_same_ants_until_results_are_told():
    colony = make_colony()
    first, again = colony.ask(), colony.ask()
    assert all(a.solution is b.solution for a, b in zip(first, again))
    assert colony.iteration == 0
    colony.tell(evaluate(colony))
    assert colony.iteration == 1
    assert colony.ask()[1].solution is not first[1].solution


def test_incomplete_results_are_rejected():
    colony = make_colony()
    with pytest.raises(ValueError):
        colony.tell(evaluate(colony)[:-1])


def test_pheromone_starts_at_its_maximum_and_stays_within_bounds():
    colony = make_colony(tau_min=0.02, tau_max=1.0)
    assert np.all(colony.pheromone == 1.0)
    for _ in range(40):
        colony.tell(evaluate(colony))
    assert colony.pheromone.min() >= 0.02 and colony.pheromone.max() <= 1.0
    assert colony.pheromone.min() == pytest.approx(0.02)      # lo que nadie refuerza se evapora hasta el mínimo


def test_evaporation_reduces_what_is_not_reinforced_and_deposit_keeps_the_best_trail():
    colony = make_colony(evaporation=0.25, elite_ants=1)
    results = evaluate(colony)
    best = max(results, key=lambda r: r.fitness).candidate.solution
    colony.tell(results)
    states = np.arange(STATES)
    on_trail = colony.pheromone[states, best.actions]
    off_trail = np.delete(colony.pheromone, best.actions[0], axis=1)[0]
    assert np.allclose(on_trail, 1.0)
    assert np.allclose(off_trail, 0.75)


def test_only_the_situations_an_ant_actually_met_are_reinforced():
    colony = make_colony(evaporation=0.5, elite_ants=3)
    colony.tell(evaluate(colony, visited=[0, 1]))
    assert colony.pheromone[:2].max() == 1.0
    assert np.allclose(colony.pheromone[2:], 0.5)


def test_ants_follow_strong_pheromone_trails():
    colony = make_colony(ants=200)
    colony.pheromone[:] = 0.01
    colony.pheromone[:, 2] = 1.0
    chosen = np.array([a.solution.actions for a in colony.ask()])
    assert np.mean(chosen == 2) > 0.9


def test_heuristic_guides_the_ants_while_pheromone_is_flat():
    heuristic = np.full((STATES, ACTIONS), 0.1)
    heuristic[:, 1] = 1.0
    guided = np.array([a.solution.actions for a in make_colony(ants=200, heuristic=heuristic, beta=2.0).ask()])
    blind = np.array([a.solution.actions for a in make_colony(ants=200, heuristic=heuristic, beta=0.0).ask()])
    assert np.mean(guided == 1) > 0.9
    assert 0.15 < np.mean(blind == 1) < 0.35


def test_best_ant_returns_as_the_first_ant_of_the_next_iteration():
    colony = make_colony()
    results = evaluate(colony)
    top = max(results, key=lambda r: r.fitness)
    colony.tell(results)
    solution, fitness = colony.best()
    assert fitness == top.fitness and np.array_equal(solution.actions, top.candidate.solution.actions)
    elite = colony.ask()[0].solution
    assert np.array_equal(elite.actions, top.candidate.solution.actions)
    assert elite.visits.sum() == 0 and elite is not top.candidate.solution


def test_colony_converges_on_the_best_assignment():
    colony = make_colony()
    history = []
    for _ in range(40):
        results = evaluate(colony)
        history.append(max(r.fitness for r in results))
        colony.tell(results)
    assert all(b >= a for a, b in zip(history, history[1:]))
    assert history[-1] == STATES
    assert colony.statistics()["decisiveness"] > 0.8


def test_same_seed_reproduces_the_colony_and_state_resumes_exactly():
    def run(colony, steps):
        for _ in range(steps):
            colony.tell(evaluate(colony))
        return np.array([a.solution.actions for a in colony.ask()])

    assert np.array_equal(run(make_colony(seed=5), 4), run(make_colony(seed=5), 4))
    assert not np.array_equal(run(make_colony(seed=5), 4), run(make_colony(seed=6), 4))

    original = make_colony(seed=5)
    run(original, 3)
    original.tell(evaluate(original))            # deja el estado justo en un límite de iteración
    resumed = make_colony(seed=99)
    resumed.set_state(original.get_state())
    assert resumed.iteration == original.iteration and resumed.best()[1] == original.best()[1]
    assert np.array_equal(run(original, 3), run(resumed, 3))


def test_state_of_another_table_shape_is_rejected():
    other = RuleColony(np.ones((3, 2)), ants=4, config=ACORulesConfig(), seed=1)
    with pytest.raises(ValueError):
        other.set_state(make_colony().get_state())


def test_statistics_report_colony_parameters():
    stats = make_colony(alpha=1.5, beta=2.5, evaporation=0.3).statistics()
    assert (stats["alpha"], stats["beta"], stats["evaporation"]) == (1.5, 2.5, 0.3)
    assert 0.0 < stats["decisiveness"] <= 1.0


def test_driving_heuristic_prefers_turning_towards_the_target_and_away_from_obstacles():
    from config import load_config
    from control.rule_controller import build_rule_controller_factory

    factory = build_rule_controller_factory(load_config())
    heuristic = build_heuristic(factory.discretizer, factory.maneuvers)
    assert heuristic.shape == (factory.n_states, factory.n_actions) and heuristic.min() > 0

    def preferred(bearing, left, front, right):
        state = ((bearing * 3 + left) * 3 + front) * 3 + right
        return factory.maneuvers[int(np.argmax(heuristic[state]))]

    assert preferred(2, 2, 2, 2).steering == 0.0 and preferred(2, 2, 2, 2).acceleration == 1.0
    assert preferred(0, 2, 2, 2).steering == -1.0                 # objetivo muy a la izquierda
    assert preferred(4, 2, 2, 2).steering == 1.0
    assert preferred(2, 0, 2, 2).steering > 0                     # obstáculo a la izquierda: desviar a la derecha
    assert preferred(2, 2, 2, 0).steering < 0
    assert preferred(2, 2, 0, 2).acceleration < 1.0               # algo cerca al frente: no acelerar a fondo
