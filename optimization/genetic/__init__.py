"""Plugin de optimización: Algoritmo Genético sobre los pesos de una red MLP.

Este es el único lugar donde el GA se conecta con el resto: evoluciona vectores
reales y usa ``MLPControllerFactory`` para convertirlos en controladores.
"""
from control.policy_controller import build_mlp_controller_factory
from optimization.genetic.genetic_algorithm import GAConfig, GeneticAlgorithm
from optimization.registry import StrategyBundle, StrategyPlugin


def build(config: dict) -> StrategyBundle:
    controller_factory = build_mlp_controller_factory(config)
    strategy = GeneticAlgorithm(
        genome_length=controller_factory.parameter_count,
        population_size=config["training"]["population_size"],
        config=GAConfig.from_dict(config["genetic"]),
        seed=config["training"]["seed"],
    )
    return StrategyBundle(strategy, controller_factory)


PLUGIN = StrategyPlugin(name="genetic", label="Algoritmo genético (GA)", build=build)
