"""Controlador por tabla de reglas: cada situación discreta tiene asignada una maniobra.

La situación resume lo que percibe el vehículo (hacia dónde queda el siguiente
waypoint y qué tan cerca hay algo a la izquierda, al frente y a la derecha). La
tabla dice qué maniobra aplicar en cada una. No depende de ningún algoritmo:
cualquier optimizador de asignaciones discretas puede rellenarla.
"""
from __future__ import annotations

import math
from bisect import bisect_right
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

import numpy as np

from control.controller import Action, Controller, Observation
from control.rays import relative_ray_angles

STEERINGS = (-1.0, -0.5, 0.0, 0.5, 1.0)
THROTTLES = (1.0, 0.2, -1.0)                      # acelerar, avanzar despacio, frenar
BEARING_EDGES_DEG = (-50.0, -12.0, 12.0, 50.0)    # límites entre: muy a la izquierda, izquierda, al frente...
SIDE_SECTOR_DEG = (15.0, 75.0)                    # los sectores laterales cubren de 15° a 75° a cada lado
NEAR, MID, FREE = 0, 1, 2                         # niveles de cercanía de un sector
LEVELS = 3


def default_maneuvers() -> List[Action]:
    """Las 15 maniobras posibles: 5 direcciones por 3 niveles de aceleración."""
    return [Action(steering, throttle) for throttle in THROTTLES for steering in STEERINGS]


class ObservationDiscretizer:
    """Convierte una ``Observation`` en el índice de una situación discreta.

    Los ángulos positivos quedan del lado hacia el que gira una dirección positiva.
    """

    def __init__(self, num_rays: int, fov_deg: float = 360.0, near_distance: float = 1.0,
                 mid_distance: float = 2.5) -> None:
        self.near_distance = float(near_distance)
        self.mid_distance = float(mid_distance)
        angles = np.round(np.degrees(relative_ray_angles(num_rays, fov_deg)), 6)   # relativos al frente
        inner, outer = SIDE_SECTOR_DEG
        self._sectors = (
            np.flatnonzero((angles >= -outer) & (angles < -inner)),    # izquierda
            np.flatnonzero(np.abs(angles) <= inner),                    # frente
            np.flatnonzero((angles > inner) & (angles <= outer)),      # derecha
        )
        self.bearings = len(BEARING_EDGES_DEG) + 1
        self.size = self.bearings * LEVELS ** 3

    def _level(self, lidar: np.ndarray, sector: np.ndarray, lidar_range: float) -> int:
        if sector.size == 0:
            return FREE
        distance = float(lidar[sector].min()) * lidar_range
        return NEAR if distance < self.near_distance else MID if distance < self.mid_distance else FREE

    def encode(self, obs: Observation) -> int:
        bearing = bisect_right(BEARING_EDGES_DEG, math.degrees(obs.waypoint_bearing))
        left, front, right = (self._level(obs.lidar, sector, obs.lidar_range) for sector in self._sectors)
        return ((bearing * LEVELS + left) * LEVELS + front) * LEVELS + right

    def decode(self, state: int) -> Tuple[int, int, int, int]:
        """(dirección del objetivo, izquierda, frente, derecha) de una situación."""
        state, right = divmod(state, LEVELS)
        state, front = divmod(state, LEVELS)
        bearing, left = divmod(state, LEVELS)
        return bearing, left, front, right


@dataclass
class RuleTable:
    """Una maniobra por situación, más las veces que cada situación se presentó al conducir."""

    actions: np.ndarray
    visits: Optional[np.ndarray] = None

    def __post_init__(self) -> None:
        self.actions = np.asarray(self.actions, dtype=int)
        if self.visits is None:
            self.visits = np.zeros(self.actions.shape[0], dtype=int)


class RuleTableController(Controller):
    def __init__(self, table: RuleTable, discretizer: ObservationDiscretizer, maneuvers: Sequence[Action]) -> None:
        self.table = table
        self.discretizer = discretizer
        self.maneuvers = list(maneuvers)

    def act(self, observation: Observation) -> Action:
        state = self.discretizer.encode(observation)
        self.table.visits[state] += 1
        return self.maneuvers[self.table.actions[state]]


class RuleControllerFactory:
    """Construye controladores a partir de una ``RuleTable``."""

    def __init__(self, discretizer: ObservationDiscretizer, maneuvers: Optional[Sequence[Action]] = None) -> None:
        self.discretizer = discretizer
        self.maneuvers = list(maneuvers) if maneuvers is not None else default_maneuvers()

    @property
    def n_states(self) -> int:
        return self.discretizer.size

    @property
    def n_actions(self) -> int:
        return len(self.maneuvers)

    def __call__(self, table: RuleTable) -> RuleTableController:
        if table.actions.shape[0] != self.n_states:
            raise ValueError(f"La tabla tiene {table.actions.shape[0]} situaciones y se esperaban {self.n_states}")
        return RuleTableController(table, self.discretizer, self.maneuvers)


def build_rule_controller_factory(config: dict) -> RuleControllerFactory:
    """Fábrica de controladores de reglas según las secciones lidar y rule_policy."""
    lidar = config["lidar"]
    return RuleControllerFactory(ObservationDiscretizer(lidar["num_rays"], lidar["fov_deg"], **config["rule_policy"]))
