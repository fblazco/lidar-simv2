"""Colisiones del cuerpo circular de un vehículo. Sin dependencias de renderizado."""
from __future__ import annotations

import numpy as np


def circle_hits_boxes(x: float, y: float, radius: float, boxes: np.ndarray) -> bool:
    if len(boxes) == 0:
        return False
    dx = x - np.minimum(np.maximum(x, boxes[:, 0]), boxes[:, 2])
    dy = y - np.minimum(np.maximum(y, boxes[:, 1]), boxes[:, 3])
    return bool(np.any(dx * dx + dy * dy <= radius * radius))


def circle_hits_circles(x: float, y: float, radius: float, circles: np.ndarray) -> bool:
    if len(circles) == 0:
        return False
    dx = circles[:, 0] - x
    dy = circles[:, 1] - y
    reach = circles[:, 2] + radius
    return bool(np.any(dx * dx + dy * dy <= reach * reach))


def circle_out_of_bounds(x: float, y: float, radius: float, width: float, height: float) -> bool:
    return x - radius < 0.0 or y - radius < 0.0 or x + radius > width or y + radius > height


def collides(world, x: float, y: float, radius: float) -> bool:
    """Vehículo contra bordes, obstáculos estáticos y dinámicos del mundo."""
    return (
        circle_out_of_bounds(x, y, radius, world.width, world.height)
        or circle_hits_boxes(x, y, radius, world.boxes)
        or circle_hits_circles(x, y, radius, world.circles)
    )
