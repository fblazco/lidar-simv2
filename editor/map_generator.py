"""Generador de mapas aleatorios, válidos y reproducibles por semilla."""
from __future__ import annotations

import math
from dataclasses import dataclass, fields
from typing import Optional, Tuple

import numpy as np

from control.controller import FREE_NAVIGATION, ROUTE_FOLLOWING
from editor.map_editor import line_cells
from simulation.map_data import OBSTACLE_KINDS, DynamicObstacleSpec, MapData

MARGIN = 2                 # celdas libres junto al borde para inicio, destino y puntos de control
PROTECTED_CELLS = 3        # sin obstáculos estáticos a esta distancia del inicio y del destino
START_CLEARANCE = 2.5      # ningún obstáculo móvil pasa más cerca que esto del inicio (unidades)
GOAL_CLEARANCE = 1.5


@dataclass
class GeneratorConfig:
    cols: int = 32
    rows: int = 20
    cell_size: float = 1.0
    navigation_mode: str = ROUTE_FOLLOWING        # "route", "free" o "mixed"
    control_points: Tuple[int, int] = (2, 4)      # puntos intermedios del camino (mín, máx)
    static_obstacles: Tuple[int, int] = (3, 8)
    dynamic_obstacles: Tuple[int, int] = (1, 3)
    speed_range: Tuple[float, float] = (0.8, 2.5)
    pause_range: Tuple[float, float] = (0.3, 1.5)
    on_route_fraction: float = 0.4                # obstáculos estáticos puestos sobre el camino

    @classmethod
    def from_dict(cls, data: dict) -> "GeneratorConfig":
        values = {f.name: data[f.name] for f in fields(cls) if f.name in data}
        return cls(**{k: tuple(v) if isinstance(v, list) else v for k, v in values.items()})


