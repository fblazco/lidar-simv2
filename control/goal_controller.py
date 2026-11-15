"""Navegación de referencia, sin aprendizaje: apuntar al siguiente waypoint y avanzar.

No esquiva nada por sí sola. Sirve como línea de base y como navegación mínima
sobre la cual medir un algoritmo de evasión (FTG, APF) por sí solo.
"""
from __future__ import annotations

from control.avoidance.base import INTENT_SPAN, SPEED_GAIN
from control.controller import Action, Controller, Observation

TURN_SLOWDOWN = 0.7


class GoalSeekingController(Controller):
    def __init__(self, cruise_speed: float = 0.8) -> None:
        self.cruise_speed = cruise_speed      # fracción de la velocidad máxima

    def act(self, observation: Observation) -> Action:
        bearing = observation.waypoint_bearing
        steering = max(-1.0, min(1.0, bearing / INTENT_SPAN))
        wanted = self.cruise_speed * observation.max_speed * (1.0 - TURN_SLOWDOWN * min(1.0, abs(bearing)))
        return Action(steering, max(-1.0, min(1.0, SPEED_GAIN * (wanted - observation.speed))))
