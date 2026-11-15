"""Corridas de entrenamiento terminadas: resumen, guardado y comparación.

Una corrida es un entrenamiento con un algoritmo, desde su primera iteración
hasta que se da por finalizado. Su registro guarda el historial completo y de
él se derivan las cifras de resumen, de modo que dos corridas (del mismo
algoritmo o de algoritmos distintos) se comparan con las mismas métricas.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from optimization.training import IterationStats

NOT_APPLICABLE = "no aplica"


@dataclass
class RunRecord:
    run_id: str
    strategy: str                   # nombre del plugin
    label: str                      # nombre visible del algoritmo
    finished_at: str                # fecha y hora ISO en que se finalizó
    seed: int
    population_size: int
    generalizes: bool               # si lo aprendido sirve en mapas no vistos (hay validación)
    training_seeds: List[int] = field(default_factory=list)
    validation_seeds: List[int] = field(default_factory=list)
    fixed_maps: List[str] = field(default_factory=list)
    history: List[dict] = field(default_factory=list)   # un IterationStats por iteración

    def stats(self) -> List[IterationStats]:
        return [IterationStats.from_dict(item) for item in self.history]

    def metrics(self) -> Dict[str, Optional[float]]:
        """Cifras de resumen derivadas del historial. ``None`` cuando una no aplica."""
        history = self.stats()
        last = history[-1]
        best = max(history, key=lambda h: h.best_fitness)
        first_success = next((h.iteration for h in history if h.success_rate > 0.0), None)
        validated = [h for h in history if h.validation_fitness is not None] if self.generalizes else []
        seconds = sum(h.seconds for h in history)
        return {
            "iterations": last.iteration,
            "evaluations": last.evaluations,
            "best_fitness": best.best_fitness,
            "best_iteration": next(h.iteration for h in history if h.best_fitness == best.best_fitness),
            "final_mean_fitness": last.mean_fitness,
            "final_success_rate": last.success_rate,
            "best_success_rate": max(h.success_rate for h in history),
            "first_success_iteration": first_success,
            "validation_fitness": validated[-1].validation_fitness if validated else None,
            "validation_success_rate": validated[-1].validation_success_rate if validated else None,
            "final_collisions": last.collisions,
            "mean_distance": last.mean_distance,
            "mean_time": last.mean_time,
            "seconds": seconds,
            "seconds_per_iteration": seconds / len(history),
        }


# (clave, etiqueta, formato, qué es mejor: "high", "low" o None si solo informa, texto cuando falta)
METRICS: List[Tuple[str, str, str, Optional[str], str]] = [
    ("iterations", "Generaciones", "int", None, "-"),
    ("evaluations", "Evaluaciones", "int", None, "-"),
    ("best_fitness", "Mejor fitness", "float", "high", "-"),
    ("best_iteration", "Generación del mejor fitness", "int", "low", "-"),
    ("final_mean_fitness", "Fitness promedio final", "float", "high", "-"),
    ("final_success_rate", "Tasa de éxito final", "percent", "high", "-"),
    ("best_success_rate", "Mejor tasa de éxito", "percent", "high", "-"),
    ("first_success_iteration", "Generación del primer éxito", "int", "low", "nunca"),
    ("validation_fitness", "Fitness en validación", "float", "high", NOT_APPLICABLE),
    ("validation_success_rate", "Éxito en validación", "percent", "high", NOT_APPLICABLE),
    ("final_collisions", "Colisiones (última generación)", "int", "low", "-"),
    ("mean_distance", "Distancia media final", "float", None, "-"),
    ("mean_time", "Tiempo medio de navegación", "seconds", None, "-"),
    ("seconds", "Tiempo total", "seconds", None, "-"),
    ("seconds_per_iteration", "Tiempo por generación", "seconds", "low", "-"),
]


def _text(value: Optional[float], kind: str, missing: str) -> str:
    if value is None:
        return missing
    if kind == "int":
        return str(int(value))
    if kind == "percent":
        return f"{value * 100:.1f} %"
    if kind == "seconds":
        return f"{value:.1f} s"
    return f"{value:.1f}"


def summary_rows(record: RunRecord) -> List[Tuple[str, str]]:
    """Resumen de una corrida como filas (etiqueta, texto)."""
    metrics = record.metrics()
    rows = [("Algoritmo", record.label)]
    rows += [(label, _text(metrics[key], kind, missing)) for key, label, kind, _, missing in METRICS]
    return rows


def compare_runs(a: RunRecord, b: RunRecord) -> List[Tuple[str, str, str, Optional[str]]]:
    """Filas (etiqueta, texto de A, texto de B, ganador "a"/"b"/None) con las mismas métricas para ambas."""
    first, second = a.metrics(), b.metrics()
    rows: List[Tuple[str, str, str, Optional[str]]] = [("Algoritmo", a.label, b.label, None)]
    for key, label, kind, better, missing in METRICS:
        va, vb = first[key], second[key]
        winner = None
        if better is not None and va is not None and vb is not None and va != vb:
            winner = "a" if (va > vb) == (better == "high") else "b"
        rows.append((label, _text(va, kind, missing), _text(vb, kind, missing), winner))
    return rows


def format_summary(record: RunRecord) -> str:
    rows = summary_rows(record)
    width = max(len(label) for label, _ in rows)
    return "\n".join(f"{label:<{width}}  {text}" for label, text in rows)


def format_comparison(a: RunRecord, b: RunRecord) -> str:
    """Tabla de texto; un asterisco marca la corrida mejor en cada métrica."""
    rows = compare_runs(a, b)
    table = [("", f"A: {a.run_id}", f"B: {b.run_id}")]
    table += [(label, ta + (" *" if winner == "a" else ""), tb + (" *" if winner == "b" else ""))
              for label, ta, tb, winner in rows]
    widths = [max(len(row[i]) for row in table) for i in range(3)]
    return "\n".join("  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)).rstrip() for row in table)


def _safe_id(run_id: str) -> str:
    return re.sub(r"[^\w\-]+", "_", run_id).strip("_") or "corrida"


def save_run(record: RunRecord, directory: Union[str, Path]) -> Path:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{_safe_id(record.run_id)}.json"
    path.write_text(json.dumps(asdict(record), indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def load_run(path: Union[str, Path]) -> RunRecord:
    return RunRecord(**json.loads(Path(path).read_text(encoding="utf-8")))


def list_runs(directory: Union[str, Path]) -> List[RunRecord]:
    """Corridas guardadas, de la más reciente a la más antigua. Los archivos ilegibles se omiten."""
    directory = Path(directory)
    records = []
    for path in directory.glob("*.json") if directory.is_dir() else []:
        try:
            record = load_run(path)
            record.metrics()
        except (OSError, ValueError, TypeError, KeyError, IndexError):
            continue
        records.append(record)
    return sorted(records, key=lambda r: r.finished_at, reverse=True)
