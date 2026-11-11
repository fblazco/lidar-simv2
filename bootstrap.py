"""Punto de ensamblado: construye los objetos del sistema a partir de la configuración.

Aquí (y solo aquí) se conectan simulador, sensores, mapas, evaluación y el
plugin de optimización elegido. Ningún algoritmo concreto se importa por nombre.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Sequence, Tuple, Union

from editor.map_generator import GeneratorConfig, MapGenerator
from editor.map_manager import load_map
from optimization.checkpoint import load_checkpoint, save_checkpoint
from optimization.evaluation import EvaluationSettings, Evaluator
from optimization.fitness import FitnessFunction, FitnessWeights
from optimization.registry import StrategyPlugin, discover_plugins
from optimization.training import ScenarioProvider, TrainingSession
from sensors.lidar import Lidar
from simulation.environment import SimulationConfig
from simulation.factory import SimulationFactory
from simulation.map_data import MapData
from simulation.vehicle import VehicleParams


def build_simulation_factory(config: dict) -> SimulationFactory:
    lidar = dict(config["lidar"])
    return SimulationFactory(
        VehicleParams.from_dict(config["vehicle"]),
        lambda: Lidar(**lidar),
        SimulationConfig.from_dict(config["simulation"]),
    )


def build_map_generator(config: dict) -> MapGenerator:
    return MapGenerator(GeneratorConfig.from_dict({**config["map"], **config["generator"]}))


def available_strategies() -> Dict[str, StrategyPlugin]:
    return discover_plugins()


def _build_session(config: dict, maps: Sequence[MapData]) -> TrainingSession:
    training = config["training"]
    plugins = discover_plugins()
    if training["strategy"] not in plugins:
        available = ", ".join(sorted(plugins)) or "ninguna"
        raise ValueError(f"No existe la estrategia de aprendizaje '{training['strategy']}'. Disponibles: {available}")
    for map_data in maps:
        problems = map_data.validate()
        if problems:
            raise ValueError(f"El mapa '{map_data.name}' no sirve para entrenar: {'; '.join(problems)}")
    bundle = plugins[training["strategy"]].build(config)
    evaluator = Evaluator(
        build_simulation_factory(config),
        bundle.controller_factory,
        FitnessFunction(FitnessWeights.from_dict(config["fitness"])),
        EvaluationSettings.from_dict(training),
    )
    scenarios = ScenarioProvider(
        build_map_generator(config).generate,
        seed=training["seed"],
        train_count=training["scenarios_per_candidate"],
        validation_count=training["validation_scenarios"],
        fixed_maps=maps,
        resample_every=training["resample_scenarios_every"],
    )
    return TrainingSession(bundle.strategy, evaluator, scenarios,
                           visible_agents=training["visible_agents"], validate_every=training["validate_every"])


def build_training_session(config: dict, fixed_maps: Sequence[MapData] = ()) -> TrainingSession:
    """Sesión nueva. ``fixed_maps`` y ``training.map_files`` se suman a los mapas aleatorios."""
    from_files = [load_map(path) for path in config["training"].get("map_files", [])]
    return _build_session(config, [*from_files, *fixed_maps])


def save_training_session(session: TrainingSession, path: Union[str, Path], config: dict) -> Path:
    meta, arrays = session.get_state()
    meta["config"] = config
    return save_checkpoint(path, meta, arrays)


def load_training_session(path: Union[str, Path]) -> Tuple[TrainingSession, dict]:
    """Reconstruye la sesión con la configuración guardada en el checkpoint."""
    meta, arrays = load_checkpoint(path)
    config = meta["config"]
    maps = [MapData.from_dict(data) for data in meta["scenarios"]["fixed_maps"]]
    session = _build_session(config, maps)
    session.set_state(meta, arrays)
    return session, config
