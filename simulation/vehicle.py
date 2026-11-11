"""El móvil: una entidad física con sensor y controlador inyectados.

No conoce ningún algoritmo de aprendizaje. Para decidir solo consulta a su
``Controller``; para percibir, a su sensor. Ambos se pasan desde fuera.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, fields
from enum import Enum
from typing import Optional

import numpy as np

from control.controller import Action, Controller, Observation
from simulation.geometry import wrap_angle


@dataclass
class VehicleParams:
    radius: float = 0.35                 # cuerpo de colisión circular
    wheelbase: float = 0.7
    max_speed: float = 4.0
    max_reverse_speed: float = 0.0       # 0 = sin marcha atrás
    max_acceleration: float = 5.0
    max_brake: float = 8.0
    max_steering_angle: float = math.radians(35.0)
    drag: float = 0.4                    # pérdida de velocidad proporcional (1/s)

    @classmethod
    def from_dict(cls, data: dict) -> "VehicleParams":
        values = {f.name: data[f.name] for f in fields(cls) if f.name in data}
        if "max_steering_angle_deg" in data:
            values["max_steering_angle"] = math.radians(data["max_steering_angle_deg"])
        return cls(**values)


@dataclass
class VehicleState:
    x: float = 0.0
    y: float = 0.0
    heading: float = 0.0   # radianes; 0 apunta a +x, positivo gira hacia +y
    speed: float = 0.0


class Status(Enum):
    ACTIVE = "activo"
    COLLIDED = "colisión"
    REACHED_GOAL = "llegó"
    TIMED_OUT = "sin tiempo"


class Mobile:
    """Vehículo con modelo cinemático de bicicleta simplificado."""

    def __init__(self, params: VehicleParams, sensor=None, controller: Optional[Controller] = None,
                 name: str = "") -> None:
        self.params = params
        self.sensor = sensor            # cualquier objeto con scan(...), num_rays y max_range
        self.controller = controller
        self.name = name
        self.navigation = None          # NavigationInfo; lo actualiza la simulación
        self.reset(0.0, 0.0, 0.0)

    @property
    def active(self) -> bool:
        return self.status is Status.ACTIVE

    def reset(self, x: float, y: float, heading: float) -> None:
        self.state = VehicleState(float(x), float(y), float(heading), 0.0)
        self.status = Status.ACTIVE
        self.distance_traveled = 0.0
        self.elapsed = 0.0
        self.last_action = Action()
        rays = self.sensor.num_rays if self.sensor is not None else 0
        self.scan = np.ones(rays)
        self.previous_scan = self.scan
        if self.controller is not None:
            self.controller.reset()

    def sense(self, circles: np.ndarray, boxes: np.ndarray, bounds) -> None:
        if self.sensor is None:
            return
        self.previous_scan = self.scan
        self.scan = self.sensor.scan(self.state.x, self.state.y, self.state.heading, circles, boxes, bounds)

    def decide(self, observation: Observation) -> Action:
        self.controller.observe(observation)
        self.last_action = self.controller.act(observation).clipped()
        return self.last_action

    def apply(self, action: Action, dt: float) -> None:
        """Integra un paso de movimiento. Independiente del renderizado."""
        action = action.clipped()
        p, s = self.params, self.state
        thrust = action.acceleration * (p.max_acceleration if action.acceleration >= 0.0 else p.max_brake)
        speed = s.speed + (thrust - p.drag * s.speed) * dt
        speed = min(max(speed, -p.max_reverse_speed), p.max_speed)
        turn_rate = speed / p.wheelbase * math.tan(action.steering * p.max_steering_angle)
        heading = wrap_angle(s.heading + turn_rate * dt)
        s.x += speed * math.cos(heading) * dt
        s.y += speed * math.sin(heading) * dt
        s.heading = heading
        s.speed = speed
        self.distance_traveled += abs(speed) * dt
