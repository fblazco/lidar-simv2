"""Ruta ordenada de waypoints y seguimiento del avance de un móvil.

Un único ``Navigator`` cubre los dos modos de navegación; el simulador no
tiene implementaciones separadas para cada uno.
"""
from __future__ import annotations

import heapq
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


# --- camino más corto de un mapa -----------------------------------------------------------

_NEIGHBORS = ((1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
              (1, 1, math.sqrt(2.0)), (1, -1, math.sqrt(2.0)), (-1, 1, math.sqrt(2.0)), (-1, -1, math.sqrt(2.0)))


def _grid_path(map_data, blocked: set):
    """Camino de menor costo sobre la grilla (8 vecinos, sin cortar esquinas), o None si no existe."""
    start, goal = map_data.start, map_data.goal
    best, previous, queue = {start: 0.0}, {}, [(0.0, start)]
    while queue:
        cost, cell = heapq.heappop(queue)
        if cell == goal:
            path = [cell]
            while path[-1] in previous:
                path.append(previous[path[-1]])
            return path[::-1]
        if cost > best[cell]:
            continue
        for dc, dr, step in _NEIGHBORS:
            nxt = (cell[0] + dc, cell[1] + dr)
            if nxt in blocked or not map_data.in_bounds(nxt):
                continue
            if dc and dr and ((cell[0] + dc, cell[1]) in blocked or (cell[0], cell[1] + dr) in blocked):
                continue
            if cost + step < best.get(nxt, math.inf):
                best[nxt], previous[nxt] = cost + step, cell
                heapq.heappush(queue, (cost + step, nxt))
    return None


def _clear_segment(a, b, map_data, blocked: set) -> bool:
    """La recta entre dos puntos no atraviesa ninguna celda con obstáculo fijo."""
    samples = max(2, int(math.hypot(b[0] - a[0], b[1] - a[1]) / (0.2 * map_data.cell_size)))
    return all(
        map_data.cell_at(a[0] + (b[0] - a[0]) * i / samples, a[1] + (b[1] - a[1]) * i / samples) not in blocked
        for i in range(samples + 1)
    )


def shortest_path_length(map_data) -> float:
    """Largo del camino más corto de inicio a destino, en unidades del mundo.

    En seguimiento de ruta es el largo del camino dibujado. En navegación libre
    es el camino más corto entre los obstáculos fijos, sin holgura para el
    cuerpo del vehículo: una cota optimista con la que medir lo recorrido.
    """
    cells = map_data.path_cells()
    if map_data.navigation_mode == ROUTE_FOLLOWING and len(cells) > 2:
        return Route([map_data.cell_center(c) for c in cells]).length
    (sx, sy), (gx, gy) = map_data.cell_center(map_data.start), map_data.cell_center(map_data.goal)
    blocked = set(map_data.static_obstacles)
    path = _grid_path(map_data, blocked)
    if path is None:
        return math.hypot(gx - sx, gy - sy)
    points = [map_data.cell_center(c) for c in path]
    length, i = 0.0, 0
    while i < len(points) - 1:        # se tensa el camino de celdas: de cada punto al más lejano que se ve
        j = len(points) - 1
        while j > i + 1 and not _clear_segment(points[i], points[j], map_data, blocked):
            j -= 1
        length += math.hypot(points[j][0] - points[i][0], points[j][1] - points[i][1])
        i = j
    return length
