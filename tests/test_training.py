"""Sesión de entrenamiento: generaciones, escenarios comparables, checkpoints."""
import subprocess
import sys
from pathlib import Path

import pytest

from bootstrap import build_training_session, load_training_session, save_training_session
from config import load_config

ROOT = Path(__file__).resolve().parent.parent


def tiny_config(**training):
    return load_config(overrides={
        "map": {"cols": 16, "rows": 10},
        "simulation": {"max_time": 6.0},
        "policy": {"hidden_layers": [4]},
        "observation": {"use_previous_lidar": False},
        "generator": {"static_obstacles": [1, 2], "dynamic_obstacles": [1, 1]},
        "training": {"population_size": 6, "visible_agents": 0, "scenarios_per_candidate": 2,
                     "validation_scenarios": 2, "stall_time": 1.5, **training},
    })


def summary(stats):
    return (stats.iteration, stats.best_fitness, stats.mean_fitness, stats.success_rate, stats.collisions,
            stats.validation_fitness)


def test_one_iteration_evaluates_the_whole_population_and_reports_statistics():
    session = build_training_session(tiny_config())
    stats = session.run_iteration()
    assert stats.iteration == 1
    assert stats.evaluations == 6 and stats.episodes == 12
    assert stats.best_fitness >= stats.mean_fitness
    assert 0.0 <= stats.success_rate <= 1.0
    assert 0 <= stats.collisions <= 12
    assert stats.mean_distance >= 0.0 and stats.mean_time > 0.0
    assert stats.validation_fitness is not None
    assert {"mutation_rate", "diversity"} <= set(stats.strategy)
    assert session.history == [stats]
    assert session.strategy.iteration == 1


def test_generations_follow_one_another_and_never_get_worse_on_fixed_scenarios():
    session = build_training_session(tiny_config())
    history = [session.run_iteration() for _ in range(4)]
    assert [h.iteration for h in history] == [1, 2, 3, 4]
    assert [h.evaluations for h in history] == [6, 12, 18, 24]
    best = [h.best_fitness for h in history]
    assert all(b >= a for a, b in zip(best, best[1:]))


def test_all_candidates_of_a_generation_share_the_scenarios_and_seeds_are_recorded():
    session = build_training_session(tiny_config())
    first = session.run_iteration()
    second = session.run_iteration()
    assert len(first.training_seeds) == 2
    assert first.training_seeds == second.training_seeds           # fijos por defecto
    assert first.training_seeds == session.scenarios.training_seeds(0)
    assert [s.seed for s in session.scenarios.training_set(0)] == first.training_seeds


def test_validation_scenarios_are_separate_from_training_scenarios():
    scenarios = build_training_session(tiny_config()).scenarios
    assert len(scenarios.validation_seeds()) == 2
    assert not set(scenarios.validation_seeds()) & set(scenarios.training_seeds(0))


def test_resampling_changes_the_training_scenarios_between_generations():
    session = build_training_session(tiny_config(resample_scenarios_every=1))
    first = session.run_iteration()
    second = session.run_iteration()
    assert first.training_seeds != second.training_seeds


def test_training_is_reproducible_from_the_seed():
    def run():
        session = build_training_session(tiny_config())
        return [summary(session.run_iteration()) for _ in range(3)]

    assert run() == run()
    other = build_training_session(tiny_config(seed=99))
    assert [summary(other.run_iteration()) for _ in range(3)] != run()


def test_checkpoint_resumes_training_with_identical_results(tmp_path):
    config = tiny_config()
    straight = build_training_session(config)
    expected = [summary(straight.run_iteration()) for _ in range(4)]

    first_half = build_training_session(config)
    for _ in range(2):
        first_half.run_iteration()
    path = save_training_session(first_half, tmp_path / "ckpt.npz", config)
    resumed, saved_config = load_training_session(path)
    assert saved_config == config
    assert [summary(h) for h in resumed.history] == expected[:2]
    assert [summary(resumed.run_iteration()) for _ in range(2)] == expected[2:]


def test_visible_agents_are_stepped_without_changing_the_outcome():
    headless = build_training_session(tiny_config()).run_iteration()
    session = build_training_session(tiny_config(visible_agents=3))
    session.begin_iteration()
    assert len(session.visible) == 3
    shown = [run for run in session.visible if run is not None]
    assert len({run.candidate.id for run in shown}) == 3
    assert len({id(run.simulation.world) for run in shown}) == 3    # cada uno con su propio mundo
    stats = None
    frames = 0
    while stats is None:
        assert session.strategy.iteration == 0    # la generación siguiente no empieza antes de tiempo
        stats = session.advance(visible_steps=5, time_budget=0.002)
        frames += 1
    assert frames > 3                              # el trabajo se reparte en varios cuadros
    assert summary(stats) == summary(headless)
    assert session.strategy.iteration == 1


def test_fixed_maps_are_added_to_every_candidates_scenarios():
    from helpers import corridor_map
    session = build_training_session(tiny_config(), fixed_maps=[corridor_map()])
    labels = [s.label for s in session.scenarios.training_set(0)]
    assert labels[0] == "corridor" and len(labels) == 3
    assert session.run_iteration().episodes == 18


def test_unknown_strategy_is_reported_clearly():
    with pytest.raises(ValueError, match="estrategia"):
        build_training_session(tiny_config(strategy="pso"))


