"""Plugin de optimización: Algoritmo Genético sobre los pesos de una red MLP.

Este es el único lugar donde el GA se conecta con el resto: evoluciona vectores
reales y usa ``MLPControllerFactory`` para convertirlos en controladores.
"""
from pathlib import Path

from control.policy_controller import build_mlp_controller_factory
from optimization.genetic.genetic_algorithm import GAConfig, GeneticAlgorithm
from optimization.registry import StrategyBundle, StrategyPlugin, for_any_scenario


def build(config: dict) -> StrategyBundle:
    controller_factory = build_mlp_controller_factory(config)
    strategy = GeneticAlgorithm(
        genome_length=controller_factory.parameter_count,
        population_size=config["training"]["population_size"],
        config=GAConfig.from_dict(config["genetic"]),
        seed=config["training"]["seed"],
    )
    return StrategyBundle(strategy, for_any_scenario(controller_factory))


ASSETS = Path(__file__).parent      # el ícono y la escena viajan con el plugin

PLUGIN = StrategyPlugin(
    name="genetic",
    label="Algoritmo genético (GA)",
    build=build,
    short_label="Genético",
    description="Evoluciona los pesos de una red neuronal que conduce el vehículo.",
    stat_labels={
        "mutation_rate": "Tasa de mutación",
        "mutation_sigma": "Sigma de mutación",
        "crossover_rate": "Tasa de crossover",
        "elitism": "Elitismo",
        "diversity": "Diversidad genética",
    },
    icon=str(ASSETS / "icon.svg"),
    demo=str(ASSETS / "demo.json"),
)
