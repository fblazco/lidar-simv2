"""Descubrimiento de plugins de optimización.

Cada subpaquete de ``optimization/`` que exponga un atributo ``PLUGIN`` es un
algoritmo disponible. Nada fuera de ese subpaquete lo importa por nombre: si se
borra la carpeta, el resto del proyecto sigue funcionando (sin ese algoritmo);
si se agrega una carpeta nueva, aparece sola.
"""
from __future__ import annotations

import importlib
import pkgutil
from dataclasses import dataclass, field
from typing import Any, Callable, Dict

from control.controller import Controller
from optimization.strategy import LearningStrategy


@dataclass
class StrategyBundle:
    """Lo que entrega un plugin: el optimizador y cómo convertir sus soluciones en controladores."""

    strategy: LearningStrategy
    controller_factory: Callable[[Any, Any], Controller]   # (solución, escenario) -> controlador


@dataclass(frozen=True)
class StrategyPlugin:
    name: str                                  # identificador usado en la configuración
    label: str                                 # nombre para mostrar
    build: Callable[[dict], StrategyBundle]    # recibe la configuración completa
    short_label: str = ""                      # nombre breve para botones
    description: str = ""                      # una línea que explica qué aprende
    stat_labels: Dict[str, str] = field(default_factory=dict)   # nombre visible de sus estadísticas

    def __post_init__(self) -> None:
        if not self.short_label:
            object.__setattr__(self, "short_label", self.label)


def for_any_scenario(factory: Callable[[Any], Controller]) -> Callable[[Any, Any], Controller]:
    """Adapta una fábrica cuyas soluciones no dependen del escenario (p. ej. pesos de una red)."""
    return lambda solution, scenario: factory(solution)


def discover_plugins() -> Dict[str, StrategyPlugin]:
    import optimization

    plugins: Dict[str, StrategyPlugin] = {}
    for info in pkgutil.iter_modules(optimization.__path__):
        if not info.ispkg:
            continue
        module = importlib.import_module(f"optimization.{info.name}")
        plugin = getattr(module, "PLUGIN", None)
        if isinstance(plugin, StrategyPlugin):
            plugins[plugin.name] = plugin
    return plugins
