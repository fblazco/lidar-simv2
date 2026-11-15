"""Plugin de optimización: colonia de hormigas que traza una ruta sobre cada mapa.

Cada hormiga propone un camino celda a celda y un ``RouteController`` lo
conduce en el simulador. Aprende una ruta por mapa: no generaliza a mapas no
vistos, por lo que no participa de la validación.
"""
from typing import Any

from control.route_controller import RouteController, build_route_follower_settings
from optimization.aco_routes.colony import ACORoutesConfig, RouteColonies
from optimization.registry import StrategyBundle, StrategyPlugin
from optimization.strategy import UnknownScenarioError


class RouteControllerFactory:
    """(plan de rutas, escenario) -> controlador que sigue la ruta de ese escenario."""

    def __init__(self, follower: dict) -> None:
        self.follower = dict(follower)

    def __call__(self, plan: dict, scenario: Any) -> RouteController:
        route = plan.get(scenario.key)
        if route is None:
            name = scenario.label or scenario.map_data.name
            raise UnknownScenarioError(
                f"La colonia de rutas no entrenó con el mapa '{name}': solo conoce sus mapas de entrenamiento"
            )
        world = scenario.map_data
        settings = dict(self.follower)
        settings["lookahead"] = settings["lookahead"] * world.cell_size
        return RouteController([world.cell_center(cell) for cell in route], **settings)


def build(config: dict) -> StrategyBundle:
    colonies = RouteColonies(
        ants=config["training"]["population_size"],
        config=ACORoutesConfig.from_dict(config["aco_routes"]),
        seed=config["training"]["seed"],
    )
    return StrategyBundle(colonies, RouteControllerFactory(build_route_follower_settings(config)))


PLUGIN = StrategyPlugin(
    name="aco_routes",
    label="Colonia de hormigas: rutas por mapa (ACO)",
    build=build,
    short_label="ACO rutas",
    description="Las hormigas trazan con feromonas una ruta celda a celda sobre cada mapa de entrenamiento.",
    stat_labels={
        "alpha": "Peso de la feromona (alfa)",
        "beta": "Peso de la heurística (beta)",
        "evaporation": "Evaporación",
        "route_length": "Largo de la mejor ruta (celdas)",
        "trail_focus": "Feromona sobre la mejor ruta",
    },
)
