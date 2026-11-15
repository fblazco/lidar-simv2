"""Punto de ensamblado: construye los objetos del sistema a partir de la configuración.

Aquí (y solo aquí) se conectan simulador, sensores, mapas, evaluación y el
plugin de optimización elegido. Ningún algoritmo concreto se importa por nombre.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from config import deep_merge, load_config
from control.avoidance import DEFAULT as LEARNED_AVOIDANCE, discover_avoidance
from control.avoidance.base import AvoidancePlugin, with_avoidance
from typing import Dict, Optional, Sequence, Tuple, Union

from editor.map_generator import GeneratorConfig, MapGenerator
from editor.map_manager import load_map
from optimization.checkpoint import load_checkpoint, save_checkpoint
from optimization.evaluation import EvaluationSettings, Evaluator
from optimization.fitness import FitnessFunction, FitnessWeights
from optimization.registry import StrategyPlugin, discover_plugins
from optimization.results import RunRecord, save_run
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


def available_avoidance() -> Dict[str, AvoidancePlugin]:
    return discover_avoidance()


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
    avoidance = training.get("avoidance", LEARNED_AVOIDANCE)
    avoiders = discover_avoidance()
    if avoidance not in avoiders:
        raise ValueError(f"No existe el algoritmo de evasión '{avoidance}'. Disponibles: {', '.join(avoiders)}")
    controller_factory = bundle.controller_factory
    if avoiders[avoidance].build(config) is not None:      # una capa de evasión envuelve a cada controlador
        controller_factory = with_avoidance(controller_factory, lambda: avoiders[avoidance].build(config))
    evaluator = Evaluator(
        build_simulation_factory(config),
        controller_factory,
        FitnessFunction(FitnessWeights.from_dict(config["fitness"])),
        EvaluationSettings.from_dict(training),
    )
    scenarios = ScenarioProvider(
        build_map_generator(config).generate,
        seed=training["seed"],
        train_count=training["scenarios_per_candidate"],
        validation_count=training["validation_scenarios"],
        fixed_maps=maps,
        # Un algoritmo que aprende una ruta por mapa no puede cambiar de mapas en cada generación.
        resample_every=training["resample_scenarios_every"] if bundle.strategy.generalizes else 0,
    )
    return TrainingSession(bundle.strategy, evaluator, scenarios,
                           visible_agents=training["visible_agents"], validate_every=training["validate_every"],
                           max_iterations=training.get("max_iterations", 0), avoidance=avoidance)


def with_strategy(config: dict, strategy: str) -> dict:
    """Copia de la configuración con otro algoritmo de aprendizaje elegido."""
    return deep_merge(config, {"training": {"strategy": strategy}})


def with_choices(config: dict, strategy: Optional[str] = None, avoidance: Optional[str] = None,
                 map_mode: Optional[str] = None) -> dict:
    """Copia de la configuración con las elecciones del usuario: navegación, evasión y tipo de mapas."""
    training = {key: value for key, value in (("strategy", strategy), ("avoidance", avoidance)) if value}
    generator = {"navigation_mode": map_mode} if map_mode else {}
    return deep_merge(config, {"training": training, "generator": generator})


def build_training_session(config: dict, fixed_maps: Sequence[MapData] = ()) -> TrainingSession:
    """Sesión nueva con el algoritmo ``training.strategy``.

    ``fixed_maps`` y ``training.map_files`` se suman a los mapas aleatorios.
    """
    from_files = [load_map(path) for path in config["training"].get("map_files", [])]
    return _build_session(config, [*from_files, *fixed_maps])


def save_training_session(session: TrainingSession, path: Union[str, Path], config: dict) -> Path:
    meta, arrays = session.get_state()
    meta["config"] = config
    return save_checkpoint(path, meta, arrays)


def load_training_session(path: Union[str, Path]) -> Tuple[TrainingSession, dict]:
    """Reconstruye la sesión con la configuración guardada en el checkpoint."""
    meta, arrays = load_checkpoint(path)
    config = deep_merge(load_config(), meta["config"])   # los ajustes nuevos toman su valor por defecto
    maps = [MapData.from_dict(data) for data in meta["scenarios"]["fixed_maps"]]
    session = _build_session(config, maps)
    session.set_state(meta, arrays)
    return session, config


def finish_run(session: TrainingSession, config: dict, directory: Union[str, Path],
               run_id: str) -> Optional[RunRecord]:
    """Da por finalizada una corrida: guarda su registro (resumen + historial) y lo devuelve.

    Devuelve ``None`` si todavía no terminó ninguna iteración. Se puede llamar
    más de una vez con el mismo ``run_id`` para actualizar el registro.
    """
    if not session.history:
        return None
    strategy = session.strategy
    plugin = discover_plugins().get(strategy.name)
    avoider = discover_avoidance().get(session.avoidance)
    scenarios = session.scenarios
    record = RunRecord(
        run_id=run_id,
        strategy=strategy.name,
        label=plugin.label if plugin is not None else strategy.name,
        finished_at=datetime.now().isoformat(timespec="seconds"),
        seed=scenarios.seed,
        population_size=config["training"]["population_size"],
        generalizes=bool(strategy.generalizes),
        training_seeds=list(session.history[-1].training_seeds),
        validation_seeds=scenarios.validation_seeds() if strategy.generalizes else [],
        fixed_maps=[m.name for m in scenarios.fixed_maps],
        history=[h.to_dict() for h in session.history],
        avoidance=session.avoidance,
        avoidance_label=avoider.label if avoider is not None else session.avoidance,
        map_mode=config["generator"]["navigation_mode"],
        resampled=scenarios.resample_every > 0,
    )
    save_run(record, directory)
    return record
