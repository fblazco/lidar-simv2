"""Campos potenciales artificiales (APF, Khatib 1986).

El vehículo se mueve como si lo empujaran dos fuerzas:

- una de atracción, de módulo constante, hacia la dirección deseada;
- una de repulsión por cada punto que el LiDAR ve más cerca que
  ``influence_distance``, que crece muy rápido al acercarse:

      F_rep = repulsion * (1/d - 1/d0) / d^2        (d = holgura al obstáculo, d0 = distancia de influencia)

El rumbo es el de la fuerza resultante. Un obstáculo alineado con el destino
empuja justo en contra de la atracción y el método puro se queda sin fuerza
lateral; para rodearlo se suma una componente tangencial (campo de vórtice, De
Medio y Oriolo 1991): la repulsión de lo que hay al frente, girada 90° hacia el
lado más despejado.

Es simple y suave, y conserva los defectos conocidos del método: mínimos
locales frente a paredes anchas y oscilaciones en pasos estrechos.
"""
from __future__ import annotations

import math

import numpy as np

from control.avoidance.base import (AvoidancePlugin, ObstacleAvoider, asset, goal_in_sight, intended_direction,
                                    speed_guard, steering_towards)
from control.controller import Action, Observation
from control.rays import relative_ray_angles

MIN_CLEARANCE = 0.05
MIN_SPEED_FRACTION = 0.4      # sin velocidad no se puede girar: nunca se frena del todo
BACKWARD_SLOWDOWN = 0.6       # factor de velocidad cuando la fuerza resultante empuja hacia atrás
FRONT_SECTOR = math.radians(45.0)     # solo lo que está al frente genera fuerza tangencial


class PotentialFields(ObstacleAvoider):
    def __init__(self, num_rays: int, fov_deg: float = 360.0, robot_radius: float = 0.35,
                 influence_distance: float = 2.5, repulsion: float = 2.0, attraction: float = 1.0,
                 tangential: float = 1.0) -> None:
        self.robot_radius = robot_radius
        self.influence_distance = influence_distance   # más lejos que esto, un obstáculo no empuja
        self.repulsion = repulsion
        self.attraction = attraction
        self.tangential = tangential                   # fracción de la repulsión frontal que se vuelve lateral
        self._angles = relative_ray_angles(num_rays, fov_deg)
        self._cos = np.cos(self._angles)
        self._sin = np.sin(self._angles)
        self._spacing = 2.0 * math.pi / num_rays       # cada rayo representa este ángulo de entorno
        self._front = np.abs(self._angles) <= FRONT_SECTOR
        self._left = (self._angles < 0.0) & (self._angles >= -math.pi / 2.0)
        self._right = (self._angles > 0.0) & (self._angles <= math.pi / 2.0)
        self._side = 0                                  # lado por el que se está rodeando: -1 izquierda, 1 derecha

    def reset(self) -> None:
        self._side = 0

    def force(self, observation: Observation, wanted: float):
        """Fuerza resultante (adelante, lateral) en el marco del vehículo y holgura mínima."""
        clearance = np.maximum(observation.lidar * observation.lidar_range - self.robot_radius, MIN_CLEARANCE)
        near = clearance < self.influence_distance
        fx, fy = self.attraction * math.cos(wanted), self.attraction * math.sin(wanted)
        if not near.any():
            self._side = 0
            return fx, fy, math.inf
        d = clearance[near]
        push = self.repulsion * (1.0 / d - 1.0 / self.influence_distance) / (d * d) * self._spacing
        fx -= float(np.sum(push * self._cos[near]))
        fy -= float(np.sum(push * self._sin[near]))
        ahead = self._front[near]
        if ahead.any():                         # componente tangencial: rodear lo que está al frente
            if self._side == 0:                 # se elige el lado más despejado y se mantiene mientras dure el obstáculo
                self._side = 1 if clearance[self._right].sum() >= clearance[self._left].sum() else -1
            rx = -float(np.sum(push[ahead] * self._cos[near][ahead]))
            ry = -float(np.sum(push[ahead] * self._sin[near][ahead]))
            fx += self.tangential * self._side * ry
            fy -= self.tangential * self._side * rx
        else:
            self._side = 0
        return fx, fy, float(d.min())

    def adjust(self, observation: Observation, proposal: Action) -> Action:
        wanted = intended_direction(proposal)
        fx, fy, closest = self.force(observation, wanted)
        if math.isinf(closest) or goal_in_sight(observation, self._angles, self.robot_radius + MIN_CLEARANCE):
            return Action(steering_towards(wanted), proposal.acceleration)
        heading = math.atan2(fy, fx)
        slow = max(MIN_SPEED_FRACTION, min(1.0, closest / self.influence_distance))
        if fx < 0.0:
            slow *= BACKWARD_SLOWDOWN
        limited = min(proposal.acceleration, speed_guard(observation, observation.max_speed * slow))
        return Action(steering_towards(heading), limited)


def build(config: dict) -> PotentialFields:
    lidar = config["lidar"]
    return PotentialFields(lidar["num_rays"], lidar["fov_deg"], config["vehicle"]["radius"],
                           **config["avoidance"]["apf"])


PLUGIN = AvoidancePlugin(
    name="apf",
    label="APF: campos potenciales artificiales",
    short_label="APF",
    description="El destino atrae y cada obstáculo que ve el LiDAR repele; el vehículo sigue la fuerza resultante.",
    build=build,
    icon=asset("apf.svg"),
    demo=asset("apf.json"),
)
