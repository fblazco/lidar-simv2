"""Sesión de entrenamiento: ciclo pedir -> evaluar -> informar, independiente del algoritmo.

El trabajo se reparte en llamadas cortas a ``advance`` para no bloquear el ciclo
de la interfaz; ``run_iteration`` usa exactamente el mismo camino sin ventana.
Vocabulario: un *candidato* (individuo) se evalúa en varios *episodios* (uno por
escenario); una *iteración* (generación) termina cuando todos los candidatos
fueron evaluados, y solo entonces la estrategia produce la siguiente.
"""
from __future__ import annotations

import copy
import time
from collections import deque
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Deque, Dict, List, Optional, Sequence, Tuple

import numpy as np

from control.controller import Controller
from optimization.evaluation import CandidateEvaluation, Evaluator, Scenario
from optimization.strategy import Candidate, CandidateResult, LearningStrategy, StrategyState
from simulation.map_data import MapData

IDLE, EVALUATING, VALIDATING = "idle", "evaluating", "validating"
BACKGROUND_CHUNK = 32          # pasos de simulación entre consultas del reloj
ARRAY_PREFIX = "strategy."


class ScenarioProvider:
    """Conjuntos de escenarios reproducibles a partir de una semilla maestra.

    Todos los candidatos de una iteración reciben el mismo conjunto de
    entrenamiento. El conjunto de validación usa otro flujo de semillas y nunca
    interviene en la selección.
    """

    def __init__(self, generate: Callable[[int], MapData], seed: int, train_count: int, validation_count: int,
                 fixed_maps: Sequence[MapData] = (), resample_every: int = 0) -> None:
        self.generate = generate
        self.seed = int(seed)
        self.train_count = int(train_count)
        self.validation_count = int(validation_count)
        self.fixed_maps = list(fixed_maps)
        self.resample_every = int(resample_every)
        self._cache: Dict[Tuple[int, ...], List[Scenario]] = {}

    def _seeds(self, stream: int, epoch: int, count: int) -> List[int]:
        return [int(s) for s in np.random.SeedSequence([self.seed, stream, epoch]).generate_state(count)]

    def training_seeds(self, iteration: int) -> List[int]:
        epoch = iteration // self.resample_every if self.resample_every > 0 else 0
        return self._seeds(0, epoch, self.train_count)

    def validation_seeds(self) -> List[int]:
        return self._seeds(1, 0, self.validation_count)

    def _random_scenarios(self, seeds: List[int]) -> List[Scenario]:
        key = tuple(seeds)
        if key not in self._cache:
            self._cache = {k: v for k, v in self._cache.items() if k == tuple(self.validation_seeds())}
            self._cache[key] = [Scenario(self.generate(s), s, f"semilla {s}") for s in seeds]
        return self._cache[key]

    def training_set(self, iteration: int) -> List[Scenario]:
        fixed = [Scenario(m, None, m.name) for m in self.fixed_maps]
        return fixed + self._random_scenarios(self.training_seeds(iteration))

    def validation_set(self) -> List[Scenario]:
        return self._random_scenarios(self.validation_seeds())

    def state(self) -> dict:
        return {"seed": self.seed, "fixed_maps": [m.to_dict() for m in self.fixed_maps]}


@dataclass
class IterationStats:
    iteration: int                    # generación evaluada (1 = la primera)
    evaluations: int                  # candidatos evaluados en total
    episodes: int                     # episodios simulados en total
    best_fitness: float
    mean_fitness: float
    worst_fitness: float
    success_rate: float               # fracción de episodios que llegaron al destino
    collisions: int                   # episodios de esta iteración que terminaron en colisión
    mean_distance: float              # distancia media recorrida por episodio
    mean_time: float                  # tiempo medio de navegación por episodio (s)
    validation_fitness: Optional[float] = None
    validation_success_rate: Optional[float] = None
    training_seeds: List[int] = field(default_factory=list)
    strategy: Dict[str, float] = field(default_factory=dict)   # estadísticas propias del algoritmo
    seconds: float = 0.0              # tiempo de cómputo dedicado a la iteración
    iteration_episodes: int = 0       # episodios simulados en esta iteración
    stalls: int = 0                   # episodios cortados por no avanzar
    path_efficiency: float = 0.0      # camino más corto / recorrido, media de los episodios que llegaron
    min_clearance: float = 0.0        # distancia mínima a un obstáculo, media por episodio
    validation_episodes: int = 0
    validation_collisions: int = 0
    validation_efficiency: Optional[float] = None   # eficiencia media de las llegadas en validación
    validation_time: Optional[float] = None         # tiempo medio hasta el destino en validación (s)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "IterationStats":
        return cls(**data)


