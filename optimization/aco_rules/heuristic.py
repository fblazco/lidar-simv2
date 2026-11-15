"""Información heurística de la colonia de reglas: qué maniobra parece razonable en cada situación.

Es el conocimiento previo del problema (el equivalente a 1/distancia en el
viajante): girar hacia el objetivo, alejarse de lo que está cerca y no acelerar
a fondo con algo delante. Las feromonas corrigen y afinan esta intuición.
"""
from __future__ import annotations

import numpy as np

from control.rule_controller import FREE, MID, NEAR, ObservationDiscretizer

STEERING_TOLERANCE = 0.45
OBSTACLE_PUSH = 0.9                          # cuánto desvía la dirección un obstáculo lateral
SIDE_WEIGHT = {NEAR: 1.0, MID: 0.4, FREE: 0.0}
THROTTLE_PREFERENCE = {                      # preferencia de (acelerar, despacio, frenar) según el frente
    NEAR: {1.0: 0.3, 0.2: 1.0, -1.0: 0.6},
    MID: {1.0: 0.6, 0.2: 1.0, -1.0: 0.3},
    FREE: {1.0: 1.0, 0.2: 0.5, -1.0: 0.1},
}
FLOOR = 0.02                                 # ninguna maniobra queda descartada de antemano


def build_heuristic(discretizer: ObservationDiscretizer, maneuvers) -> np.ndarray:
    """Matriz (situaciones x maniobras) de deseabilidad a priori, siempre positiva."""
    heuristic = np.empty((discretizer.size, len(maneuvers)))
    half = (discretizer.bearings - 1) / 2.0
    for state in range(discretizer.size):
        bearing, left, front, right = discretizer.decode(state)
        towards_target = (bearing - half) / half                       # -1 muy a la izquierda .. 1 muy a la derecha
        away_from_obstacles = SIDE_WEIGHT[left] - SIDE_WEIGHT[right]   # positivo: girar a la derecha
        wanted = float(np.clip(towards_target + OBSTACLE_PUSH * away_from_obstacles, -1.0, 1.0))
        for index, maneuver in enumerate(maneuvers):
            steering = np.exp(-((maneuver.steering - wanted) ** 2) / (2.0 * STEERING_TOLERANCE ** 2))
            heuristic[state, index] = FLOOR + steering * THROTTLE_PREFERENCE[front][maneuver.acceleration]
    return heuristic
