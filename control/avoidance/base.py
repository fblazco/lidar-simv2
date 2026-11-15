"""Contrato de la capa de evasión de obstáculos.

Un ``ObstacleAvoider`` no decide a dónde ir: recibe lo que propone el
controlador de navegación y lo corrige según lo que ve el LiDAR. Por eso se
puede combinar con cualquier controlador (red neuronal, tabla de reglas,
seguidor de rutas, referencia sin aprendizaje) mediante ``AvoidanceController``.
"""
from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Optional

import numpy as np

from control.controller import Action, Controller, Observation

INTENT_SPAN = math.pi / 2.0    # una dirección a fondo significa "quiero ir 90° hacia ese lado"
STEERING_GAIN = 2.0            # dirección a fondo con ~30° de error de rumbo
SPEED_GAIN = 1.5
GOAL_MARGIN = 0.3              # holgura para dar por despejado el tramo final hasta el destino


def intended_direction(action: Action) -> float:
    """Hacia dónde quiere ir el controlador de navegación, como ángulo relativo al frente."""
    return action.steering * INTENT_SPAN


def steering_towards(direction: float) -> float:
    """Orden de dirección para encarar un ángulo relativo al frente."""
    return max(-1.0, min(1.0, STEERING_GAIN * direction))


def speed_guard(observation: Observation, limit: float) -> float:
    """Aceleración que mantiene la velocidad por debajo de ``limit``."""
    return max(-1.0, min(1.0, SPEED_GAIN * (limit - observation.speed)))


def goal_in_sight(observation: Observation, angles: np.ndarray, reach: float) -> bool:
    """El destino está más cerca que cualquier obstáculo en el corredor que lleva hasta él.

    Evita el defecto clásico de los métodos reactivos: no poder llegar a un
    destino que tiene una pared justo detrás.
    """
    distance = observation.lidar * observation.lidar_range
    relative = angles - observation.goal_bearing
    relative = (relative + math.pi) % (2.0 * math.pi) - math.pi
    corridor = (np.abs(relative) < math.pi / 2.0) & (distance * np.abs(np.sin(relative)) < reach)
    if not corridor.any():
        return True
    return float((distance * np.cos(relative))[corridor].min()) > observation.goal_distance + GOAL_MARGIN


class ObstacleAvoider(ABC):
    def reset(self) -> None:
        """Se llama al comenzar cada episodio."""

    @abstractmethod
    def adjust(self, observation: Observation, proposal: Action) -> Action:
        """Corrige la acción propuesta por la navegación para no chocar."""


class AvoidanceController(Controller):
    """Navegación + evasión: el controlador interno propone y el evasor corrige."""

    def __init__(self, inner: Controller, avoider: ObstacleAvoider) -> None:
        self.inner = inner
        self.avoider = avoider

    @property
    def planned_path(self):
        return getattr(self.inner, "planned_path", None)

    def reset(self) -> None:
        self.inner.reset()
        self.avoider.reset()

    def observe(self, observation: Observation) -> None:
        self.inner.observe(observation)

    def act(self, observation: Observation) -> Action:
        return self.avoider.adjust(observation, self.inner.act(observation).clipped())


def with_avoidance(controller_factory: Callable[[Any, Any], Controller],
                   make_avoider: Callable[[], ObstacleAvoider]) -> Callable[[Any, Any], Controller]:
    """Fábrica de controladores que envuelve cada uno con un evasor propio."""
    return lambda solution, scenario: AvoidanceController(controller_factory(solution, scenario), make_avoider())


@dataclass(frozen=True)
class AvoidancePlugin:
    name: str                                            # identificador usado en la configuración
    label: str
    short_label: str
    description: str
    build: Callable[[dict], Optional[ObstacleAvoider]]   # None = no se agrega ninguna capa
