"""Follow the Gap (FTG): encarar el hueco más ancho entre los obstáculos.

Sigue el método de Sezer y Gökaşan (2012):

1. Los rayos del LiDAR más cortos que ``free_distance`` son obstáculos.
2. Cada obstáculo se agranda con el radio del vehículo (más un margen), de modo
   que el vehículo pueda tratarse como un punto.
3. Los tramos consecutivos de rayos que quedan libres son los huecos.
4. Se elige el hueco más ancho y se toma su centro.
5. El rumbo final pondera ese centro con la dirección deseada: cuanto más cerca
   está el obstáculo, más pesa el hueco.

       rumbo = (alfa/d_min * centro_del_hueco + beta * deseada) / (alfa/d_min + beta)

La velocidad se limita en proporción a la distancia al obstáculo más cercano.
"""
from __future__ import annotations

import math
from typing import List, Optional, Tuple

import numpy as np

from control.avoidance.base import (AvoidancePlugin, ObstacleAvoider, goal_in_sight, intended_direction,
                                    speed_guard, steering_towards)
from control.controller import Action, Observation
from control.rays import relative_ray_angles

MIN_SPEED_FRACTION = 0.25


class FollowTheGap(ObstacleAvoider):
    def __init__(self, num_rays: int, fov_deg: float = 360.0, robot_radius: float = 0.35,
                 free_distance: float = 2.5, safety_margin: float = 0.25, alpha: float = 2.5,
                 beta: float = 1.0, view_deg: float = 200.0) -> None:
        self.free_distance = free_distance          # más lejos que esto, un rayo cuenta como libre
        self.reach = robot_radius + safety_margin   # cuánto se agranda cada obstáculo
        self.alpha = alpha                          # peso del hueco
        self.beta = beta                            # peso de la dirección deseada
        angles = relative_ray_angles(num_rays, fov_deg)
        self._all_angles = angles
        self._half_view = math.radians(view_deg) / 2.0
        inside = np.flatnonzero(np.abs(angles) <= self._half_view)
        self._view = inside[np.argsort(angles[inside])]      # rayos del campo de visión, de izquierda a derecha
        self._angles = angles[self._view]
        self._last_heading: Optional[float] = None

    def reset(self) -> None:
        self._last_heading = None

    @staticmethod
    def _gaps(free: np.ndarray) -> List[Tuple[int, int]]:
        """Tramos (primero, último) de rayos libres consecutivos."""
        gaps, start = [], None
        for i, is_free in enumerate(free):
            if is_free and start is None:
                start = i
            elif not is_free and start is not None:
                gaps.append((start, i - 1))
                start = None
        if start is not None:
            gaps.append((start, len(free) - 1))
        return gaps

    def adjust(self, observation: Observation, proposal: Action) -> Action:
        wanted = max(-self._half_view, min(self._half_view, intended_direction(proposal)))
        distance = observation.lidar[self._view] * observation.lidar_range
        obstacle = distance < self.free_distance
        if not obstacle.any() or goal_in_sight(observation, self._all_angles, self.reach):
            self._last_heading = wanted
            return Action(steering_towards(wanted), proposal.acceleration)

        nearest = float(distance.min())
        half_width = np.arcsin(np.minimum(1.0, self.reach / np.maximum(distance[obstacle], 1e-6)))
        blocked = (np.abs(self._angles[:, None] - self._angles[obstacle][None, :]) <= half_width[None, :]).any(axis=1)
        gaps = self._gaps(~blocked)
        if not gaps:                    # sin salida a la vista: frenar
            return Action(steering_towards(wanted), -1.0)

        # El hueco más ancho; a igual ancho, el más cercano al rumbo que ya se llevaba (evita vaivenes).
        reference = self._last_heading if self._last_heading is not None else wanted
        centers = [(self._angles[first] + self._angles[last]) / 2.0 for first, last in gaps]
        best = max(range(len(gaps)), key=lambda i: (gaps[i][1] - gaps[i][0], -abs(centers[i] - reference)))
        weight = self.alpha / max(nearest, 1e-6)
        heading = (weight * centers[best] + self.beta * wanted) / (weight + self.beta)
        self._last_heading = heading

        fraction = max(MIN_SPEED_FRACTION, min(1.0, nearest / self.free_distance))
        limited = min(proposal.acceleration, speed_guard(observation, observation.max_speed * fraction))
        return Action(steering_towards(heading), limited)


def build(config: dict) -> FollowTheGap:
    lidar = config["lidar"]
    return FollowTheGap(lidar["num_rays"], lidar["fov_deg"], config["vehicle"]["radius"], **config["avoidance"]["ftg"])


PLUGIN = AvoidancePlugin(
    name="ftg",
    label="FTG: Follow the Gap",
    short_label="FTG",
    description="Encara el hueco más ancho entre los obstáculos que ve el LiDAR, ponderado con la dirección deseada.",
    build=build,
)
