"""LiDAR geométrico por raycasting contra círculos, cajas y bordes del mundo.

No depende del simulador: recibe la pose del sensor y arreglos NumPy con la
geometría a detectar.
"""
from __future__ import annotations

import math

import numpy as np


class Lidar:
    def __init__(self, num_rays: int = 72, fov_deg: float = 360.0, max_range: float = 8.0) -> None:
        self.num_rays = int(num_rays)
        self.fov_deg = float(fov_deg)
        self.max_range = float(max_range)
        if self.fov_deg >= 360.0:
            self.angles = np.arange(self.num_rays) * (2.0 * math.pi / self.num_rays)
        else:
            half = math.radians(self.fov_deg) / 2.0
            self.angles = np.linspace(-half, half, self.num_rays)
        self._cos = np.cos(self.angles)
        self._sin = np.sin(self.angles)

    def _directions(self, heading: float):
        c, s = math.cos(heading), math.sin(heading)
        return self._cos * c - self._sin * s, self._sin * c + self._cos * s

    def scan(self, x, y, heading, circles: np.ndarray, boxes: np.ndarray, bounds) -> np.ndarray:
        """Distancia normalizada (0..1) al primer obstáculo en cada rayo.

        ``circles``: (N, 3) con x, y, radio. ``boxes``: (M, 4) con xmin, ymin,
        xmax, ymax. ``bounds``: (ancho, alto) del mundo, tratado como pared.
        """
        dx, dy = self._directions(heading)
        # Un rayo paralelo a un eje (componente 0) se trata como casi paralelo.
        dx = np.where(dx == 0.0, 1e-12, dx)
        dy = np.where(dy == 0.0, 1e-12, dy)
        inv_dx, inv_dy = 1.0 / dx, 1.0 / dy
        width, height = bounds
        wall_x = np.where(dx > 0.0, width - x, -x) * inv_dx
        wall_y = np.where(dy > 0.0, height - y, -y) * inv_dy
        distance = np.minimum(self.max_range, np.maximum(np.minimum(wall_x, wall_y), 0.0))

        if len(circles):
            ox, oy = circles[:, 0] - x, circles[:, 1] - y
            along = np.outer(dx, ox) + np.outer(dy, oy)
            disc = circles[:, 2] ** 2 - (ox * ox + oy * oy - along * along)
            half_chord = np.sqrt(np.maximum(disc, 0.0))
            hit = (disc >= 0.0) & (along + half_chord >= 0.0)
            t = np.where(hit, np.maximum(along - half_chord, 0.0), np.inf)
            distance = np.minimum(distance, t.min(axis=1))

        if len(boxes):
            ax = (boxes[:, 0] - x) * inv_dx[:, None]
            bx = (boxes[:, 2] - x) * inv_dx[:, None]
            ay = (boxes[:, 1] - y) * inv_dy[:, None]
            by = (boxes[:, 3] - y) * inv_dy[:, None]
            near = np.maximum(np.minimum(ax, bx), np.minimum(ay, by))
            far = np.minimum(np.maximum(ax, bx), np.maximum(ay, by))
            t = np.where((far >= near) & (far >= 0.0), np.maximum(near, 0.0), np.inf)
            distance = np.minimum(distance, t.min(axis=1))

        return distance / self.max_range

    def hit_points(self, x, y, heading, scan: np.ndarray) -> np.ndarray:
        """Punto final de cada rayo para una medición dada (para dibujarlos)."""
        dx, dy = self._directions(heading)
        reach = scan * self.max_range
        return np.column_stack((x + dx * reach, y + dy * reach))
