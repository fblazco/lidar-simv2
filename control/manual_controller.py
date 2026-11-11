"""Control manual: la interfaz traduce el teclado a ``set_command``.

No depende de Pygame; cualquier fuente de entrada puede manejarlo.
"""
from __future__ import annotations

from control.controller import Action, Controller, Observation


class ManualController(Controller):
    def __init__(self) -> None:
        self._command = Action()

    def set_command(self, steering: float, acceleration: float) -> None:
        self._command = Action(steering, acceleration).clipped()

    def reset(self) -> None:
        self._command = Action()

    def act(self, observation: Observation) -> Action:
        return self._command
