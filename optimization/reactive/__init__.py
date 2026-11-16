"""Plugin de referencia: navegación sin aprendizaje.

No optimiza nada: en cada iteración evalúa el mismo controlador, que apunta al
objetivo. Con mapas nuevos en cada iteración, sus estadísticas miden cuánto
rinde esa navegación mínima y, sobre todo, cuánto aporta por sí solo el
algoritmo de evasión elegido (FTG, APF).
"""
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from control.goal_controller import GoalSeekingController
from optimization.registry import StrategyBundle, StrategyPlugin, for_any_scenario
from optimization.strategy import Candidate, CandidateResult, LearningStrategy, StrategyState

SOLUTION = "ir-al-objetivo"     # no hay nada que aprender: la solución es siempre la misma


class GoalSeeking(LearningStrategy):
    name = "reactive"

    def __init__(self) -> None:
        self._iteration = 0
        self._fitness: Optional[float] = None

    @property
    def iteration(self) -> int:
        return self._iteration

    def ask(self) -> List[Candidate]:
        return [Candidate(0, SOLUTION)]

    def tell(self, results: Sequence[CandidateResult]) -> None:
        if len(results) != 1:
            raise ValueError("La referencia sin aprendizaje evalúa un único controlador por iteración")
        self._fitness = float(results[0].fitness)
        self._iteration += 1

    def best(self) -> Optional[Tuple[Any, float]]:
        return (SOLUTION, self._fitness) if self._fitness is not None else None

    def statistics(self) -> Dict[str, float]:
        return {}

    def get_state(self) -> StrategyState:
        return StrategyState({"iteration": self._iteration, "fitness": self._fitness}, {})

    def set_state(self, state: StrategyState) -> None:
        self._iteration = int(state.meta["iteration"])
        self._fitness = state.meta["fitness"]


def build(config: dict) -> StrategyBundle:
    settings = dict(config.get("reactive", {}))
    return StrategyBundle(GoalSeeking(), for_any_scenario(lambda solution: GoalSeekingController(**settings)))


ASSETS = Path(__file__).parent      # el ícono y la escena viajan con el plugin

PLUGIN = StrategyPlugin(
    name="reactive",
    label="Sin aprendizaje: ir directo al objetivo (referencia)",
    build=build,
    short_label="Sin aprender",
    description="No aprende: apunta al objetivo. Es la línea de base y permite medir FTG y APF por sí solos.",
    icon=str(ASSETS / "icon.svg"),
    demo=str(ASSETS / "demo.json"),
)
