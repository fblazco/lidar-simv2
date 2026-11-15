"""Corridas de entrenamiento terminadas: resumen, guardado y comparación.

Una corrida es un entrenamiento con un algoritmo, desde su primera iteración
hasta que se da por finalizado. Su registro guarda el historial completo y de
él se derivan las cifras de resumen, de modo que dos corridas (del mismo
algoritmo o de algoritmos distintos) se comparan con las mismas métricas.
"""
from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from optimization.training import IterationStats

NOT_APPLICABLE = "no aplica"
RECENT = 10                       # iteraciones finales que se promedian (con mapas nuevos, una sola es ruidosa)
SIGNIFICANCE_LEVEL = 0.05
MAP_MODES = {"free": "navegación libre", "route": "seguimiento de ruta", "mixed": "libres y con ruta"}


def wilson_interval(successes: int, total: int, z: float = 1.96) -> Tuple[float, float]:
    """Intervalo de confianza (95 % por defecto) de una proporción, por el método de Wilson."""
    if total <= 0:
        return (0.0, 1.0)
    p = successes / total
    denominator = 1.0 + z * z / total
    center = (p + z * z / (2.0 * total)) / denominator
    half = z * math.sqrt(p * (1.0 - p) / total + z * z / (4.0 * total * total)) / denominator
    return (0.0 if successes == 0 else max(0.0, center - half), 1.0 if successes == total else min(1.0, center + half))


