"""Colonia de hormigas que traza una ruta sobre la grilla de cada mapa.

Planteo clásico de ACO para planificación de caminos: cada hormiga avanza de
celda en celda desde el inicio hasta el destino, sin repetir celdas, eligiendo
la siguiente con probabilidad proporcional a ``feromona^alpha * heurística^beta``.
La feromona vive en las celdas de cada mapa; se evapora en cada iteración y las
mejores rutas (según el fitness obtenido al conducirlas en el simulador)
depositan sobre sus celdas.

Las hormigas conocen el plano estático del mapa (grilla, inicio, destino,
obstáculos fijos y camino dibujado). Los obstáculos móviles no figuran en el
plano: su efecto llega solo a través del fitness.

Como la ruta la conducirá un vehículo que no puede girar sobre sí mismo, una
hormiga cambia de rumbo como mucho 45° entre un paso y el siguiente.

Lo aprendido es una ruta por mapa, así que no sirve en mapas no vistos.
"""
from __future__ import annotations

import copy
import math
from dataclasses import dataclass, fields
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from optimization.strategy import Candidate, CandidateResult, LearningStrategy, StrategyState

Cell = Tuple[int, int]
MOVES = ((1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1))
GAIN_OFFSET = 1.5     # desplaza la mejora de potencial para que retroceder sea posible pero improbable
ETA_FLOOR = 0.05
MAX_DEAD_ENDS = 60
GENTLE_TURNS = (0, 1, 7)          # diferencia de rumbo permitida entre pasos: recto o 45° a cada lado
WIDE_TURNS = (0, 1, 2, 6, 7)      # hasta 90°: solo para el primer paso y para entrar al destino


@dataclass
class ACORoutesConfig:
    alpha: float = 1.0              # peso de la feromona
    beta: float = 3.0               # peso de la información heurística
    evaporation: float = 0.2
    elite_ants: int = 5             # rutas que depositan en cada mapa, de la mejor a la peor
    tau_min: float = 0.01
    tau_max: float = 1.0
    route_attraction: float = 1.5   # costo de alejarse una celda del camino dibujado (modo ruta)
    clearance: float = 0.7          # factor heurístico de las celdas pegadas a un obstáculo fijo

    @classmethod
    def from_dict(cls, data: dict) -> "ACORoutesConfig":
        return cls(**{f.name: data[f.name] for f in fields(cls) if f.name in data})


