"""Operadores genéticos: selección, crossover y mutación."""
import numpy as np
import pytest

from optimization.genetic.crossover import get_crossover
from optimization.genetic.genome import population_diversity, random_population
from optimization.genetic.mutation import gaussian_mutation
from optimization.genetic.selection import tournament_selection


def rng(seed=0):
    return np.random.default_rng(seed)


def test_random_population_has_the_requested_shape_and_scale():
    population = random_population(40, 200, 0.5, rng())
    assert population.shape == (40, 200)
    assert population.std() == pytest.approx(0.5, rel=0.1)


def test_diversity_is_zero_for_clones_and_positive_otherwise():
    assert population_diversity(np.ones((5, 8))) == 0.0
    assert population_diversity(random_population(20, 50, 1.0, rng())) > 0.5


def test_tournament_as_large_as_the_population_always_picks_the_best():
    fitness = np.array([1.0, 9.0, 3.0, 4.0])
    r = rng()
    assert all(tournament_selection(fitness, 50, r) == 1 for _ in range(20))


def test_tournament_favours_fitter_individuals():
    fitness = np.arange(10, dtype=float)
    r = rng(1)
    picks = [tournament_selection(fitness, 3, r) for _ in range(2000)]
    assert all(0 <= p < 10 for p in picks)
    assert np.mean(picks) > 6.0
    assert len(set(picks)) > 5     # no es puramente elitista


def test_uniform_crossover_takes_every_gene_from_one_parent():
    a, b = np.zeros(200), np.ones(200)
    child = get_crossover("uniform")(a, b, rng())
    assert set(np.unique(child)) == {0.0, 1.0}
    assert 60 < child.sum() < 140


def test_single_point_crossover_joins_a_prefix_and_a_suffix():
    a, b = np.zeros(50), np.ones(50)
    child = get_crossover("single_point")(a, b, rng(3))
    cut = int(np.argmax(child))
    assert 0 < cut < 50
    assert np.all(child[:cut] == 0.0) and np.all(child[cut:] == 1.0)


def test_blend_crossover_stays_between_the_parents():
    a, b = np.full(100, -1.0), np.full(100, 2.0)
    child = get_crossover("blend")(a, b, rng())
    assert np.all((child >= -1.0) & (child <= 2.0))
    assert child.std() > 0


def test_crossover_does_not_modify_the_parents_and_unknown_types_fail():
    a, b = np.zeros(20), np.ones(20)
    get_crossover("uniform")(a, b, rng())
    assert not a.any() and b.all()
    with pytest.raises(ValueError):
        get_crossover("inexistente")


def test_mutation_rate_controls_how_many_genes_change():
    genes = np.zeros(5000)
    assert np.array_equal(gaussian_mutation(genes, 0.0, 0.3, rng()), genes)
    assert np.count_nonzero(gaussian_mutation(genes, 1.0, 0.3, rng())) == 5000
    changed = np.count_nonzero(gaussian_mutation(genes, 0.1, 0.3, rng()))
    assert 400 < changed < 600


def test_mutation_noise_is_gaussian_with_the_given_sigma_and_leaves_input_intact():
    genes = np.zeros(20000)
    mutated = gaussian_mutation(genes, 1.0, 0.3, rng())
    assert mutated.std() == pytest.approx(0.3, rel=0.05)
    assert abs(mutated.mean()) < 0.01
    assert not genes.any()