def proportions_p_value(successes_a: int, total_a: int, successes_b: int, total_b: int) -> float:
    """Valor p bilateral de la prueba z de dos proporciones."""
    pooled = (successes_a + successes_b) / (total_a + total_b)
    spread = math.sqrt(pooled * (1.0 - pooled) * (1.0 / total_a + 1.0 / total_b))
    if spread == 0.0:
        return 1.0
    z = abs(successes_a / total_a - successes_b / total_b) / spread
    return math.erfc(z / math.sqrt(2.0))


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
    avoidance: str = "learned"      # nombre del algoritmo de evasión de obstáculos
    avoidance_label: str = "Aprendida por el propio algoritmo"
    map_mode: str = ""              # free | route | mixed (vacío en corridas anteriores a este dato)
    resampled: bool = False          # si los mapas de entrenamiento cambiaban en cada generación

    def maps_text(self) -> str:
        if not self.map_mode:
            return "sin dato"
        change = "nuevos en cada generación" if self.resampled else "fijos"
        return f"{MAP_MODES.get(self.map_mode, self.map_mode)}, {change}"

    def validation_counts(self) -> Optional[Tuple[int, int]]:
        """(llegadas, mapas) de la última validación, o None si no hubo o no se guardó el detalle."""
        if not self.generalizes:
            return None
        done = [h for h in self.stats() if h.validation_success_rate is not None and h.validation_episodes]
        if not done:
            return None
        return round(done[-1].validation_success_rate * done[-1].validation_episodes), done[-1].validation_episodes

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
        recent = history[-RECENT:]
        recent_episodes = sum(h.iteration_episodes for h in recent)
        efficient = [h.path_efficiency for h in recent if h.path_efficiency > 0.0]
        measured = [h.min_clearance for h in recent if h.iteration_episodes]
        checked = validated[-1] if validated else None
        counts = self.validation_counts()
        return {
            "iterations": last.iteration,
            "evaluations": last.evaluations,
            "best_fitness": best.best_fitness,
            "best_iteration": next(h.iteration for h in history if h.best_fitness == best.best_fitness),
            "final_mean_fitness": last.mean_fitness,
            "final_success_rate": last.success_rate,
            "recent_success_rate": sum(h.success_rate for h in recent) / len(recent),
            "best_success_rate": max(h.success_rate for h in history),
            "first_success_iteration": first_success,
            "final_collisions": last.collisions,
            "recent_collision_rate": sum(h.collisions for h in recent) / recent_episodes if recent_episodes else None,
            "path_efficiency": sum(efficient) / len(efficient) if efficient else None,
            "min_clearance": sum(measured) / len(measured) if measured else None,
            "validation_fitness": checked.validation_fitness if checked else None,
            "validation_success_rate": checked.validation_success_rate if checked else None,
            "validation_interval": wilson_interval(*counts) if counts else None,
            "best_validation_success_rate": max(h.validation_success_rate for h in validated) if validated else None,
            "validation_collision_rate": (checked.validation_collisions / checked.validation_episodes
                                          if checked and checked.validation_episodes else None),
            "validation_efficiency": checked.validation_efficiency if checked else None,
            "validation_time": checked.validation_time if checked else None,
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
    ("recent_success_rate", "Éxito medio (últimas 10 gen.)", "percent", "high", "-"),
    ("best_success_rate", "Mejor tasa de éxito", "percent", "high", "-"),
    ("first_success_iteration", "Generación del primer éxito", "int", "low", "nunca"),
    ("final_collisions", "Colisiones (última generación)", "int", "low", "-"),
    ("recent_collision_rate", "Colisiones (últimas 10 gen.)", "percent", "low", "sin dato"),
    ("path_efficiency", "Eficiencia del camino", "percent", "high", "sin dato"),
    ("min_clearance", "Holgura mínima media", "float2", "high", "sin dato"),
    ("validation_fitness", "Fitness en validación", "float", "high", NOT_APPLICABLE),
    ("validation_success_rate", "Éxito en validación", "percent", "high", NOT_APPLICABLE),
    ("validation_interval", "Intervalo de confianza 95 %", "interval", None, NOT_APPLICABLE),
    ("best_validation_success_rate", "Mejor éxito en validación", "percent", "high", NOT_APPLICABLE),
    ("validation_collision_rate", "Colisiones en validación", "percent", "low", NOT_APPLICABLE),
    ("validation_efficiency", "Eficiencia del camino en validación", "percent", "high", NOT_APPLICABLE),
    ("validation_time", "Tiempo al destino en validación", "seconds", "low", NOT_APPLICABLE),
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
    if kind == "float2":
        return f"{value:.2f}"
    if kind == "interval":
        return f"{value[0] * 100:.1f} – {value[1] * 100:.1f} %"
    return f"{value:.1f}"


def summary_rows(record: RunRecord) -> List[Tuple[str, str]]:
    """Resumen de una corrida como filas (etiqueta, texto)."""
    metrics = record.metrics()
    rows = [("Algoritmo", record.label), ("Evasión de obstáculos", record.avoidance_label),
            ("Mapas", record.maps_text())]
    rows += [(label, _text(metrics[key], kind, missing)) for key, label, kind, _, missing in METRICS]
    return rows


def compare_runs(a: RunRecord, b: RunRecord) -> List[Tuple[str, str, str, Optional[str]]]:
    """Filas (etiqueta, texto de A, texto de B, ganador "a"/"b"/None) con las mismas métricas para ambas."""
    first, second = a.metrics(), b.metrics()
    rows: List[Tuple[str, str, str, Optional[str]]] = [
        ("Algoritmo", a.label, b.label, None),
        ("Evasión de obstáculos", a.avoidance_label, b.avoidance_label, None),
        ("Mapas", a.maps_text(), b.maps_text(), None),
    ]
    for key, label, kind, better, missing in METRICS:
        va, vb = first[key], second[key]
        winner = None
        if better is not None and va is not None and vb is not None and va != vb:
            winner = "a" if (va > vb) == (better == "high") else "b"
        rows.append((label, _text(va, kind, missing), _text(vb, kind, missing), winner))
    return rows


def validation_significance(a: RunRecord, b: RunRecord) -> Optional[str]:
    """Frase que dice si la diferencia de éxito en validación entre dos corridas es significativa.

    Usa la prueba z de dos proporciones sobre la última validación de cada una.
    Devuelve None si alguna no tiene validación con el detalle necesario.
    """
    first, second = a.validation_counts(), b.validation_counts()
    if first is None or second is None:
        return None
    p_value = proportions_p_value(*first, *second)
    shown = "p < 0.001" if p_value < 0.001 else f"p = {p_value:.3f}"
    verdict = "es" if p_value < SIGNIFICANCE_LEVEL else "no es"
    return (f"Éxito en validación: {first[0]} de {first[1]} mapas frente a {second[0]} de {second[1]}. "
            f"La diferencia {verdict} estadísticamente significativa ({shown}, prueba z de dos proporciones).")


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
    text = "\n".join("  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)).rstrip() for row in table)
    verdict = validation_significance(a, b)
    return text + (f"\n\n{verdict}" if verdict else "")


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
    return sorted(records, key=lambda r: (r.finished_at, r.run_id), reverse=True)   # a igual segundo, por nombre
