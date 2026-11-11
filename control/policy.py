"""Políticas: funciones que transforman un vector de entrada en salidas de control."""
from __future__ import annotations

from typing import Protocol, Sequence

import numpy as np


class Policy(Protocol):
    def __call__(self, inputs: np.ndarray) -> np.ndarray: ...


class MLPPolicy:
    """Perceptrón multicapa de arquitectura fija con activación tanh.

    Sus parámetros (pesos y sesgos) se leen y escriben como un único vector
    plano, que es lo que cualquier optimizador puede manipular sin conocer la red.
    """

    def __init__(self, layer_sizes: Sequence[int]) -> None:
        self.layer_sizes = [int(n) for n in layer_sizes]
        if len(self.layer_sizes) < 2:
            raise ValueError("La red necesita al menos capa de entrada y de salida")
        self._weights = [np.zeros((a, b)) for a, b in zip(self.layer_sizes, self.layer_sizes[1:])]
        self._biases = [np.zeros(b) for b in self.layer_sizes[1:]]

    @staticmethod
    def parameter_count(layer_sizes: Sequence[int]) -> int:
        return int(sum(a * b + b for a, b in zip(layer_sizes, layer_sizes[1:])))

    def set_parameters(self, parameters: np.ndarray) -> None:
        flat = np.asarray(parameters, dtype=float).ravel()
        expected = self.parameter_count(self.layer_sizes)
        if flat.size != expected:
            raise ValueError(f"La red espera {expected} parámetros y recibió {flat.size}")
        offset = 0
        for i, (a, b) in enumerate(zip(self.layer_sizes, self.layer_sizes[1:])):
            self._weights[i] = flat[offset:offset + a * b].reshape(a, b).copy()
            offset += a * b
            self._biases[i] = flat[offset:offset + b].copy()
            offset += b

    def get_parameters(self) -> np.ndarray:
        return np.concatenate([np.concatenate([w.ravel(), b]) for w, b in zip(self._weights, self._biases)])

    def __call__(self, inputs: np.ndarray) -> np.ndarray:
        x = inputs
        for weights, bias in zip(self._weights, self._biases):
            x = np.tanh(x @ weights + bias)
        return x
