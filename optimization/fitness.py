"""Fitness de un episodio. Común a cualquier algoritmo de optimización."""
from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Sequence


@dataclass(frozen=True)
class EpisodeMetrics:
    progress: float              # mejor avance hacia el destino, 0..1
    reached_goal: bool
    collided: bool
    stalled: bool                # episodio cortado por no avanzar
    time: float                  # tiempo de simulación usado (s)
    time_limit: float
    distance: float              # distancia recorrida
    mean_deviation: float        # desvío lateral medio respecto del camino
    steering_change: float       # cambio medio de dirección entre pasos (0..2)
    acceleration_change: float   # cambio medio de aceleración entre pasos (0..2)


@dataclass
class FitnessWeights:
    progress: float = 100.0         # por completar el 100 % del recorrido
    goal: float = 500.0             # premio por llegar (muy superior a solo sobrevivir)
    time_bonus: float = 100.0       # extra por llegar rápido (proporcional al tiempo sobrante)
    collision: float = 20.0         # castigo por chocar
    stall: float = 30.0             # castigo por quedarse detenido (mayor que chocar)
    deviation: float = 30.0         # castigo máximo por apartarse del camino
    deviation_scale: float = 2.0    # desvío medio (unidades) que recibe el castigo máximo
    smoothness: float = 10.0        # castigo máximo por control brusco

    @classmethod
    def from_dict(cls, data: dict) -> "FitnessWeights":
        return cls(**{f.name: data[f.name] for f in fields(cls) if f.name in data})


class FitnessFunction:
    def __init__(self, weights: FitnessWeights) -> None:
        self.weights = weights

    def __call__(self, m: EpisodeMetrics) -> float:
        w = self.weights
        score = w.progress * m.progress
        if m.reached_goal:
            score += w.goal + w.time_bonus * max(0.0, 1.0 - m.time / m.time_limit)
        if m.collided:
            score -= w.collision
        if m.stalled:
            score -= w.stall
        score -= w.deviation * min(1.0, m.mean_deviation / w.deviation_scale)
        score -= w.smoothness * min(1.0, (m.steering_change + m.acceleration_change) / 2.0)
        return float(score)

    @staticmethod
    def aggregate(scores: Sequence[float]) -> float:
        """Fitness de un candidato: media de sus episodios en todos los escenarios."""
        return float(sum(scores) / len(scores)) if scores else 0.0
