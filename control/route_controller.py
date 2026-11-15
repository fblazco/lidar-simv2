"""Controlador que sigue una ruta de waypoints.

Persigue el siguiente waypoint de su ruta usando la posición del vehículo y
frena cuando el LiDAR detecta algo dentro del corredor que va a ocupar. No
depende de quién planificó la ruta.
"""
from __future__ import annotations

import math
from typing import Sequence

import numpy as np

from control.controller import Action, Controller, Observation

STEERING_GAIN = 2.0          # dirección a fondo con ~30° de error de rumbo
SPEED_GAIN = 1.5
TURN_SLOWDOWN = 0.7          # fracción de velocidad que se quita al encarar un giro cerrado
CORRIDOR_HALF_WIDTH = 0.38   # semiancho del corredor vigilado: apenas más que el radio del vehículo
CORRIDOR_SPEED_WIDENING = 0.1
FRONT_CONE_DEG = 75.0
MAX_CORRIDOR_SHIFT = 0.35     # rad: cuánto se orienta el corredor hacia el lado al que se está girando
SEARCH_WINDOW = 4            # tramos de la ruta que se revisan por delante del actual


class RouteController(Controller):
    def __init__(self, waypoints: Sequence, num_rays: int, fov_deg: float = 360.0, cruise_speed: float = 0.8,
                 lookahead: float = 0.8, safety_margin: float = 0.5, reaction_time: float = 0.4) -> None:
        self.planned_path = np.asarray(waypoints, dtype=float).reshape(-1, 2)   # legible para dibujar la ruta
        if len(self.planned_path) == 0:
            raise ValueError("La ruta necesita al menos un waypoint")
        self._points = [(float(x), float(y)) for x, y in self.planned_path]
        self.cruise_speed = cruise_speed          # fracción de la velocidad máxima
        self.lookahead = lookahead                # adelanto del punto perseguido sobre la ruta
        self.safety_margin = safety_margin        # distancia mínima a un obstáculo en el corredor
        self.reaction_time = reaction_time        # margen extra proporcional a la velocidad
        if fov_deg >= 360.0:
            angles = np.arange(num_rays) * (2.0 * math.pi / num_rays)
        else:
            half = math.radians(fov_deg) / 2.0
            angles = np.linspace(-half, half, num_rays)
        angles = (angles + math.pi) % (2.0 * math.pi) - math.pi
        self._front = np.flatnonzero(np.abs(angles) <= math.radians(FRONT_CONE_DEG))
        self._front_angles = angles[self._front]
        self._segment = 0

    def reset(self) -> None:
        self._segment = 0

    def _target(self, x: float, y: float):
        """Punto de la ruta situado ``lookahead`` por delante de la posición más cercana a ella.

        La búsqueda solo mira unos pocos tramos hacia delante, así el seguimiento
        avanza de forma continua aunque la ruta vuelva a pasar cerca de sí misma.
        """
        points, last = self._points, len(self._points) - 1
        if last == 0:
            return points[0]
        best, best_t, best_distance = self._segment, 0.0, math.inf
        for i in range(self._segment, min(self._segment + SEARCH_WINDOW, last)):
            (ax, ay), (bx, by) = points[i], points[i + 1]
            dx, dy = bx - ax, by - ay
            length2 = dx * dx + dy * dy
            t = 0.0 if length2 == 0.0 else max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / length2))
            distance = math.hypot(ax + t * dx - x, ay + t * dy - y)
            if distance < best_distance - 1e-9:
                best, best_t, best_distance = i, t, distance
        self._segment = best
        remaining, i, t = self.lookahead, best, best_t      # se avanza `lookahead` a lo largo de la ruta
        while True:
            (ax, ay), (bx, by) = points[i], points[i + 1]
            length = math.hypot(bx - ax, by - ay)
            available = length * (1.0 - t)
            if remaining <= available or i + 1 == last:
                t = 1.0 if length == 0.0 else min(1.0, t + remaining / length)
                return (ax + t * (bx - ax), ay + t * (by - ay))
            remaining -= available
            i, t = i + 1, 0.0

    def _clearance_ahead(self, obs: Observation, bearing: float) -> float:
        """Distancia libre dentro del corredor que el vehículo está por ocupar.

        El vehículo avanza en arco hacia su objetivo, así que el corredor se
        orienta un poco hacia ese lado. Sin esto, un obstáculo fijo al costado
        de la ruta lo dejaría frenado: no puede girar sin avanzar.
        """
        if len(self._front) == 0:
            return math.inf
        distance = obs.lidar[self._front] * obs.lidar_range
        relative = self._front_angles - max(-MAX_CORRIDOR_SHIFT, min(MAX_CORRIDOR_SHIFT, bearing))
        speed_ratio = abs(obs.speed) / obs.max_speed if obs.max_speed > 0 else 0.0
        half_width = CORRIDOR_HALF_WIDTH + CORRIDOR_SPEED_WIDENING * speed_ratio
        inside = (distance * np.abs(np.sin(relative)) < half_width) & (np.abs(relative) < math.pi / 2.0)
        return float((distance * np.cos(relative))[inside].min()) if inside.any() else math.inf

    def act(self, obs: Observation) -> Action:
        tx, ty = self._target(obs.x, obs.y)
        bearing = math.atan2(ty - obs.y, tx - obs.x) - obs.heading
        bearing = (bearing + math.pi) % (2.0 * math.pi) - math.pi
        steering = max(-1.0, min(1.0, STEERING_GAIN * bearing))
        if self._clearance_ahead(obs, bearing) < self.safety_margin + abs(obs.speed) * self.reaction_time:
            return Action(steering, -1.0)
        wanted = self.cruise_speed * obs.max_speed * (1.0 - TURN_SLOWDOWN * min(1.0, abs(bearing)))
        return Action(steering, max(-1.0, min(1.0, SPEED_GAIN * (wanted - obs.speed))))


def build_route_follower_settings(config: dict) -> dict:
    """Parámetros del seguidor según las secciones lidar y aco_routes.follower (adelanto en celdas)."""
    lidar = config["lidar"]
    return {"num_rays": lidar["num_rays"], "fov_deg": lidar["fov_deg"], **config["aco_routes"]["follower"]}
