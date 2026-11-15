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
                     "validation_scenarios": 2, "stall_time": 1.5, **training},
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
