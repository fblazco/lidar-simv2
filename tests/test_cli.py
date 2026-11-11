"""Entrenamiento sin ventana desde la línea de comandos."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

TINY = {
    "map": {"cols": 16, "rows": 10},
    "simulation": {"max_time": 4.0},
    "policy": {"hidden_layers": [4]},
    "training": {"population_size": 4, "scenarios_per_candidate": 1, "validation_scenarios": 1,
                 "stall_time": 1.0, "checkpoint_every": 1},
}


def run_cli(*args):
    return subprocess.run([sys.executable, "main.py", *args], cwd=ROOT, capture_output=True, text=True)


def test_headless_training_writes_checkpoint_and_log_and_can_resume(tmp_path):
    config = tmp_path / "tiny.json"
    config.write_text(json.dumps(TINY))
    first = run_cli("train", "--generations", "2", "--config", str(config), "--name", "prueba",
                    "--base-dir", str(tmp_path))
    assert first.returncode == 0, first.stderr
    checkpoint = tmp_path / "models" / "prueba.npz"
    log = tmp_path / "logs" / "prueba.jsonl"
    assert checkpoint.exists()
    lines = [json.loads(line) for line in log.read_text().splitlines()]
    assert [line["iteration"] for line in lines] == [1, 2]
    assert lines[0]["training_seeds"] and "best_fitness" in lines[0]
    assert "gen" in first.stdout.lower()

    second = run_cli("train", "--generations", "1", "--resume", str(checkpoint), "--name", "prueba",
                     "--base-dir", str(tmp_path))
    assert second.returncode == 0, second.stderr
    lines = [json.loads(line) for line in log.read_text().splitlines()]
    assert [line["iteration"] for line in lines] == [1, 2, 3]
