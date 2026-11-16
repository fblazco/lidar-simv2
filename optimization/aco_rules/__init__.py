"""Plugin de optimización: colonia de hormigas que aprende reglas de conducción.

Las hormigas construyen una tabla "situación -> maniobra". Lo aprendido no
depende de ningún mapa, así que se entrena y se valida igual que el genético.
"""
from pathlib import Path

from control.rule_controller import build_rule_controller_factory
from optimization.aco_rules.colony import ACORulesConfig, RuleColony
from optimization.aco_rules.heuristic import build_heuristic
from optimization.registry import StrategyBundle, StrategyPlugin, for_any_scenario


def build(config: dict) -> StrategyBundle:
    controller_factory = build_rule_controller_factory(config)
    colony = RuleColony(
        build_heuristic(controller_factory.discretizer, controller_factory.maneuvers),
        ants=config["training"]["population_size"],
        config=ACORulesConfig.from_dict(config["aco_rules"]),
        seed=config["training"]["seed"],
    )
    return StrategyBundle(colony, for_any_scenario(controller_factory))


ASSETS = Path(__file__).parent      # el ícono y la escena viajan con el plugin

PLUGIN = StrategyPlugin(
    name="aco_rules",
    label="Colonia de hormigas: reglas de conducción (ACO)",
    build=build,
    short_label="ACO reglas",
    description="Las hormigas eligen con feromonas una maniobra para cada situación del LiDAR y del objetivo.",
    stat_labels={
        "alpha": "Peso de la feromona (alfa)",
        "beta": "Peso de la heurística (beta)",
        "evaporation": "Evaporación",
        "explored_states": "Situaciones encontradas",
        "decisiveness": "Decisión de la colonia",
    },
    icon=str(ASSETS / "icon.svg"),
    demo=str(ASSETS / "demo.json"),
)
