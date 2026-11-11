"""Convierte una ``Observation`` en el vector de entrada de una política.

Es la única fuente de verdad sobre las dimensiones de entrada: cualquier
módulo que necesite el tamaño debe consultar ``ObservationBuilder.size``.
"""
from __future__ import annotations

import math

import numpy as np

from control.controller import Observation, ROUTE_FOLLOWING

_SCALARS = (
    "heading_sin", "heading_cos", "speed",
    "goal_distance", "goal_sin", "goal_cos",
    "waypoint_distance", "waypoint_sin", "waypoint_cos",
    "deviation", "path_sin", "path_cos",
    "mode",
)


class ObservationBuilder:
    """Vector acotado en [-1, 1].

    El LiDAR se codifica como proximidad (1 - distancia normalizada): 0 cuando
    no hay nada dentro del alcance y 1 cuando el obstáculo toca el vehículo.
    """

    def __init__(
        self,
        num_rays: int,
        use_previous_lidar: bool = True,
        distance_scale: float = 10.0,
        deviation_scale: float = 2.0,
    ) -> None:
        self.num_rays = int(num_rays)
        self.use_previous_lidar = bool(use_previous_lidar)
        self.distance_scale = float(distance_scale)
        self.deviation_scale = float(deviation_scale)
        names = [f"lidar_{i}" for i in range(self.num_rays)]
        if self.use_previous_lidar:
            names += [f"lidar_prev_{i}" for i in range(self.num_rays)]
        self.feature_names = names + list(_SCALARS)

    @property
    def size(self) -> int:
        return len(self.feature_names)

    def build(self, obs: Observation) -> np.ndarray:
        n = self.num_rays
        if obs.lidar.shape[0] != n:
            raise ValueError(f"Se esperaban {n} rayos LiDAR y llegaron {obs.lidar.shape[0]}")
        vector = np.empty(self.size)
        vector[:n] = 1.0 - obs.lidar
        i = n
        if self.use_previous_lidar:
            vector[n:2 * n] = 1.0 - obs.lidar_previous
            i = 2 * n
        max_speed = obs.max_speed if obs.max_speed > 0 else 1.0
        vector[i:] = (
            math.sin(obs.heading), math.cos(obs.heading),
            max(-1.0, min(1.0, obs.speed / max_speed)),
            min(1.0, obs.goal_distance / self.distance_scale),
            math.sin(obs.goal_bearing), math.cos(obs.goal_bearing),
            min(1.0, obs.waypoint_distance / self.distance_scale),
            math.sin(obs.waypoint_bearing), math.cos(obs.waypoint_bearing),
            max(-1.0, min(1.0, obs.path_deviation / self.deviation_scale)),
            math.sin(obs.path_heading_error), math.cos(obs.path_heading_error),
            1.0 if obs.navigation_mode == ROUTE_FOLLOWING else 0.0,
        )
        return vector
