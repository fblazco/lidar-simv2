"""Selección de padres."""
from __future__ import annotations

import numpy as np


def tournament_selection(fitness: np.ndarray, tournament_size: int, rng: np.random.Generator) -> int:
    """Índice del mejor entre ``tournament_size`` individuos tomados al azar."""
    size = max(1, min(int(tournament_size), len(fitness)))
    contenders = rng.choice(len(fitness), size=size, replace=False)
    return int(contenders[np.argmax(fitness[contenders])])
