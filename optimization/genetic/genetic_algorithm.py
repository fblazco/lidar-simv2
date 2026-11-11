"""Algoritmo genético tradicional sobre genomas de reales.

No sabe qué representan los genes ni cómo se evalúan: solo crea poblaciones,
recibe fitness y produce la generación siguiente.
"""
from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from optimization.genetic.crossover import get_crossover
from optimization.genetic.genome import population_diversity, random_population
from optimization.genetic.mutation import gaussian_mutation
from optimization.genetic.selection import tournament_selection
from optimization.strategy import Candidate, CandidateResult, LearningStrategy, StrategyState


@dataclass
class GAConfig:
    elitism: int = 2                 # mejores individuos que pasan intactos
    tournament_size: int = 3
    init_scale: float = 0.5          # desviación de los genes iniciales
    crossover_type: str = "uniform"  # uniform | single_point | blend
    crossover_rate: float = 0.8      # probabilidad de cruzar dos padres (si no, se clona uno)
    mutation_rate: float = 0.1       # probabilidad de mutar cada gen
    mutation_sigma: float = 0.3      # desviación del ruido gaussiano
    sigma_decay: float = 1.0         # factor aplicado a sigma tras cada generación

    @classmethod
    def from_dict(cls, data: dict) -> "GAConfig":
        """Acepta la sección ``genetic`` de la configuración (con crossover y mutation anidados)."""
        flat = {k: v for k, v in data.items() if not isinstance(v, dict)}
        crossover, mutation = data.get("crossover", {}), data.get("mutation", {})
        flat.update({f"crossover_{k}": v for k, v in crossover.items()})
        flat.update({"mutation_rate": mutation.get("rate", cls.mutation_rate),
                     "mutation_sigma": mutation.get("sigma", cls.mutation_sigma),
                     "sigma_decay": mutation.get("sigma_decay", cls.sigma_decay)})
        return cls(**{f.name: flat[f.name] for f in fields(cls) if f.name in flat})


class GeneticAlgorithm(LearningStrategy):
    name = "genetic"

    def __init__(self, genome_length: int, population_size: int, config: Optional[GAConfig] = None,
                 seed: int = 0) -> None:
        self.config = config or GAConfig()
        self.genome_length = int(genome_length)
        self.population_size = int(population_size)
        self._crossover = get_crossover(self.config.crossover_type)
        self._rng = np.random.default_rng(seed)
        self.population = random_population(self.population_size, self.genome_length,
                                            self.config.init_scale, self._rng)
        self._generation = 0
        self._sigma = self.config.mutation_sigma
        self._diversity = population_diversity(self.population)
        self._best_genome: Optional[np.ndarray] = None
        self._best_fitness: Optional[float] = None

    @property
    def iteration(self) -> int:
        return self._generation

    def ask(self) -> List[Candidate]:
        return [Candidate(i, self.population[i]) for i in range(self.population_size)]

    def tell(self, results: Sequence[CandidateResult]) -> None:
        if sorted(r.candidate.id for r in results) != list(range(self.population_size)):
            raise ValueError("Se necesita el resultado de cada individuo de la generación, una sola vez")
        fitness = np.empty(self.population_size)
        for result in results:
            fitness[result.candidate.id] = result.fitness
        order = np.argsort(-fitness, kind="stable")          # 1. ordenar por fitness
        self._best_genome = self.population[order[0]].copy()
        self._best_fitness = float(fitness[order[0]])
        self._diversity = population_diversity(self.population)

        cfg = self.config
        elites = min(max(cfg.elitism, 0), self.population_size)
        offspring = np.empty_like(self.population)
        offspring[:elites] = self.population[order[:elites]]  # 2. elitismo
        for i in range(elites, self.population_size):
            child = self.population[tournament_selection(fitness, cfg.tournament_size, self._rng)]  # 3. padres
            if self._rng.random() < cfg.crossover_rate:       # 4. crossover y mutación
                other = self.population[tournament_selection(fitness, cfg.tournament_size, self._rng)]
                child = self._crossover(child, other, self._rng)
            offspring[i] = gaussian_mutation(child, cfg.mutation_rate, self._sigma, self._rng)
        self.population = offspring                           # 5. generación siguiente
        self._generation += 1
        self._sigma *= cfg.sigma_decay

    def best(self) -> Optional[Tuple[Any, float]]:
        if self._best_genome is None:
            return None
        return self._best_genome, self._best_fitness

    def statistics(self) -> Dict[str, float]:
        return {
            "mutation_rate": self.config.mutation_rate,
            "mutation_sigma": self._sigma,
            "crossover_rate": self.config.crossover_rate,
            "elitism": float(self.config.elitism),
            "diversity": self._diversity,
        }

    def get_state(self) -> StrategyState:
        arrays = {"population": self.population}
        if self._best_genome is not None:
            arrays["best_genome"] = self._best_genome
        meta = {
            "generation": self._generation,
            "sigma": self._sigma,
            "diversity": self._diversity,
            "best_fitness": self._best_fitness,
            "rng": self._rng.bit_generator.state,
        }
        return StrategyState(meta, arrays)

    def set_state(self, state: StrategyState) -> None:
        population = np.array(state.arrays["population"], dtype=float)
        if population.shape != (self.population_size, self.genome_length):
            raise ValueError(
                f"El estado guardado tiene una población {population.shape} y se esperaba "
                f"({self.population_size}, {self.genome_length}): la red o la población cambiaron"
            )
        self.population = population
        best = state.arrays.get("best_genome")
        self._best_genome = np.array(best, dtype=float) if best is not None else None
        self._best_fitness = state.meta["best_fitness"]
        self._generation = int(state.meta["generation"])
        self._sigma = float(state.meta["sigma"])
        self._diversity = float(state.meta["diversity"])
        self._rng.bit_generator.state = state.meta["rng"]
