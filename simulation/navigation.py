"""Ruta ordenada de waypoints y seguimiento del avance de un móvil.

Un único ``Navigator`` cubre los dos modos de navegación; el simulador no
tiene implementaciones separadas para cada uno.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np

from control.controller import ROUTE_FOLLOWING


class Route:
    """Polilínea ordenada en coordenadas del mundo, parametrizada por longitud de arco."""

    def __init__(self, points) -> None:
        pts = np.asarray(points, dtype=float).reshape(-1, 2)
        if len(pts) > 1:
            distinct = np.any(np.abs(np.diff(pts, axis=0)) > 1e-9, axis=1)
            pts = pts[np.concatenate(([True], distinct))]
        if len(pts) < 2:  # ruta degenerada: se trata como un tramo ínfimo
            pts = np.vstack([pts[:1], pts[:1] + (1e-6, 0.0)])
        self.points = pts
        vectors = np.diff(pts, axis=0)
        self._starts = pts[:-1]
        self._lengths = np.hypot(vectors[:, 0], vectors[:, 1])
        self._units = vectors / self._lengths[:, None]
        self._offsets = np.concatenate(([0.0], np.cumsum(self._lengths)))
        self._headings = np.arctan2(vectors[:, 1], vectors[:, 0])
        self.length = float(self._offsets[-1])

    def point_at(self, s: float) -> Tuple[float, float]:
        s = min(max(s, 0.0), self.length)
        i = min(int(np.searchsorted(self._offsets, s, side="right")) - 1, len(self._lengths) - 1)
        point = self._starts[i] + self._units[i] * (s - self._offsets[i])
        return (float(point[0]), float(point[1]))

    def project(self, x: float, y: float, around: Optional[float] = None,
                back: float = 1.0, ahead: float = 4.0) -> Tuple[float, float, float]:
        """Punto más cercano de la ruta: (longitud de arco, desvío con signo, rumbo).

        Con ``around`` la búsqueda se limita a [around - back, around + ahead]
        para que el avance sea continuo y no salte a otro tramo que pase cerca.
        El desvío es positivo a la derecha del sentido de avance (en pantalla).
        """
        rel_x = x - self._starts[:, 0]
        rel_y = y - self._starts[:, 1]
        t = rel_x * self._units[:, 0] + rel_y * self._units[:, 1]
        lo = np.zeros_like(t)
        hi = self._lengths
        if around is not None:
            lo = np.minimum(np.maximum(around - back - self._offsets[:-1], 0.0), self._lengths)
            hi = np.minimum(np.maximum(around + ahead - self._offsets[:-1], 0.0), self._lengths)
        t = np.minimum(np.maximum(t, lo), hi)
        dx = rel_x - self._units[:, 0] * t
        dy = rel_y - self._units[:, 1] * t
        dist2 = dx * dx + dy * dy
        if around is not None:
            outside = (self._offsets[:-1] > around + ahead) | (self._offsets[1:] < around - back)
            if not np.all(outside):
                dist2 = np.where(outside, np.inf, dist2)
        i = int(np.argmin(dist2))
        deviation = self._units[i, 0] * dy[i] - self._units[i, 1] * dx[i]
        return float(self._offsets[i] + t[i]), float(deviation), float(self._headings[i])


@dataclass(frozen=True)
class NavigationInfo:
    progress: float              # mejor avance logrado hacia el destino, 0..1
    goal_distance: float
    goal_direction: float        # ángulo absoluto hacia el destino
    target: Tuple[float, float]  # siguiente waypoint: punto adelantado sobre la ruta
    target_distance: float
    target_direction: float      # ángulo absoluto hacia el waypoint
    deviation: float             # distancia lateral con signo al camino
    path_heading: float          # rumbo absoluto del camino en el punto más cercano


class Navigator:
    """Sigue el avance de un móvil hacia el destino, en modo libre o por ruta."""

    def __init__(self, mode: str, route: Route, goal: Tuple[float, float], lookahead: float = 2.0) -> None:
        self.mode = mode
        self.route = route
        self.goal = (float(goal[0]), float(goal[1]))
        self.lookahead = lookahead
        self._s = 0.0
        self._best = 0.0
        self._initial_goal_distance = 1.0

    def reset(self, x: float, y: float) -> NavigationInfo:
        self._s = 0.0
        self._best = 0.0
        self._initial_goal_distance = max(math.hypot(self.goal[0] - x, self.goal[1] - y), 1e-9)
        return self.update(x, y)

    def update(self, x: float, y: float) -> NavigationInfo:
        gx, gy = self.goal[0] - x, self.goal[1] - y
        goal_distance = math.hypot(gx, gy)
        goal_direction = math.atan2(gy, gx)
        if self.mode == ROUTE_FOLLOWING:
            self._s, deviation, path_heading = self.route.project(x, y, around=self._s)
            progress = self._s / self.route.length
            target = self.route.point_at(self._s + self.lookahead)
        else:
            progress = 1.0 - goal_distance / self._initial_goal_distance
            target, deviation, path_heading = self.goal, 0.0, goal_direction
        self._best = max(self._best, min(max(progress, 0.0), 1.0))
        tx, ty = target[0] - x, target[1] - y
        return NavigationInfo(
            progress=self._best,
            goal_distance=goal_distance,
            goal_direction=goal_direction,
            target=target,
            target_distance=math.hypot(tx, ty),
            target_direction=math.atan2(ty, tx) if (tx or ty) else path_heading,
            deviation=deviation,
            path_heading=path_heading,
        )
