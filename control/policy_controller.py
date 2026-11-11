"""Controlador que delega la decisión en una política numérica."""
from __future__ import annotations

from typing import Sequence

import numpy as np

from control.controller import Action, Controller, Observation
from control.observation_builder import ObservationBuilder
from control.policy import MLPPolicy, Policy

N_OUTPUTS = 2  # steering, acceleration


class PolicyController(Controller):
    """Observación -> vector (ObservationBuilder) -> política -> Action."""

    def __init__(self, policy: Policy, observation_builder: ObservationBuilder) -> None:
        self.policy = policy
        self.observation_builder = observation_builder

    def act(self, observation: Observation) -> Action:
        outputs = self.policy(self.observation_builder.build(observation))
        return Action(float(outputs[0]), float(outputs[1]))


class MLPControllerFactory:
    """Construye controladores a partir de un vector plano de parámetros.

    Es el puente entre un optimizador de vectores reales (GA hoy; PSO o ABC
    mañana) y el simulador: el optimizador no conoce la red ni el vehículo.
    """

    def __init__(self, observation_builder: ObservationBuilder, hidden_layers: Sequence[int]) -> None:
        self.observation_builder = observation_builder
        self.layer_sizes = [observation_builder.size, *[int(h) for h in hidden_layers], N_OUTPUTS]

    @property
    def parameter_count(self) -> int:
        return MLPPolicy.parameter_count(self.layer_sizes)

    def __call__(self, parameters: np.ndarray) -> PolicyController:
        policy = MLPPolicy(self.layer_sizes)
        policy.set_parameters(parameters)
        return PolicyController(policy, self.observation_builder)


def build_mlp_controller_factory(config: dict) -> MLPControllerFactory:
    """Fábrica de controladores MLP según las secciones lidar, observation y policy."""
    builder = ObservationBuilder(num_rays=config["lidar"]["num_rays"], **config["observation"])
    return MLPControllerFactory(builder, config["policy"]["hidden_layers"])
