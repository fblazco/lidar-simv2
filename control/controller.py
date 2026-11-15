"""Contrato entre el simulador y cualquier controlador de un móvil.

Este módulo solo define datos e interfaces. No importa Pygame, ni el
simulador, ni ningún algoritmo de aprendizaje: es lo único que el simulador
necesita conocer de quien decide las acciones de un vehículo.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np

FREE_NAVIGATION = "free"      # llegar al destino evitando obstáculos
ROUTE_FOLLOWING = "route"     # seguir los caminos, pudiendo apartarse y volver
NAVIGATION_MODES = (FREE_NAVIGATION, ROUTE_FOLLOWING)


@dataclass(frozen=True)
class Action:
    """Orden de control normalizada."""

    steering: float = 0.0       # dirección, -1 (izquierda) .. 1 (derecha)
    acceleration: float = 0.0   # 1 acelera a fondo, -1 frena a fondo

    def clipped(self) -> "Action":
        return Action(
            float(max(-1.0, min(1.0, self.steering))),
            float(max(-1.0, min(1.0, self.acceleration))),
        )


@dataclass(frozen=True, eq=False)
class Observation:
    """Lo que un móvil percibe en un instante. Solo valores numéricos.

    Los ángulos ``*_bearing`` y ``path_heading_error`` son relativos a la
    orientación del vehículo, en radianes dentro de (-pi, pi].
    """

    lidar: np.ndarray             # distancias normalizadas 0..1, una por rayo
    lidar_previous: np.ndarray    # medición del paso anterior
    heading: float                # orientación absoluta (rad)
    speed: float                  # velocidad lineal (unidades/s)
    max_speed: float
    goal_distance: float
    goal_bearing: float
    waypoint_distance: float      # siguiente waypoint (punto adelantado de la ruta)
    waypoint_bearing: float
    path_deviation: float         # distancia lateral con signo al camino (0 en modo libre)
    path_heading_error: float     # dirección del camino respecto del vehículo
    navigation_mode: str          # FREE_NAVIGATION o ROUTE_FOLLOWING
    lidar_range: float            # alcance máximo del sensor (unidades)
    time: float                   # tiempo de simulación (s)
    x: float = 0.0                # posición absoluta (unidades del mundo)
    y: float = 0.0


class Controller(ABC):
    """Decide la acción de un móvil a partir de sus observaciones."""

    def reset(self) -> None:
        """Se llama al comenzar cada episodio."""

    def observe(self, observation: Observation) -> None:
        """Recibe cada observación antes de ``act`` (para controladores con memoria)."""

    @abstractmethod
    def act(self, observation: Observation) -> Action:
        """Devuelve la acción a ejecutar en este paso."""