class MapGenerator:
    def __init__(self, config: Optional[GeneratorConfig] = None) -> None:
        self.config = config or GeneratorConfig()

    def generate(self, seed: int) -> MapData:
        """El mismo ``seed`` con la misma configuración produce el mismo mapa."""
        rng = np.random.default_rng(seed)
        for _ in range(200):
            candidate = self._attempt(rng, int(seed))
            if candidate is not None and not candidate.validate():
                return candidate
        raise RuntimeError("No se pudo generar un mapa válido con esta configuración")

    def _attempt(self, rng: np.random.Generator, seed: int) -> Optional[MapData]:
        cfg = self.config
        route = self._route(rng)
        if len(route) < 12 or any(max(abs(a[0] - b[0]), abs(a[1] - b[1])) != 1 for a, b in zip(route, route[1:])):
            return None
        start, goal = route[0], route[-1]
        ahead = route[min(3, len(route) - 1)]
        mode = cfg.navigation_mode
        if mode == "mixed":
            mode = FREE_NAVIGATION if rng.random() < 0.5 else ROUTE_FOLLOWING
        map_data = MapData(
            name=f"aleatorio_{seed}", cols=cfg.cols, rows=cfg.rows, cell_size=cfg.cell_size,
            navigation_mode=mode, route=route, start=start, goal=goal, seed=seed,
            start_heading=math.atan2(ahead[1] - start[1], ahead[0] - start[0]),
        )
        static = self._static_obstacles(rng, map_data)
        dynamic = self._dynamic_obstacles(rng, map_data)
        if static is None or dynamic is None:
            return None
        map_data.static_obstacles = static
        map_data.dynamic_obstacles = dynamic
        return map_data

    def _route(self, rng: np.random.Generator) -> list:
        cfg = self.config
        row = lambda: int(rng.integers(MARGIN, cfg.rows - MARGIN))  # noqa: E731
        first_col, last_col = MARGIN, cfg.cols - 1 - MARGIN
        n_mid = int(rng.integers(cfg.control_points[0], cfg.control_points[1] + 1))
        mid_cols = np.linspace(first_col, last_col, n_mid + 2)[1:-1]
        points = [(first_col, row())]
        points += [(int(round(c + rng.uniform(-1.0, 1.0))), row()) for c in mid_cols]
        points.append((last_col, row()))
        if rng.random() < 0.5:   # mitad de los mapas van de derecha a izquierda
            points = [(cfg.cols - 1 - c, r) for c, r in points]
        route = [points[0]]
        for a, b in zip(points, points[1:]):
            route.extend(line_cells(a, b)[1:])
        return route

    def _static_obstacles(self, rng: np.random.Generator, m: MapData) -> Optional[list]:
        cfg = self.config
        count = int(rng.integers(cfg.static_obstacles[0], cfg.static_obstacles[1] + 1))
        placed: list = []
        for _ in range(count * 40):
            if len(placed) == count:
                break
            base = m.route[int(rng.integers(5, len(m.route) - 5))]
            cell = base
            if rng.random() >= cfg.on_route_fraction:
                cell = (base[0] + int(rng.integers(-3, 4)), base[1] + int(rng.integers(-3, 4)))
            near_ends = any(
                max(abs(cell[0] - e[0]), abs(cell[1] - e[1])) <= PROTECTED_CELLS for e in (m.start, m.goal)
            )
            if m.in_bounds(cell) and not near_ends and cell not in placed:
                placed.append(cell)
        return placed if len(placed) == count else None

    def _dynamic_obstacles(self, rng: np.random.Generator, m: MapData) -> Optional[list]:
        cfg = self.config
        count = int(rng.integers(cfg.dynamic_obstacles[0], cfg.dynamic_obstacles[1] + 1))
        cs, radius = m.cell_size, 0.4 * m.cell_size
        start, goal = m.cell_center(m.start), m.cell_center(m.goal)
        placed: list = []
        for _ in range(count * 40):
            if len(placed) == count:
                break
            kind = OBSTACLE_KINDS[int(rng.integers(len(OBSTACLE_KINDS)))]
            cx, cy = m.cell_center(m.route[int(rng.integers(6, len(m.route) - 3))])
            spec = DynamicObstacleSpec(
                kind=kind, x=cx, y=cy, radius=radius,
                speed=float(rng.uniform(*cfg.speed_range)),
                direction=1 if rng.random() < 0.5 else -1,
                pause=0.0 if rng.random() < 0.5 else float(rng.uniform(*cfg.pause_range)),
            )
            if kind == "circular":
                spec.center_x = cx + float(rng.uniform(-1.0, 1.0)) * cs
                spec.center_y = cy + float(rng.uniform(-1.0, 1.0)) * cs
                room = min(spec.center_x, m.width - spec.center_x, spec.center_y, m.height - spec.center_y) - radius
                spec.orbit_radius = min(float(rng.uniform(1.5, 3.0)) * cs, room)
                if spec.orbit_radius < cs:
                    continue
                angle = float(rng.uniform(0.0, 2.0 * math.pi))
                spec.x = spec.center_x + spec.orbit_radius * math.cos(angle)
                spec.y = spec.center_y + spec.orbit_radius * math.sin(angle)
                spec.pause = 0.0
            else:
                half = float(rng.uniform(2.0, 4.0)) * cs
                center, size = (cx, m.width) if kind == "horizontal" else (cy, m.height)
                spec.range_min = max(radius, center - half)
                spec.range_max = min(size - radius, center + half)
                along = float(rng.uniform(spec.range_min, spec.range_max))
                if kind == "horizontal":
                    spec.x = along
                else:
                    spec.y = along
            if (self._clearance(spec, start) > START_CLEARANCE + radius
                    and self._clearance(spec, goal) > GOAL_CLEARANCE + radius):
                placed.append(spec)
        return placed if len(placed) == count else None

    @staticmethod
    def _clearance(spec: DynamicObstacleSpec, point) -> float:
        """Distancia mínima entre un punto y toda la trayectoria del obstáculo."""
        px, py = point
        if spec.kind == "circular":
            return abs(math.hypot(px - spec.center_x, py - spec.center_y) - spec.orbit_radius)
        if spec.kind == "horizontal":
            nearest = min(max(px, spec.range_min), spec.range_max)
            return math.hypot(px - nearest, py - spec.y)
        nearest = min(max(py, spec.range_min), spec.range_max)
        return math.hypot(px - spec.x, py - nearest)
