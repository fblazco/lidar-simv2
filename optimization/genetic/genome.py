"""Genoma del GA: un vector plano de reales (los pesos y sesgos de la red)."""
from __future__ import annotations

import numpy as np


def random_population(size: int, genome_length: int, scale: float, rng: np.random.Generator) -> np.ndarray:
    """Población inicial: una fila por individuo, genes ~ N(0, scale)."""
    return rng.normal(0.0, scale, size=(size, genome_length))


def population_diversity(population: np.ndarray) -> float:
    """Diversidad genética: desviación estándar media de cada gen en la población."""
    return float(np.mean(np.std(population, axis=0)))
