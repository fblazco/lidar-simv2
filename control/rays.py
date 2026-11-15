"""Geometría de los rayos del LiDAR vista desde un controlador."""
from __future__ import annotations

import math

import numpy as np


def relative_ray_angles(num_rays: int, fov_deg: float = 360.0) -> np.ndarray:
    """Ángulo de cada rayo respecto del frente del vehículo, en radianes dentro de (-pi, pi].

    Los positivos quedan del lado hacia el que gira una dirección positiva.
    """
    if fov_deg >= 360.0:
        angles = np.arange(num_rays) * (2.0 * math.pi / num_rays)
    else:
        half = math.radians(fov_deg) / 2.0
        angles = np.linspace(-half, half, num_rays)
    return (angles + math.pi) % (2.0 * math.pi) - math.pi
