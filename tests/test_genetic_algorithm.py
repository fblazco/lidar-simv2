"""Algoritmo genético como estrategia de aprendizaje (sin simulador)."""
import numpy as np
import pytest

from optimization.genetic.genetic_algorithm import GAConfig, GeneticAlgorithm
from optimization.strategy import CandidateResult, LearningStrategy

TARGET = np.linspace(-1.0, 1.0, 12)


def sphere(genome):
    """Fitness de juguete: cuanto más cerca de TARGET, mejor (máximo 0)."""
    return -float(np.sum((genome - TARGET) ** 2))


def evaluate(ga):
    return [CandidateResult(c, sphere(c.solution), []) for c in ga.ask()]


def make_ga(seed=7, **config):
    return GeneticAlgorithm(genome_length=12, population_size=30, config=GAConfig(**config), seed=seed)


def test_is_a_learning_strategy_and_offers_one_candidate_per_individual():
    ga = make_ga()
    assert isinstance(ga, LearningStrategy)
    candidates = ga.ask()
    assert [c.id for c in candidates] == list(range(30))
    assert all(c.solution.shape == (12,) for c in candidates)


def test_generation_only_advances_when_results_are_told():
    ga = make_ga()
    first = [c.solution.copy() for c in ga.ask()]
    again = [c.solution.copy() for c in ga.ask()]
    assert ga.iteration == 0
    assert all(np.array_equal(a, b) for a, b in zip(first, again))
    ga.tell(evaluate(ga))
    assert ga.iteration == 1
    assert len(ga.ask()) == 30


def test_incomplete_results_are_rejected():
    ga = make_ga()
    with pytest.raises(ValueError):
        ga.tell(evaluate(ga)[:-1])
    assert ga.iteration == 0


def test_elitism_keeps_the_best_individuals_unchanged():
    ga = make_ga(elitism=3)
    results = evaluate(ga)
    ranked = sorted(results, key=lambda r: r.fitness, reverse=True)
    ga.tell(results)
    survivors = [c.solution for c in ga.ask()[:3]]
    for survivor, elite in zip(survivors, ranked[:3]):
        assert np.array_equal(survivor, elite.candidate.solution)


def test_best_reports_the_fittest_solution_seen_in_the_last_generation():
    ga = make_ga()
    assert ga.best() is None
    results = evaluate(ga)
    ga.tell(results)
    solution, fitness = ga.best()
    top = max(results, key=lambda r: r.fitness)
    assert fitness == top.fitness and np.array_equal(solution, top.candidate.solution)


def test_evolution_improves_fitness_over_generations():
    ga = make_ga()
    history = []
    for _ in range(60):
        results = evaluate(ga)
        history.append(max(r.fitness for r in results))
        ga.tell(results)
    assert all(b >= a for a, b in zip(history, history[1:]))   # elitismo: nunca empeora
    assert history[-1] > history[0] / 10                        # error al menos 10 veces menor
    assert ga.iteration == 60


def test_same_seed_gives_the_same_evolution_and_different_seeds_differ():
    def run(seed):
        ga = make_ga(seed=seed)
        for _ in range(5):
            ga.tell(evaluate(ga))
        return np.array([c.solution for c in ga.ask()])

    assert np.array_equal(run(1), run(1))
    assert not np.array_equal(run(1), run(2))


def test_saved_state_resumes_exactly_where_it_left_off():
    original = make_ga()
    for _ in range(3):
        original.tell(evaluate(original))
    state = original.get_state()
    resumed = make_ga(seed=999)
    resumed.set_state(state)
    assert resumed.iteration == 3
    assert resumed.best()[1] == original.best()[1]
    for _ in range(3):
        original.tell(evaluate(original))
        resumed.tell(evaluate(resumed))
    assert np.array_equal(np.array([c.solution for c in original.ask()]),
                          np.array([c.solution for c in resumed.ask()]))


def test_statistics_report_ga_specific_values():
    ga = make_ga(mutation_rate=0.2, mutation_sigma=0.4, sigma_decay=0.5)
    stats = ga.statistics()
    assert stats["mutation_rate"] == 0.2 and stats["mutation_sigma"] == 0.4
    assert stats["diversity"] > 0
    ga.tell(evaluate(ga))
    assert ga.statistics()["mutation_sigma"] == pytest.approx(0.2)


def test_state_for_another_population_shape_is_rejected():
    state = make_ga().get_state()
    other = GeneticAlgorithm(genome_length=5, population_size=30, config=GAConfig(), seed=1)
    with pytest.raises(ValueError):
        other.set_state(state)
