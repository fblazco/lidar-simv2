"""Mundo físico construido a partir de un ``MapData``: geometría, ruta y tiempo."""
from __future__ import annotations

import numpy as np

from simulation.map_data import MapData
from simulation.navigation import Route
from simulation.obstacle import DynamicObstacle


class World:
    def __init__(self, map_data: MapData) -> None:
        if map_data.start is None or map_data.goal is None:
            raise ValueError("El mapa necesita inicio (S) y destino (G) para simularse")
        self.map = map_data
        self.width = map_data.width
        self.height = map_data.height
        self.cell_size = map_data.cell_size
        self.navigation_mode = map_data.navigation_mode
        cs = map_data.cell_size
        # Obstáculos estáticos: una caja por celda (xmin, ymin, xmax, ymax).
        self.boxes = np.array(
            [[c * cs, r * cs, (c + 1) * cs, (r + 1) * cs] for c, r in map_data.static_obstacles], dtype=float
        ).reshape(-1, 4)
        self.dynamic_obstacles = [DynamicObstacle(spec) for spec in map_data.dynamic_obstacles]
        # Obstáculos dinámicos: círculos (x, y, radio) actualizados con el tiempo.
        self.circles = np.zeros((len(self.dynamic_obstacles), 3))
        self.circles[:, 2] = [o.radius for o in self.dynamic_obstacles]
        sx, sy = map_data.cell_center(map_data.start)
        self.start_pose = (sx, sy, map_data.start_heading)
        self.goal = map_data.cell_center(map_data.goal)
        self.route = Route([map_data.cell_center(c) for c in map_data.path_cells()])
        self.time = 0.0
        self.set_time(0.0)

    @property
    def bounds(self):
        return (self.width, self.height)

    def set_time(self, time: float) -> None:
        self.time = time
        for i, obstacle in enumerate(self.dynamic_obstacles):
            self.circles[i, 0], self.circles[i, 1] = obstacle.position_at(time)
