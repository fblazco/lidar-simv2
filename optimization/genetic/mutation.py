"""Mutación gaussiana de pesos."""
from __future__ import annotations

import numpy as np


def gaussian_mutation(genes: np.ndarray, rate: float, sigma: float, rng: np.random.Generator) -> np.ndarray:
    """Copia de ``genes`` donde cada gen recibe ruido N(0, sigma) con probabilidad ``rate``."""
    mutated = genes.copy()
    mask = rng.random(genes.shape[0]) < rate
    mutated[mask] += rng.normal(0.0, sigma, size=int(mask.sum()))
    return mutated
