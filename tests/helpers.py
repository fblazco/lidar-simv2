"""Utilidades compartidas por las pruebas (no forman parte del producto)."""
from control.controller import Action, Controller
from sensors.lidar import Lidar
from simulation.environment import SimulationConfig
from simulation.factory import SimulationFactory
from simulation.map_data import MapData
from simulation.vehicle import VehicleParams


class ConstantController(Controller):
    """Devuelve siempre la misma acción y guarda las observaciones recibidas."""

    def __init__(self, steering=0.0, acceleration=1.0):
        self.action = Action(steering, acceleration)
        self.observations = []
        self.resets = 0

    def reset(self):
        self.resets += 1

    def act(self, observation):
        self.observations.append(observation)
        return self.action


def corridor_map(**overrides) -> MapData:
    """Mapa 20x10 con una ruta recta horizontal de S (1,5) a G (18,5)."""
    data = dict(
        name="corridor",
        cols=20,
        rows=10,
        route=[(c, 5) for c in range(1, 19)],
        start=(1, 5),
        start_heading=0.0,
        goal=(18, 5),
    )
    data.update(overrides)
    return MapData(**data)


def make_factory(max_time=30.0, **vehicle) -> SimulationFactory:
    return SimulationFactory(
        VehicleParams(**vehicle),
        lambda: Lidar(num_rays=72, fov_deg=360.0, max_range=8.0),
        SimulationConfig(dt=0.05, max_time=max_time, goal_radius=0.6),
    )