def test_headless_training_never_imports_pygame():
    code = (
        "import sys; from bootstrap import build_training_session; from config import load_config\n"
        "cfg = load_config(overrides={'map': {'cols': 16, 'rows': 10}, 'simulation': {'max_time': 3.0},"
        " 'policy': {'hidden_layers': [4]}, 'training': {'population_size': 4, 'scenarios_per_candidate': 1,"
        " 'validation_scenarios': 1, 'stall_time': 1.0}})\n"
        "build_training_session(cfg).run_iteration()\n"
        "assert 'pygame' not in sys.modules, 'pygame fue importado'\n"
    )
    result = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


# --- contratos comunes a cualquier estrategia -------------------------------------------

import numpy as np

from control.controller import Controller
from optimization.evaluation import EvaluationSettings, Evaluator
from optimization.fitness import FitnessFunction, FitnessWeights
from optimization.strategy import Candidate, LearningStrategy, StrategyState
from optimization.training import ScenarioProvider, TrainingSession

from helpers import ConstantController, corridor_map, make_factory


class ThrottleStrategy(LearningStrategy):
    """Estrategia mínima de prueba: sus soluciones son aceleraciones constantes."""

    name = "throttle"

    def __init__(self, generalizes=True):
        self.generalizes = generalizes
        self.calls = []
        self._iteration = 0

    @property
    def iteration(self):
        return self._iteration

    def prepare(self, scenarios):
        self.calls.append(("prepare", [s.label for s in scenarios]))

    def ask(self):
        self.calls.append(("ask", None))
        return [Candidate(0, 0.4), Candidate(1, 1.0)]

    def tell(self, results):
        self.calls.append(("tell", [round(r.fitness) for r in results]))
        self._iteration += 1

    def best(self):
        return (1.0, 0.0)

    def statistics(self):
        return {}

    def get_state(self):
        return StrategyState({"iteration": self._iteration}, {})

    def set_state(self, state):
        self._iteration = state.meta["iteration"]


def throttle_session(strategy, **kwargs):
    evaluator = Evaluator(make_factory(max_time=10.0),
                          lambda throttle, scenario: ConstantController(0.0, throttle),
                          FitnessFunction(FitnessWeights()), EvaluationSettings(stall_time=2.0))
    scenarios = ScenarioProvider(lambda seed: corridor_map(name=f"val_{seed}"), seed=1, train_count=0,
                                 validation_count=1, fixed_maps=[corridor_map()])
    return TrainingSession(strategy, evaluator, scenarios, **kwargs)


def test_strategy_is_told_the_scenarios_before_it_is_asked_for_candidates():
    strategy = ThrottleStrategy()
    throttle_session(strategy).run_iteration()
    assert [name for name, _ in strategy.calls] == ["prepare", "ask", "tell"]
    assert strategy.calls[0][1] == ["corridor"]


def test_strategies_that_do_not_generalize_are_not_validated():
    validated = throttle_session(ThrottleStrategy(generalizes=True)).run_iteration()
    skipped = throttle_session(ThrottleStrategy(generalizes=False)).run_iteration()
    assert validated.validation_fitness is not None
    assert skipped.validation_fitness is None and skipped.validation_success_rate is None


def test_iteration_statistics_record_the_time_spent():
    stats = throttle_session(ThrottleStrategy()).run_iteration()
    assert stats.seconds > 0.0


def test_session_finishes_when_it_reaches_the_iteration_limit():
    session = throttle_session(ThrottleStrategy(), max_iterations=2)
    assert not session.finished
    session.run_iteration()
    assert not session.finished
    session.run_iteration()
    assert session.finished
    assert not throttle_session(ThrottleStrategy()).finished          # sin límite nunca termina sola


def test_best_controller_is_built_for_the_map_it_will_drive():
    session = throttle_session(ThrottleStrategy())
    assert session.best_controller(corridor_map()) is None             # todavía no entrenó
    session.run_iteration()
    controller = session.best_controller(corridor_map())
    assert isinstance(controller, Controller)
    assert controller.act(None).acceleration == 1.0                    # el mejor fue el que aceleró a fondo


def test_checkpoints_saved_before_new_settings_existed_still_load(tmp_path):
    config = tiny_config()
    session = build_training_session(config)
    session.run_iteration()
    old_style = {k: v for k, v in config.items() if not k.startswith("aco_")}
    old_style["training"] = {k: v for k, v in config["training"].items() if k != "max_iterations"}
    path = save_training_session(session, tmp_path / "viejo.npz", old_style)
    resumed, loaded_config = load_training_session(path)
    assert resumed.strategy.iteration == 1
    assert loaded_config["training"]["max_iterations"] == load_config()["training"]["max_iterations"]
    assert "aco_rules" in loaded_config and "aco_routes" in loaded_config


@pytest.mark.parametrize("strategy", ["genetic", "aco_rules", "aco_routes"])
def test_every_algorithm_trains_and_resumes_identically(strategy, tmp_path):
    config = tiny_config(strategy=strategy)
    straight = build_training_session(config)
    assert straight.strategy.name == strategy
    expected = [summary(straight.run_iteration()) for _ in range(3)]
    best = [e[1] for e in expected]
    assert all(b >= a for a, b in zip(best, best[1:]))                 # el mejor nunca empeora

    first = build_training_session(config)
    first.run_iteration()
    resumed, _ = load_training_session(save_training_session(first, tmp_path / "c.npz", config))
    assert [summary(resumed.run_iteration()) for _ in range(2)] == expected[1:]


def test_strategy_can_be_chosen_by_name_and_all_three_are_available():
    from bootstrap import available_strategies
    plugins = available_strategies()
    assert sorted(plugins) == ["aco_routes", "aco_rules", "genetic"]
    for plugin in plugins.values():
        assert plugin.label and plugin.short_label and len(plugin.short_label) <= 12
