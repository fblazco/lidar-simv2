"""Simulación: avanza el mundo y sus móviles con paso de tiempo fijo.

No sabe quién controla cada móvil ni si alguien está aprendiendo: solo pide
una acción al controlador de cada vehículo. Los móviles de un mismo mundo son
independientes entre sí (no colisionan ni se detectan mutuamente).
"""
from __future__ import annotations

from dataclasses import dataclass, fields, replace
from typing import List, Sequence

from control.controller import Observation
from simulation.collision import collides
from simulation.geometry import wrap_angle
from simulation.navigation import Navigator
from simulation.vehicle import Mobile, Status
from simulation.world import World


@dataclass
class SimulationConfig:
    dt: float = 0.05           # paso fijo de simulación (s)
    max_time: float = 40.0     # límite de tiempo del episodio (s)
    goal_radius: float = 0.6   # distancia al destino que cuenta como llegada
    lookahead: float = 2.0     # adelanto del waypoint objetivo sobre la ruta

    @classmethod
    def from_dict(cls, data: dict) -> "SimulationConfig":
        return cls(**{f.name: data[f.name] for f in fields(cls) if f.name in data})


class Simulation:
    def __init__(self, world: World, mobiles: Sequence[Mobile], config: SimulationConfig) -> None:
        self.world = world
        self.mobiles: List[Mobile] = list(mobiles)
        self.config = config
        self._navigators = [
            Navigator(world.navigation_mode, world.route, world.goal, config.lookahead) for _ in self.mobiles
        ]
        self.reset()

    @property
    def done(self) -> bool:
        return not any(m.active for m in self.mobiles)

    def reset(self) -> None:
        self.steps = 0
        self.time = 0.0
        self.world.set_time(0.0)
        x, y, heading = self.world.start_pose
        for mobile, navigator in zip(self.mobiles, self._navigators):
            mobile.reset(x, y, heading)
            mobile.navigation = navigator.reset(x, y)
            self._sense(mobile)
            mobile.previous_scan = mobile.scan

    def observation_for(self, mobile: Mobile) -> Observation:
        state, nav = mobile.state, mobile.navigation
        return Observation(
            lidar=mobile.scan,
            lidar_previous=mobile.previous_scan,
            heading=state.heading,
            speed=state.speed,
            max_speed=mobile.params.max_speed,
            goal_distance=nav.goal_distance,
            goal_bearing=wrap_angle(nav.goal_direction - state.heading),
            waypoint_distance=nav.target_distance,
            waypoint_bearing=wrap_angle(nav.target_direction - state.heading),
            path_deviation=nav.deviation,
            path_heading_error=wrap_angle(nav.path_heading - state.heading),
            navigation_mode=self.world.navigation_mode,
            lidar_range=mobile.sensor.max_range if mobile.sensor is not None else 0.0,
            time=self.time,
            x=state.x,
            y=state.y,
        )

    def step(self) -> None:
        """Avanza un paso: decidir -> mover obstáculos -> mover vehículos -> evaluar -> sensar."""
        if self.done:
            return
        dt = self.config.dt
        decisions = [(m, n, m.decide(self.observation_for(m)))
                     for m, n in zip(self.mobiles, self._navigators) if m.active]
        self.steps += 1
        self.time = self.steps * dt
        self.world.set_time(self.time)
        for mobile, navigator, action in decisions:
            mobile.apply(action, dt)
            mobile.elapsed = self.time
            state = mobile.state
            mobile.navigation = navigator.update(state.x, state.y)
            if collides(self.world, state.x, state.y, mobile.params.radius):
                mobile.status = Status.COLLIDED
            elif mobile.navigation.goal_distance <= self.config.goal_radius:
                mobile.status = Status.REACHED_GOAL
                mobile.navigation = replace(mobile.navigation, progress=1.0)
            elif self.time >= self.config.max_time - 1e-9:
                mobile.status = Status.TIMED_OUT
            self._sense(mobile)

    def _sense(self, mobile: Mobile) -> None:
        mobile.sense(self.world.circles, self.world.boxes, self.world.bounds)