class TrainingSession:
    def __init__(self, strategy: LearningStrategy, evaluator: Evaluator, scenarios: ScenarioProvider,
                 visible_agents: int = 0, validate_every: int = 1, max_iterations: int = 0,
                 avoidance: str = "learned") -> None:
        self.strategy = strategy
        self.evaluator = evaluator
        self.scenarios = scenarios
        self.visible_agents = max(0, int(visible_agents))
        self.validate_every = int(validate_every)
        self.max_iterations = int(max_iterations)   # 0 = sin límite
        self.avoidance = avoidance                  # algoritmo de evasión con que se arman los controladores
        self._seconds = 0.0
        self._started_at = 0.0
        self.history: List[IterationStats] = []
        self.evaluations = 0
        self.episodes = 0
        self.best_solution: Any = None
        self.best_fitness: Optional[float] = None
        self.phase = IDLE
        self.visible: List[Optional[CandidateEvaluation]] = []
        self._pending: Deque[Candidate] = deque()
        self._results: Dict[int, CandidateResult] = {}
        self._candidate_count = 0
        self._background: Optional[CandidateEvaluation] = None
        self._validation: Optional[CandidateEvaluation] = None
        self._scenario_set: List[Scenario] = []
        self._training_seeds: List[int] = []

    # --- consultas para la interfaz -------------------------------------------
    @property
    def current_iteration(self) -> int:
        """Número de la generación que se está evaluando (1 = la primera)."""
        return self.strategy.iteration + 1

    @property
    def evaluated(self) -> Tuple[int, int]:
        """(candidatos evaluados, candidatos totales) de la iteración en curso."""
        return len(self._results), self._candidate_count

    def is_collected(self, run: CandidateEvaluation) -> bool:
        return run.candidate.id in self._results

    @property
    def finished(self) -> bool:
        """Se alcanzó el límite de iteraciones (nunca, si no hay límite)."""
        return 0 < self.max_iterations <= self.strategy.iteration

    def best_controller(self, map_data: MapData) -> Optional[Controller]:
        """Controlador con la mejor solución de la última iteración, para conducir ``map_data``.

        Lanza ``UnknownScenarioError`` si la solución solo sirve en los mapas con que se entrenó.
        """
        if self.best_solution is None:
            return None
        return self.evaluator.controller_factory(self.best_solution, Scenario(map_data, None, map_data.name))

    def training_maps(self) -> List[MapData]:
        """Mapas de entrenamiento de la iteración en curso (o de la próxima)."""
        return [s.map_data for s in self.scenarios.training_set(self.strategy.iteration)]

    # --- ciclo de entrenamiento -------------------------------------------------
    def begin_iteration(self) -> None:
        self._training_seeds = self.scenarios.training_seeds(self.strategy.iteration)
        self._scenario_set = self.scenarios.training_set(self.strategy.iteration)
        self.strategy.prepare(self._scenario_set)
        candidates = self.strategy.ask()
        self._pending = deque(candidates)
        self._candidate_count = len(candidates)
        self._results = {}
        self._background = None
        self._validation = None
        self.visible = [self._next_run() for _ in range(self.visible_agents)]
        self.phase = EVALUATING

    def _next_run(self, from_end: bool = False) -> Optional[CandidateEvaluation]:
        if not self._pending:
            return None
        candidate = self._pending.pop() if from_end else self._pending.popleft()
        return self.evaluator.start(candidate, self._scenario_set)

    def advance(self, visible_steps: int = 1, time_budget: float = 0.0) -> Optional[IterationStats]:
        """Avanza un poco el entrenamiento y vuelve enseguida.

        Los candidatos visibles avanzan ``visible_steps`` pasos de simulación;
        el resto se evalúa sin dibujarse durante ``time_budget`` segundos como
        máximo. Devuelve las estadísticas cuando la iteración acaba de terminar
        (la siguiente empezará en la próxima llamada); si no, ``None``.
        """
        started = self._started_at = time.perf_counter()
        try:
            return self._advance(visible_steps, started + time_budget)
        finally:
            if self.phase != IDLE:      # al cerrar la iteración el tiempo ya quedó en sus estadísticas
                self._seconds += time.perf_counter() - started

    def _advance(self, visible_steps: int, deadline: float) -> Optional[IterationStats]:
        if self.phase == IDLE:
            self.begin_iteration()
        if self.phase == EVALUATING:
            self._advance_visible(visible_steps)
            self._advance_background(deadline)
            if len(self._results) == self._candidate_count:
                self._begin_validation()
        if self.phase == VALIDATING:
            run = self._validation
            while run is not None and not run.done:
                self._step_many(run, BACKGROUND_CHUNK)
                if time.perf_counter() >= deadline:
                    break
            if run is None or run.done:
                return self._finish_iteration()
        return None

    def run_iteration(self) -> IterationStats:
        """Evalúa una iteración completa (bloqueante). Mismo código que con ventana."""
        while True:
            stats = self.advance(visible_steps=64, time_budget=0.05)
            if stats is not None:
                return stats

    @staticmethod
    def _step_many(run: CandidateEvaluation, steps: int) -> None:
        for _ in range(steps):
            if run.done:
                break
            run.step()

    def _advance_visible(self, steps: int) -> None:
        for i, run in enumerate(self.visible):
            if run is None or self.is_collected(run):
                replacement = self._next_run()
                if replacement is None:
                    continue   # no quedan candidatos: el último queda a la vista
                self.visible[i] = run = replacement
            self._step_many(run, steps)
            if run.done:
                self._results[run.candidate.id] = run.result()

    def _advance_background(self, deadline: float) -> None:
        while True:
            if self._background is None:
                self._background = self._next_run(from_end=True)
                if self._background is None:
                    return
            self._step_many(self._background, BACKGROUND_CHUNK)
            if self._background.done:
                self._results[self._background.candidate.id] = self._background.result()
                self._background = None
            if time.perf_counter() >= deadline:
                return

    def _ordered_results(self) -> List[CandidateResult]:
        return [self._results[i] for i in sorted(self._results)]

    def _begin_validation(self) -> None:
        self.phase = VALIDATING
        due = self.validate_every > 0 and self.current_iteration % self.validate_every == 0
        if due and self.strategy.generalizes and self.scenarios.validation_count > 0:
            best = max(self._ordered_results(), key=lambda r: r.fitness)
            self._validation = self.evaluator.start(
                Candidate(-1, best.candidate.solution), self.scenarios.validation_set()
            )

    def _finish_iteration(self) -> IterationStats:
        results = self._ordered_results()
        best = max(results, key=lambda r: r.fitness)
        validation = self._validation.result() if self._validation is not None else None
        self.best_solution = copy.deepcopy(best.candidate.solution)
        self.best_fitness = best.fitness
        self.strategy.tell(results)      # recién aquí nace la siguiente generación
        episodes = [e for r in results for e in r.episodes]
        fitness = [r.fitness for r in results]
        self.evaluations += len(results)
        self.episodes += len(episodes)
        count = max(len(episodes), 1)
        arrived = [e for e in episodes if e.reached_goal]
        checked = validation.episodes if validation else []
        checked_ok = [e for e in checked if e.reached_goal]
        stats = IterationStats(
            iteration=self.strategy.iteration,
            evaluations=self.evaluations,
            episodes=self.episodes,
            best_fitness=best.fitness,
            mean_fitness=float(sum(fitness) / len(fitness)),
            worst_fitness=float(min(fitness)),
            success_rate=sum(e.reached_goal for e in episodes) / count,
            collisions=sum(e.collided for e in episodes),
            mean_distance=sum(e.distance for e in episodes) / count,
            mean_time=sum(e.time for e in episodes) / count,
            validation_fitness=validation.fitness if validation else None,
            validation_success_rate=(
                sum(e.reached_goal for e in validation.episodes) / max(len(validation.episodes), 1)
                if validation else None
            ),
            training_seeds=list(self._training_seeds),
            strategy={k: float(v) for k, v in self.strategy.statistics().items()},
            seconds=self._seconds + (time.perf_counter() - self._started_at),
            iteration_episodes=len(episodes),
            stalls=sum(e.stalled for e in episodes),
            path_efficiency=sum(e.path_efficiency for e in arrived) / len(arrived) if arrived else 0.0,
            min_clearance=sum(e.min_clearance for e in episodes) / count,
            validation_episodes=len(checked),
            validation_collisions=sum(e.collided for e in checked),
            validation_efficiency=(sum(e.path_efficiency for e in checked_ok) / len(checked_ok)
                                   if checked_ok else None),
            validation_time=sum(e.time for e in checked_ok) / len(checked_ok) if checked_ok else None,
        )
        self._seconds = 0.0
        self.history.append(stats)
        self.phase = IDLE
        return stats

    # --- persistencia --------------------------------------------------------------
    def get_state(self) -> Tuple[dict, Dict[str, np.ndarray]]:
        """Estado al límite entre iteraciones (una iteración a medias no se guarda)."""
        state = self.strategy.get_state()
        meta = {
            "strategy_name": self.strategy.name,
            "strategy": state.meta,
            "history": [h.to_dict() for h in self.history],
            "evaluations": self.evaluations,
            "episodes": self.episodes,
            "scenarios": self.scenarios.state(),
        }
        return meta, {ARRAY_PREFIX + key: value for key, value in state.arrays.items()}

    def set_state(self, meta: dict, arrays: Dict[str, np.ndarray]) -> None:
        if meta["strategy_name"] != self.strategy.name:
            raise ValueError(
                f"El checkpoint es de la estrategia '{meta['strategy_name']}', no de '{self.strategy.name}'"
            )
        own = {k[len(ARRAY_PREFIX):]: v for k, v in arrays.items() if k.startswith(ARRAY_PREFIX)}
        self.strategy.set_state(StrategyState(meta["strategy"], own))
        self.history = [IterationStats.from_dict(h) for h in meta["history"]]
        self.evaluations = meta["evaluations"]
        self.episodes = meta["episodes"]
        best = self.strategy.best()
        self.best_solution, self.best_fitness = best if best is not None else (None, None)
        self.phase = IDLE
        self.visible = []


class TrainingLog:
    """Registro del experimento: una línea JSON por iteración (incluye las semillas usadas)."""

    def __init__(self, path) -> None:
        from pathlib import Path

        self.path = Path(path)

    def append(self, stats: IterationStats) -> None:
        import json

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(stats.to_dict()) + "\n")
