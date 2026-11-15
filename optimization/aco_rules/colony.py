"""Colonia de hormigas que asigna una maniobra a cada situación de conducción.

Grafo de construcción: una etapa por situación y, en cada una, una arista por
maniobra. Cada hormiga recorre las etapas eligiendo con probabilidad
proporcional a ``feromona^alpha * heurística^beta``; el resultado es una tabla
de reglas. Tras evaluar la colonia, la feromona se evapora y las mejores
hormigas depositan sobre las decisiones que realmente usaron al conducir. Los
límites ``tau_min``/``tau_max`` evitan el estancamiento (al estilo MAX-MIN).

No sabe qué significan las situaciones ni cómo se evalúan las tablas.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, fields
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from control.rule_controller import RuleTable
from optimization.strategy import Candidate, CandidateResult, LearningStrategy, StrategyState


@dataclass
class ACORulesConfig:
    alpha: float = 1.0          # peso de la feromona
    beta: float = 2.0           # peso de la información heurística
    evaporation: float = 0.2    # fracción de feromona que se pierde en cada iteración
    elite_ants: int = 5         # hormigas que depositan, de la mejor a la peor
    tau_min: float = 0.01
    tau_max: float = 1.0

    @classmethod
    def from_dict(cls, data: dict) -> "ACORulesConfig":
        return cls(**{f.name: data[f.name] for f in fields(cls) if f.name in data})


class RuleColony(LearningStrategy):
    name = "aco_rules"

    def __init__(self, heuristic: np.ndarray, ants: int, config: Optional[ACORulesConfig] = None,
                 seed: int = 0) -> None:
        self.config = config or ACORulesConfig()
        self.heuristic = np.asarray(heuristic, dtype=float)
        self.ants = int(ants)
        self.states, self.actions = self.heuristic.shape
        self.pheromone = np.full(self.heuristic.shape, self.config.tau_max)
        self._rng = np.random.default_rng(seed)
        self._iteration = 0
        self._pending: Optional[List[Candidate]] = None
        self._rng_before_ask: Optional[dict] = None
        self._best: Optional[RuleTable] = None
        self._best_fitness: Optional[float] = None
        self._visited = np.ones(self.states, dtype=bool)   # situaciones que la colonia encontró en la última iteración

    @property
    def iteration(self) -> int:
        return self._iteration

    def _probabilities(self) -> np.ndarray:
        weights = self.pheromone ** self.config.alpha * self.heuristic ** self.config.beta
        return weights / weights.sum(axis=1, keepdims=True)

    def ask(self) -> List[Candidate]:
        if self._pending is None:
            self._rng_before_ask = copy.deepcopy(self._rng.bit_generator.state)
            thresholds = self._probabilities().cumsum(axis=1)
            tables = []
            if self._best is not None:      # la mejor hormiga vuelve a salir, con el contador de visitas limpio
                tables.append(RuleTable(self._best.actions.copy()))
            while len(tables) < self.ants:
                draws = self._rng.random(self.states)
                chosen = (draws[:, None] > thresholds).sum(axis=1)
                tables.append(RuleTable(np.minimum(chosen, self.actions - 1)))
            self._pending = [Candidate(i, table) for i, table in enumerate(tables)]
        return self._pending

    def tell(self, results: Sequence[CandidateResult]) -> None:
        if sorted(r.candidate.id for r in results) != list(range(self.ants)):
            raise ValueError("Se necesita el resultado de cada hormiga de la iteración, una sola vez")
        cfg = self.config
        ranked = sorted(results, key=lambda r: (-r.fitness, r.candidate.id))
        if self._best_fitness is None or ranked[0].fitness > self._best_fitness:
            winner = ranked[0].candidate.solution
            self._best = RuleTable(winner.actions.copy(), winner.visits.copy())
            self._best_fitness = float(ranked[0].fitness)
        self._visited = np.any([r.candidate.solution.visits > 0 for r in results], axis=0)

        self.pheromone *= 1.0 - cfg.evaporation                     # evaporación
        unit = cfg.evaporation * cfg.tau_max                        # un rastro reforzado siempre se mantiene en tau_max
        elite = max(1, min(cfg.elite_ants, self.ants))
        for rank, result in enumerate(ranked[:elite]):              # depósito por ranking
            self._deposit(result.candidate.solution, unit * (elite - rank) / elite)
        self._deposit(self._best, unit)                             # refuerzo de la mejor hormiga conocida
        np.clip(self.pheromone, cfg.tau_min, cfg.tau_max, out=self.pheromone)
        self._pending = None
        self._iteration += 1

    def _deposit(self, table: RuleTable, amount: float) -> None:
        used = np.flatnonzero(table.visits > 0)
        self.pheromone[used, table.actions[used]] += amount

    def best(self) -> Optional[Tuple[Any, float]]:
        if self._best is None:
            return None
        return RuleTable(self._best.actions.copy()), self._best_fitness

    def statistics(self) -> Dict[str, float]:
        strongest = self._probabilities().max(axis=1)
        return {
            "alpha": self.config.alpha,
            "beta": self.config.beta,
            "evaporation": self.config.evaporation,
            "explored_states": float(self._visited.sum()),
            "decisiveness": float(strongest[self._visited].mean()) if self._visited.any() else 0.0,
        }

    def get_state(self) -> StrategyState:
        arrays = {"pheromone": self.pheromone, "visited": self._visited}
        if self._best is not None:
            arrays["best_actions"] = self._best.actions
            arrays["best_visits"] = self._best.visits
        # Con hormigas pendientes de evaluar se guarda el estado previo a crearlas (el límite de iteración).
        rng = self._rng_before_ask if self._pending is not None else self._rng.bit_generator.state
        return StrategyState({"iteration": self._iteration, "best_fitness": self._best_fitness, "rng": rng}, arrays)

    def set_state(self, state: StrategyState) -> None:
        pheromone = np.array(state.arrays["pheromone"], dtype=float)
        if pheromone.shape != self.pheromone.shape:
            raise ValueError(
                f"El estado guardado tiene una tabla {pheromone.shape} y se esperaba {self.pheromone.shape}: "
                "cambiaron las situaciones o las maniobras"
            )
        self.pheromone = pheromone
        self._visited = np.array(state.arrays["visited"], dtype=bool)
        self._best = None
        if "best_actions" in state.arrays:
            self._best = RuleTable(np.array(state.arrays["best_actions"]), np.array(state.arrays["best_visits"]))
        self._best_fitness = state.meta["best_fitness"]
        self._iteration = int(state.meta["iteration"])
        self._rng.bit_generator.state = state.meta["rng"]
        self._pending = None
