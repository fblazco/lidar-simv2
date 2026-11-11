"""Operadores de cruce. Devuelven un hijo nuevo; no modifican a los padres."""
from __future__ import annotations

from typing import Callable, Dict

import numpy as np

Crossover = Callable[[np.ndarray, np.ndarray, np.random.Generator], np.ndarray]


def uniform_crossover(a: np.ndarray, b: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Cada gen viene de uno de los dos padres con igual probabilidad."""
    return np.where(rng.random(a.shape[0]) < 0.5, a, b)


def single_point_crossover(a: np.ndarray, b: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Prefijo de un padre y sufijo del otro, con un punto de corte al azar."""
    cut = int(rng.integers(1, a.shape[0])) if a.shape[0] > 1 else 0
    return np.concatenate((a[:cut], b[cut:]))


def blend_crossover(a: np.ndarray, b: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Cada gen es una mezcla aleatoria entre los valores de ambos padres."""
    alpha = rng.random(a.shape[0])
    return alpha * a + (1.0 - alpha) * b


CROSSOVERS: Dict[str, Crossover] = {
    "uniform": uniform_crossover,
    "single_point": single_point_crossover,
    "blend": blend_crossover,
}


def get_crossover(name: str) -> Crossover:
    if name not in CROSSOVERS:
        raise ValueError(f"Crossover desconocido: '{name}'. Opciones: {', '.join(CROSSOVERS)}")
    return CROSSOVERS[name]