class MapColony:
    """Feromonas y construcción de rutas para un mapa."""

    def __init__(self, map_data: Any, config: ACORoutesConfig) -> None:
        self.config = config
        self.cols, self.rows = map_data.cols, map_data.rows
        self.start, self.goal = map_data.start, map_data.goal
        self.start_direction = int(round(map_data.start_heading / (math.pi / 4.0))) % len(MOVES)
        self.pheromone = np.full((self.rows, self.cols), config.tau_max)
        self.best_route: Optional[List[Cell]] = None
        self.best_score: Optional[float] = None
        direct = max(abs(self.goal[0] - self.start[0]), abs(self.goal[1] - self.start[1]))
        self.max_steps = 10 + 2 * max(direct, len(map_data.path_cells()))   # una ruta mucho más larga no sirve
        blocked = set(map_data.static_obstacles)
        potential = self._potential(map_data)
        self._edges: Dict[int, List[Tuple[int, int, float]]] = {}   # (rumbo, celda vecina, heurística^beta)
        for row in range(self.rows):
            for col in range(self.cols):
                if (col, row) not in blocked:
                    self._edges[row * self.cols + col] = self._moves_from(col, row, blocked, potential)

    def _potential(self, map_data: Any) -> np.ndarray:
        """Cuánto falta para llegar desde cada celda; las hormigas prefieren bajarlo."""
        cols, rows = np.meshgrid(np.arange(self.cols), np.arange(self.rows))
        path = map_data.path_cells()
        if len(path) <= 2:      # navegación libre: distancia en línea recta al destino
            return np.hypot(cols - self.goal[0], rows - self.goal[1])
        waypoints = np.array(path[::-1])      # en modo ruta: tramo restante del camino + alejamiento de él
        distance = np.hypot(cols[..., None] - waypoints[:, 0], rows[..., None] - waypoints[:, 1])
        remaining = distance.argmin(axis=-1)  # con el camino invertido, el índice es lo que falta recorrer
        return remaining + self.config.route_attraction * distance.min(axis=-1)

    def _moves_from(self, col: int, row: int, blocked: set,
                    potential: np.ndarray) -> List[Tuple[int, int, float]]:
        moves = []
        for direction, (dc, dr) in enumerate(MOVES):
            c, r = col + dc, row + dr
            if not (0 <= c < self.cols and 0 <= r < self.rows) or (c, r) in blocked:
                continue
            if dc and dr and ((c, row) in blocked or (col, r) in blocked):
                continue                      # en diagonal no se roza la esquina de un obstáculo
            eta = max(potential[row, col] - potential[r, c] + GAIN_OFFSET, ETA_FLOOR)
            if any((c + i, r + j) in blocked for i, j in MOVES):
                eta *= self.config.clearance
            moves.append((direction, r * self.cols + c, float(eta ** self.config.beta)))
        return moves

    def construct(self, rng: np.random.Generator) -> List[Cell]:
        """Recorrido de una hormiga. Si queda encerrada retrocede; si no llega, devuelve lo recorrido."""
        cols = self.cols
        trail = (self.pheromone ** self.config.alpha).ravel().tolist()
        draws = rng.random(2 * self.max_steps).tolist()
        start = self.start[1] * cols + self.start[0]
        goal = self.goal[1] * cols + self.goal[0]
        path, headings, visited = [start], [None], {start}     # headings[i]: rumbo con que se llegó a path[i]
        current, heading, used, dead_ends = start, None, 0, 0
        while current != goal and len(path) < self.max_steps and used < len(draws):
            reference, turns = (self.start_direction, WIDE_TURNS) if heading is None else (heading, GENTLE_TURNS)
            options = [(cell, direction, trail[cell] * eta) for direction, cell, eta in self._edges[current]
                       if cell not in visited and (direction - reference) % 8 in turns]
            arrival = [(cell, direction, 1.0) for direction, cell, _ in self._edges[current]
                       if cell == goal and (direction - reference) % 8 in WIDE_TURNS]
            if arrival:                               # con el destino al lado se entra directamente
                options = arrival
            if not options and heading is None:      # arranque encajonado: se permite cualquier salida
                options = [(cell, direction, trail[cell] * eta) for direction, cell, eta in self._edges[current]
                           if cell not in visited]
            if not options:
                dead_ends += 1
                if len(path) == 1 or dead_ends > MAX_DEAD_ENDS:
                    break
                path.pop()
                headings.pop()
                current, heading = path[-1], headings[-1]
                continue
            pick = draws[used] * sum(weight for _, _, weight in options)
            used += 1
            for current, heading, weight in options:
                pick -= weight
                if pick <= 0.0:
                    break
            path.append(current)
            headings.append(heading)
            visited.add(current)
        return [(cell % cols, cell // cols) for cell in path]

    def update(self, scored_routes: Sequence[Tuple[List[Cell], float]]) -> None:
        """Evaporación y depósito de las mejores rutas de la iteración y de la mejor conocida."""
        cfg = self.config
        ranked = sorted(scored_routes, key=lambda item: -item[1])
        if self.best_score is None or ranked[0][1] > self.best_score:
            self.best_route, self.best_score = list(ranked[0][0]), float(ranked[0][1])
        self.pheromone *= 1.0 - cfg.evaporation
        unit = cfg.evaporation * cfg.tau_max
        elite = max(1, min(cfg.elite_ants, len(ranked)))
        for rank, (route, _) in enumerate(ranked[:elite]):
            self._deposit(route, unit * (elite - rank) / elite)
        self._deposit(self.best_route, unit)
        np.clip(self.pheromone, cfg.tau_min, cfg.tau_max, out=self.pheromone)

    def _deposit(self, route: List[Cell], amount: float) -> None:
        cells = np.array(route)
        self.pheromone[cells[:, 1], cells[:, 0]] += amount

    def heatmap(self) -> np.ndarray:
        """Feromona por celda (filas x columnas) reescalada a 0..1 entre su mínimo y su máximo actuales.

        Así se ve dónde se concentra el rastro aunque todavía quede mucha feromona en todo el mapa.
        """
        low, high = float(self.pheromone.min()), float(self.pheromone.max())
        if high - low < 1e-12:
            return np.zeros_like(self.pheromone)
        return (self.pheromone - low) / (high - low)

    def trail_focus(self) -> float:
        """Fracción de la feromona que está sobre la mejor ruta (1 = colonia totalmente convergida)."""
        surplus = self.pheromone - self.config.tau_min
        total = float(surplus.sum())
        if self.best_route is None or total <= 0.0:
            return 0.0
        cells = np.array(self.best_route)
        return float(surplus[cells[:, 1], cells[:, 0]].sum()) / total


class RouteColonies(LearningStrategy):
    """Una colonia por mapa. Cada hormiga lleva una ruta para cada escenario de la iteración."""

    name = "aco_routes"
    generalizes = False

    def __init__(self, ants: int, config: Optional[ACORoutesConfig] = None, seed: int = 0) -> None:
        self.config = config or ACORoutesConfig()
        self.ants = int(ants)
        self._rng = np.random.default_rng(seed)
        self._iteration = 0
        self._colonies: Dict[str, MapColony] = {}
        self._keys: List[str] = []                       # escenarios de la iteración, en orden
        self._best_routes: Dict[str, List[Cell]] = {}
        self._best_scores: Dict[str, float] = {}
        self._restored: Dict[str, np.ndarray] = {}       # feromonas de un checkpoint, a la espera de su mapa
        self._pending: Optional[List[Candidate]] = None
        self._rng_before_ask: Optional[dict] = None

    @property
    def iteration(self) -> int:
        return self._iteration

    def prepare(self, scenarios: Sequence[Any]) -> None:
        keys = []
        for scenario in scenarios:
            if scenario.key not in self._colonies:
                colony = MapColony(scenario.map_data, self.config)
                saved = self._restored.pop(scenario.key, None)
                if saved is not None and saved.shape == colony.pheromone.shape:
                    colony.pheromone = saved
                if scenario.key in self._best_routes:
                    colony.best_route = self._best_routes[scenario.key]
                    colony.best_score = self._best_scores[scenario.key]
                self._colonies[scenario.key] = colony
            keys.append(scenario.key)
        if keys != self._keys:
            self._keys, self._pending = keys, None

    def ask(self) -> List[Candidate]:
        if not self._keys:
            raise RuntimeError("La colonia de rutas necesita los escenarios: llamar a prepare() antes de ask()")
        if self._pending is None:
            self._rng_before_ask = copy.deepcopy(self._rng.bit_generator.state)
            colonies = [(key, self._colonies[key]) for key in self._keys]
            plans = []
            if all(colony.best_route is not None for _, colony in colonies):
                plans.append({key: list(colony.best_route) for key, colony in colonies})   # mejor ruta de cada mapa
            while len(plans) < self.ants:
                plans.append({key: colony.construct(self._rng) for key, colony in colonies})
            self._pending = [Candidate(i, plan) for i, plan in enumerate(plans)]
        return self._pending

    def tell(self, results: Sequence[CandidateResult]) -> None:
        if sorted(r.candidate.id for r in results) != list(range(self.ants)):
            raise ValueError("Se necesita el resultado de cada hormiga de la iteración, una sola vez")
        if any(len(r.scores) != len(self._keys) for r in results):
            raise ValueError("Cada resultado debe traer el puntaje de cada escenario")
        for index, key in enumerate(self._keys):
            colony = self._colonies[key]
            colony.update([(r.candidate.solution[key], r.scores[index]) for r in results])
            self._best_routes[key], self._best_scores[key] = colony.best_route, colony.best_score
        self._pending = None
        self._iteration += 1

    def best(self) -> Optional[Tuple[Any, float]]:
        if not self._best_routes:
            return None
        keys = [key for key in self._keys if key in self._best_routes] or list(self._best_routes)
        fitness = float(np.mean([self._best_scores[key] for key in keys]))
        return {key: list(route) for key, route in self._best_routes.items()}, fitness

    def cell_heatmap(self, scenario: Any) -> Optional[np.ndarray]:
        colony = self._colonies.get(scenario.key)
        return colony.heatmap() if colony is not None else None

    def statistics(self) -> Dict[str, float]:
        colonies = [self._colonies[key] for key in self._keys]
        lengths = [len(c.best_route) for c in colonies if c.best_route is not None]
        return {
            "alpha": self.config.alpha,
            "beta": self.config.beta,
            "evaporation": self.config.evaporation,
            "route_length": float(np.mean(lengths)) if lengths else 0.0,
            "trail_focus": float(np.mean([c.trail_focus() for c in colonies])) if colonies else 0.0,
        }

    def get_state(self) -> StrategyState:
        rng = self._rng_before_ask if self._pending is not None else self._rng.bit_generator.state
        meta = {
            "iteration": self._iteration,
            "rng": rng,
            "routes": {key: [list(cell) for cell in route] for key, route in self._best_routes.items()},
            "scores": dict(self._best_scores),
        }
        arrays = {f"pheromone.{key}": colony.pheromone for key, colony in self._colonies.items()}
        arrays.update({f"pheromone.{key}": saved for key, saved in self._restored.items()})
        return StrategyState(meta, arrays)

    def set_state(self, state: StrategyState) -> None:
        self._iteration = int(state.meta["iteration"])
        self._rng.bit_generator.state = state.meta["rng"]
        self._best_routes = {key: [tuple(cell) for cell in route] for key, route in state.meta["routes"].items()}
        self._best_scores = {key: float(score) for key, score in state.meta["scores"].items()}
        prefix = "pheromone."
        self._restored = {name[len(prefix):]: np.array(values, dtype=float)
                          for name, values in state.arrays.items() if name.startswith(prefix)}
        self._colonies, self._keys, self._pending = {}, [], None
