"""Contrato común de los algoritmos de aprendizaje (GA hoy; PSO, ACO, ABC después).

El contrato es de tipo "pedir / informar": la estrategia entrega candidatos
para evaluar y recibe sus resultados. No impone ninguna representación interna:
``Candidate.solution`` es opaca para el resto del sistema (un genoma, la
posición de una partícula, una fuente de alimento, un camino construido...).
Quien sabe convertir una solución en un controlador es la ``controller_factory``
que cada plugin entrega junto con su estrategia (ver ``optimization/registry.py``).

Una estrategia nunca toca la física ni el renderizado.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from optimization.fitness import EpisodeMetrics


@dataclass
class Candidate:
    id: int          # único dentro de la tanda entregada por ask()
    solution: Any    # representación propia del algoritmo


@dataclass
class CandidateResult:
    candidate: Candidate
    fitness: float
    episodes: List[EpisodeMetrics] = field(default_factory=list)


@dataclass
class StrategyState:
    """Progreso serializable: ``meta`` compatible con JSON y arreglos NumPy aparte."""

    meta: Dict[str, Any] = field(default_factory=dict)
    arrays: Dict[str, np.ndarray] = field(default_factory=dict)


class LearningStrategy(ABC):
    name: str = "strategy"

    @property
    @abstractmethod
    def iteration(self) -> int:
        """Iteraciones completadas (generaciones en GA, ciclos en ABC, etc.)."""

    @abstractmethod
    def ask(self) -> List[Candidate]:
        """Candidatos a evaluar ahora. Repetir la llamada sin ``tell`` devuelve los mismos."""

    @abstractmethod
    def tell(self, results: Sequence[CandidateResult]) -> None:
        """Recibe los resultados de TODOS los candidatos pedidos y actualiza el estado interno."""

    @abstractmethod
    def best(self) -> Optional[Tuple[Any, float]]:
        """(solución, fitness) del mejor candidato de la última iteración, o None."""

    @abstractmethod
    def statistics(self) -> Dict[str, float]:
        """Estadísticas propias del algoritmo (p. ej. tasa de mutación, diversidad)."""

    @abstractmethod
    def get_state(self) -> StrategyState:
        """Estado completo para un checkpoint."""

    @abstractmethod
    def set_state(self, state: StrategyState) -> None:
        """Restaura un estado guardado con ``get_state``."""
