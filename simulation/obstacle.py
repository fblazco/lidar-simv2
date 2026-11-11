"""Obstáculos dinámicos con trayectorias deterministas.

La posición es una función cerrada del tiempo: no hay estado acumulado, por lo
que reiniciar o repetir un episodio produce exactamente el mismo movimiento.
Los obstáculos no interactúan entre sí (pueden atravesarse).
"""
from __future__ import annotations

import math
from typing import Tuple

from simulation.map_data import DynamicObstacleSpec


class DynamicObstacle:
    def __init__(self, spec: DynamicObstacleSpec) -> None:
        self.spec = spec
        self.radius = spec.radius

    def position_at(self, time: float) -> Tuple[float, float]:
        spec = self.spec
        if spec.kind == "circular":
            return self._circular(time)
        along = self._ping_pong(time, spec.x if spec.kind == "horizontal" else spec.y)
        return (along, spec.y) if spec.kind == "horizontal" else (spec.x, along)

    def _ping_pong(self, time: float, start: float) -> float:
        """Ida y vuelta entre range_min y range_max con pausa en cada extremo."""
        spec = self.spec
        length = spec.range_max - spec.range_min
        if length <= 0.0 or spec.speed <= 0.0:
            return start
        offset = min(max(start - spec.range_min, 0.0), length)
        leg = length / spec.speed                      # duración de un tramo
        period = 2.0 * (leg + spec.pause)
        # fase 0 = saliendo de range_min hacia range_max
        phase = offset / spec.speed if spec.direction > 0 else leg + spec.pause + (length - offset) / spec.speed
        phase = math.fmod(phase + time, period)
        if phase < leg:
            return spec.range_min + spec.speed * phase
        if phase < leg + spec.pause:
            return spec.range_max
        if phase < 2.0 * leg + spec.pause:
            return spec.range_max - spec.speed * (phase - leg - spec.pause)
        return spec.range_min

    def _circular(self, time: float) -> Tuple[float, float]:
        spec = self.spec
        if spec.orbit_radius <= 0.0:
            return (spec.x, spec.y)
        angle = math.atan2(spec.y - spec.center_y, spec.x - spec.center_x)
        angle += spec.direction * (spec.speed / spec.orbit_radius) * time
        return (
            spec.center_x + spec.orbit_radius * math.cos(angle),
            spec.center_y + spec.orbit_radius * math.sin(angle),
        )
