"""Evaluación de candidatos en el simulador, paso a paso.

Es independiente del algoritmo: recibe candidatos con soluciones opacas, una
``controller_factory`` que las convierte en controladores y un conjunto de
escenarios. El mismo código sirve para evaluar con o sin renderizado: quien
quiera mostrar un candidato solo lee ``CandidateEvaluation.simulation``.
"""
from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Any, Callable, List, Optional, Sequence

from control.controller import Controller
from optimization.fitness import EpisodeMetrics, FitnessFunction
from optimization.strategy import Candidate, CandidateResult
from simulation.environment import Simulation
from simulation.factory import SimulationFactory
from simulation.map_data import MapData
from simulation.vehicle import Status


@dataclass(frozen=True)
class Scenario:
    map_data: MapData
    seed: Optional[int] = None   # semilla del generador (None para mapas dibujados a mano)
    label: str = ""


@dataclass
class EvaluationSettings:
    stall_time: float = 4.0       # segundos sin avanzar que cortan el episodio
    stall_distance: float = 0.5   # avance mínimo (unidades) que reinicia ese reloj

    @classmethod
    def from_dict(cls, data: dict) -> "EvaluationSettings":
        return cls(**{f.name: data[f.name] for f in fields(cls) if f.name in data})


class EpisodeRunner:
    """Un episodio: un móvil en un escenario, con registro de métricas."""

    def __init__(self, simulation: Simulation, settings: EvaluationSettings) -> None:
        self.simulation = simulation
        self.mobile = simulation.mobiles[0]
        self.settings = settings
        self.stalled = False
        self._steps = 0
        self._deviation = 0.0
        self._steering = 0.0
        self._acceleration = 0.0
        self._stall_progress = settings.stall_distance / max(simulation.world.route.length, 1e-9)
        self._mark_progress = self.mobile.navigation.progress
        self._mark_time = 0.0

    @property
    def done(self) -> bool:
        return self.stalled or self.simulation.done

    def step(self) -> None:
        if self.done:
            return
        mobile = self.mobile
        previous = mobile.last_action
        self.simulation.step()
        action = mobile.last_action
        if self._steps > 0:
            self._steering += abs(action.steering - previous.steering)
            self._acceleration += abs(action.acceleration - previous.acceleration)
        self._steps += 1
        self._deviation += abs(mobile.navigation.deviation)
        if mobile.active:
            progress = mobile.navigation.progress
            if progress >= self._mark_progress + self._stall_progress:
                self._mark_progress, self._mark_time = progress, self.simulation.time
            elif self.simulation.time - self._mark_time >= self.settings.stall_time - 1e-9:
                self.stalled = True

    def metrics(self) -> EpisodeMetrics:
        mobile, changes = self.mobile, max(self._steps - 1, 1)
        return EpisodeMetrics(
            progress=mobile.navigation.progress,
            reached_goal=mobile.status is Status.REACHED_GOAL,
            collided=mobile.status is Status.COLLIDED,
            stalled=self.stalled,
            time=self.simulation.time,
            time_limit=self.simulation.config.max_time,
            distance=mobile.distance_traveled,
            mean_deviation=self._deviation / max(self._steps, 1),
            steering_change=self._steering / changes,
            acceleration_change=self._acceleration / changes,
        )


class CandidateEvaluation:
    """Evalúa un candidato en todos sus escenarios, un paso de simulación por llamada."""

    def __init__(self, candidate: Candidate, controller: Controller, scenarios: Sequence[Scenario],
                 simulation_factory: SimulationFactory, fitness: FitnessFunction,
                 settings: EvaluationSettings) -> None:
        self.candidate = candidate
        self.controller = controller
        self.scenarios = list(scenarios)
        self._simulation_factory = simulation_factory
        self._fitness = fitness
        self._settings = settings
        self.episodes: List[EpisodeMetrics] = []
        self.scores: List[float] = []
        self.runner = self._start_episode(0)

    def _start_episode(self, index: int) -> EpisodeRunner:
        simulation = self._simulation_factory.create(self.scenarios[index].map_data, [self.controller])
        return EpisodeRunner(simulation, self._settings)

    @property
    def simulation(self) -> Simulation:
        """Simulación del episodio en curso (cada evaluación tiene su propio mundo)."""
        return self.runner.simulation

    @property
    def episode_count(self) -> int:
        return len(self.scenarios)

    @property
    def episode_index(self) -> int:
        return min(len(self.episodes), self.episode_count - 1)

    @property
    def scenario(self) -> Scenario:
        return self.scenarios[self.episode_index]

    @property
    def done(self) -> bool:
        return len(self.episodes) == self.episode_count

    @property
    def partial_fitness(self) -> float:
        """Fitness provisional: episodios terminados más el estado del episodio en curso."""
        scores = list(self.scores)
        if not self.done:
            scores.append(self._fitness(self.runner.metrics()))
        return self._fitness.aggregate(scores)

    def step(self) -> None:
        if self.done:
            return
        self.runner.step()
        if self.runner.done:
            metrics = self.runner.metrics()
            self.episodes.append(metrics)
            self.scores.append(self._fitness(metrics))
            if not self.done:
                self.runner = self._start_episode(len(self.episodes))

    def result(self) -> CandidateResult:
        return CandidateResult(self.candidate, self._fitness.aggregate(self.scores), list(self.episodes))


class Evaluator:
    def __init__(self, simulation_factory: SimulationFactory, controller_factory: Callable[[Any], Controller],
                 fitness: FitnessFunction, settings: Optional[EvaluationSettings] = None) -> None:
        self.simulation_factory = simulation_factory
        self.controller_factory = controller_factory
        self.fitness = fitness
        self.settings = settings or EvaluationSettings()

    def start(self, candidate: Candidate, scenarios: Sequence[Scenario]) -> CandidateEvaluation:
        """Evaluación por pasos (para repartir el trabajo entre cuadros o mostrarla)."""
        controller = self.controller_factory(candidate.solution)
        return CandidateEvaluation(candidate, controller, scenarios, self.simulation_factory,
                                   self.fitness, self.settings)

    def evaluate(self, candidates: Sequence[Candidate], scenarios: Sequence[Scenario]) -> List[CandidateResult]:
        """Evaluación completa y bloqueante: todos los candidatos en los mismos escenarios."""
        results = []
        for candidate in candidates:
            run = self.start(candidate, scenarios)
            while not run.done:
                run.step()
            results.append(run.result())
        return results
