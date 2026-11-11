"""Ensambla simulaciones inyectando sensor y controlador en cada móvil."""
from __future__ import annotations

from typing import Callable, Sequence

from control.controller import Controller
from simulation.environment import Simulation, SimulationConfig
from simulation.map_data import MapData
from simulation.vehicle import Mobile, VehicleParams
from simulation.world import World


class SimulationFactory:
    def __init__(self, vehicle_params: VehicleParams, sensor_factory: Callable[[], object],
                 config: SimulationConfig) -> None:
        self.vehicle_params = vehicle_params
        self.sensor_factory = sensor_factory   # p. ej. lambda: Lidar(...); cada móvil recibe el suyo
        self.config = config

    def create(self, map_data: MapData, controllers: Sequence[Controller]) -> Simulation:
        """Un mundo propio para ``map_data`` con un móvil por controlador."""
        world = World(map_data)
        mobiles = [
            Mobile(self.vehicle_params, self.sensor_factory(), controller, name=f"movil-{i}")
            for i, controller in enumerate(controllers)
        ]
        return Simulation(world, mobiles, self.config)
