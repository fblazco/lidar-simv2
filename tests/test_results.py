"""Corridas terminadas: resumen, guardado y comparación entre dos."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

from bootstrap import build_training_session, finish_run
from config import load_config
from optimization.results import RunRecord, compare_runs, list_runs, load_run, save_run, summary_rows
from optimization.training import IterationStats

ROOT = Path(__file__).resolve().parent.parent


def stats(iteration, best, mean, success, validation=None, seconds=2.0, collisions=5):
    return IterationStats(
        iteration=iteration, evaluations=iteration * 10, episodes=iteration * 20, best_fitness=best,
        mean_fitness=mean, worst_fitness=-30.0, success_rate=success, collisions=collisions,
        mean_distance=12.0, mean_time=8.0, validation_fitness=validation,
        validation_success_rate=None if validation is None else 0.4, training_seeds=[1, 2],
        strategy={"alpha": 1.0}, seconds=seconds,
    )


def record(run_id="a", strategy="genetic", history=None, **overrides):
    history = history or [stats(1, 100.0, 10.0, 0.0, 50.0), stats(2, 600.0, 90.0, 0.2, 120.0),
                          stats(3, 600.0, 150.0, 0.5, 110.0)]
    data = dict(run_id=run_id, strategy=strategy, label=strategy.upper(), finished_at="2026-11-14T10:00:00",
                seed=7, population_size=10, generalizes=True, training_seeds=[1, 2], validation_seeds=[3],
                fixed_maps=[], history=[h.to_dict() for h in history])
    data.update(overrides)
    return RunRecord(**data)


def test_record_derives_the_summary_figures_from_its_history():
    metrics = record().metrics()
    assert metrics["iterations"] == 3 and metrics["evaluations"] == 30
    assert metrics["best_fitness"] == 600.0 and metrics["best_iteration"] == 2
    assert metrics["final_mean_fitness"] == 150.0
    assert metrics["final_success_rate"] == 0.5 and metrics["best_success_rate"] == 0.5
    assert metrics["first_success_iteration"] == 2
    assert metrics["validation_fitness"] == 110.0 and metrics["validation_success_rate"] == 0.4
    assert metrics["seconds"] == pytest.approx(6.0) and metrics["seconds_per_iteration"] == pytest.approx(2.0)


def test_metrics_that_do_not_apply_are_reported_as_missing():
    never = record(history=[stats(1, -5.0, -20.0, 0.0), stats(2, -1.0, -10.0, 0.0)], generalizes=False).metrics()
    assert never["first_success_iteration"] is None
    assert never["validation_fitness"] is None and never["validation_success_rate"] is None


def test_runs_are_saved_as_json_and_load_back_identical(tmp_path):
    original = record("corrida_1")
    path = save_run(original, tmp_path)
    assert path == tmp_path / "corrida_1.json"
    assert json.loads(path.read_text(encoding="utf-8"))["strategy"] == "genetic"
    assert load_run(path) == original


def test_runs_are_listed_from_newest_to_oldest_and_bad_files_are_skipped(tmp_path):
    save_run(record("vieja", finished_at="2026-11-13T09:00:00"), tmp_path)
    save_run(record("nueva", finished_at="2026-11-14T09:00:00"), tmp_path)
    (tmp_path / "rota.json").write_text("{no es json", encoding="utf-8")
    assert [r.run_id for r in list_runs(tmp_path)] == ["nueva", "vieja"]
    assert list_runs(tmp_path / "no_existe") == []


def test_summary_rows_are_readable_text():
    rows = dict(summary_rows(record()))
    assert rows["Mejor fitness"] == "600.0"
    assert rows["Tasa de éxito final"] == "50.0 %"
    assert rows["Generación del primer éxito"] == "2"
    assert rows["Tiempo total"] == "6.0 s"


def test_comparison_marks_the_better_run_for_each_metric():
    slow = record("a", "genetic")
    fast = record("b", "aco_rules", history=[stats(1, 650.0, 200.0, 0.6, 300.0, seconds=1.0, collisions=2)])
    rows = {label: (a, b, winner) for label, a, b, winner in compare_runs(slow, fast)}
    assert rows["Mejor fitness"] == ("600.0", "650.0", "b")
    assert rows["Tasa de éxito final"][2] == "b"
    assert rows["Generación del primer éxito"] == ("2", "1", "b")       # antes es mejor
    assert rows["Colisiones (última generación)"] == ("5", "2", "b")  # menos es mejor
    assert rows["Tiempo por generación"][2] == "b"
    assert rows["Generaciones"] == ("3", "1", None)                       # informativo: sin ganador
    assert rows["Algoritmo"] == ("GENETIC", "ACO_RULES", None)


def test_comparison_handles_ties_and_metrics_missing_in_one_run():
    with_validation = record("a")
    without = record("b", "aco_routes", generalizes=False,
                     history=[stats(1, 100.0, 10.0, 0.0), stats(2, 600.0, 90.0, 0.2), stats(3, 600.0, 150.0, 0.5)])
    rows = {label: (a, b, winner) for label, a, b, winner in compare_runs(with_validation, without)}
    assert rows["Mejor fitness"] == ("600.0", "600.0", None)
    assert rows["Éxito en validación"] == ("40.0 %", "no aplica", None)


def tiny_config(**training):
    return load_config(overrides={
        "map": {"cols": 16, "rows": 10}, "simulation": {"max_time": 6.0}, "policy": {"hidden_layers": [4]},
        "generator": {"static_obstacles": [1, 2], "dynamic_obstacles": [1, 1]},
        "training": {"population_size": 6, "visible_agents": 0, "scenarios_per_candidate": 2,
                     "validation_scenarios": 2, "stall_time": 1.5, "resample_scenarios_every": 0, **training},
    })


def test_finishing_a_training_session_writes_its_run_record(tmp_path):
    config = tiny_config(strategy="aco_rules")
    session = build_training_session(config)
    assert finish_run(session, config, tmp_path, "vacia") is None          # sin generaciones no hay nada que resumir
    for _ in range(2):
        session.run_iteration()
    saved = finish_run(session, config, tmp_path, "mi_corrida")
    assert saved.run_id == "mi_corrida" and saved.strategy == "aco_rules"
    assert saved.label.startswith("Colonia de hormigas") and saved.population_size == 6
    assert saved.metrics()["iterations"] == 2 and saved.generalizes
    assert saved.training_seeds == session.scenarios.training_seeds(0)
    assert load_run(tmp_path / "mi_corrida.json") == saved


def run_cli(*args):
    return subprocess.run([sys.executable, "main.py", *args], cwd=ROOT, capture_output=True, text=True)


def test_cli_trains_with_the_chosen_algorithm_then_lists_and_compares_runs(tmp_path):
    config = tmp_path / "tiny.json"
    config.write_text(json.dumps({
        "map": {"cols": 16, "rows": 10}, "simulation": {"max_time": 4.0}, "policy": {"hidden_layers": [4]},
        "training": {"population_size": 4, "scenarios_per_candidate": 1, "validation_scenarios": 1,
                     "stall_time": 1.0, "checkpoint_every": 0},
    }))
    base = ["--config", str(config), "--base-dir", str(tmp_path)]
    for strategy in ("genetic", "aco_rules", "aco_routes"):
        result = run_cli("train", "--strategy", strategy, "--generations", "2", *base)
        assert result.returncode == 0, result.stderr
        assert "Resumen de la corrida" in result.stdout
        assert (tmp_path / "logs" / "runs" / f"{strategy}.json").exists()
        assert (tmp_path / "models" / f"{strategy}.npz").exists()

    listed = run_cli("runs", "--base-dir", str(tmp_path))
    assert listed.returncode == 0, listed.stderr
    assert all(name in listed.stdout for name in ("genetic", "aco_rules", "aco_routes"))

    compared = run_cli("compare", "genetic", "aco_rules", "--base-dir", str(tmp_path))
    assert compared.returncode == 0, compared.stderr
    assert "Mejor fitness" in compared.stdout and "Algoritmo" in compared.stdout

    unknown = run_cli("train", "--strategy", "pso", "--generations", "1", *base)
    assert unknown.returncode != 0 and "aco_rules" in unknown.stderr

    missing = run_cli("compare", "genetic", "no_existe", "--base-dir", str(tmp_path))
    assert missing.returncode != 0 and "no_existe" in missing.stderr


# --- evasión de obstáculos y estadística de la comparación -------------------------------------

from optimization.results import validation_significance, wilson_interval


def validated(iteration, successes, episodes=20, collisions=2, efficiency=0.9, **kwargs):
    """Estadísticas de una iteración con validación detallada."""
    item = stats(iteration, 600.0, 200.0, 0.5, validation=100.0, **kwargs)
    item.validation_success_rate = successes / episodes
    item.validation_episodes = episodes
    item.validation_collisions = collisions
    item.validation_efficiency = efficiency
    item.validation_time = 9.0
    item.iteration_episodes = 20
    item.path_efficiency = 0.8
    item.min_clearance = 0.6
    return item


def test_record_remembers_the_avoidance_algorithm_and_the_kind_of_maps():
    saved = record(avoidance="ftg", avoidance_label="FTG: Follow the Gap", map_mode="free", resampled=True)
    rows = dict(summary_rows(saved))
    assert rows["Evasión de obstáculos"] == "FTG: Follow the Gap"
    assert rows["Mapas"] == "navegación libre, nuevos en cada generación"
    assert record().avoidance == "learned"                    # las corridas anteriores no tenían capa de evasión


def test_records_saved_before_these_fields_existed_still_load(tmp_path):
    path = save_run(record("vieja"), tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    for key in ("avoidance", "avoidance_label", "map_mode", "resampled"):
        data.pop(key)
    for item in data["history"]:
        for key in ("iteration_episodes", "validation_episodes", "validation_collisions", "path_efficiency"):
            item.pop(key, None)
    path.write_text(json.dumps(data), encoding="utf-8")
    old = load_run(path)
    assert old.avoidance == "learned" and old.metrics()["validation_success_rate"] == 0.4


def test_metrics_cover_obstacle_avoidance_and_shortest_path():
    metrics = record(history=[validated(1, 6), validated(2, 12, collisions=1, efficiency=0.95)]).metrics()
    assert metrics["validation_success_rate"] == 0.6 and metrics["best_validation_success_rate"] == 0.6
    assert metrics["validation_collision_rate"] == pytest.approx(0.05)
    assert metrics["validation_efficiency"] == 0.95 and metrics["validation_time"] == 9.0
    assert metrics["recent_success_rate"] == 0.5 and metrics["recent_collision_rate"] == pytest.approx(0.25)
    assert metrics["path_efficiency"] == 0.8 and metrics["min_clearance"] == 0.6
    low, high = metrics["validation_interval"]
    assert low < 0.6 < high


def test_wilson_interval_bounds_a_success_rate():
    low, high = wilson_interval(8, 20)
    assert low == pytest.approx(0.219, abs=0.005) and high == pytest.approx(0.613, abs=0.005)
    assert wilson_interval(0, 20)[0] == 0.0 and wilson_interval(20, 20)[1] == 1.0
    assert wilson_interval(0, 0) == (0.0, 1.0)


def test_significance_tells_real_differences_from_noise():
    strong = record("a", history=[validated(1, 18)])
    weak = record("b", history=[validated(1, 4)])
    close = record("c", history=[validated(1, 16)])
    assert "p < 0.001" in validation_significance(strong, weak) and " es estadísticamente" in validation_significance(strong, weak)
    assert "no es estadísticamente" in validation_significance(strong, close)
    assert validation_significance(strong, record("d", generalizes=False)) is None      # sin validación no hay prueba


def test_comparison_shows_avoidance_and_the_new_metrics():
    learned = record("a", history=[validated(1, 8, collisions=6, efficiency=0.80)])
    ftg = record("b", avoidance="ftg", avoidance_label="FTG: Follow the Gap",
                 history=[validated(1, 14, collisions=2, efficiency=0.93)])
    rows = {label: (a, b, winner) for label, a, b, winner in compare_runs(learned, ftg)}
    assert rows["Evasión de obstáculos"] == ("Aprendida por el propio algoritmo", "FTG: Follow the Gap", None)
    assert rows["Éxito en validación"] == ("40.0 %", "70.0 %", "b")
    assert rows["Colisiones en validación"] == ("30.0 %", "10.0 %", "b")
    assert rows["Eficiencia del camino en validación"] == ("80.0 %", "93.0 %", "b")
    assert rows["Intervalo de confianza 95 %"][2] is None and "%" in rows["Intervalo de confianza 95 %"][0]


def test_cli_combines_navigation_avoidance_and_map_kind(tmp_path):
    config = tmp_path / "tiny.json"
    config.write_text(json.dumps({
        "map": {"cols": 16, "rows": 10}, "simulation": {"max_time": 4.0},
        "training": {"scenarios_per_candidate": 1, "validation_scenarios": 2, "stall_time": 1.0, "checkpoint_every": 0},
    }))
    base = ["--config", str(config), "--base-dir", str(tmp_path)]
    first = run_cli("train", "--strategy", "reactive", "--avoidance", "ftg", "--generations", "2", *base)
    second = run_cli("train", "--strategy", "reactive", "--avoidance", "apf", "--maps", "route",
                     "--generations", "2", *base)
    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    ftg = load_run(tmp_path / "logs" / "runs" / "reactive_ftg.json")
    apf = load_run(tmp_path / "logs" / "runs" / "reactive_apf.json")
    assert (ftg.avoidance, ftg.map_mode, ftg.resampled) == ("ftg", "free", True)
    assert (apf.avoidance, apf.map_mode) == ("apf", "route")
    listed = run_cli("runs", "--base-dir", str(tmp_path))
    assert "FTG" in listed.stdout and "APF" in listed.stdout
    compared = run_cli("compare", "reactive_ftg", "reactive_apf", "--base-dir", str(tmp_path))
    assert compared.returncode == 0, compared.stderr
    assert "Evasión de obstáculos" in compared.stdout and "significativa" in compared.stdout
    bad = run_cli("train", "--avoidance", "dwa", "--generations", "1", *base)
    assert bad.returncode != 0 and "ftg" in bad.stderr
