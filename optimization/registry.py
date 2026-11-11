"""Descubrimiento de plugins de optimización.

Cada subpaquete de ``optimization/`` que exponga un atributo ``PLUGIN`` es un
algoritmo disponible. Nada fuera de ese subpaquete lo importa por nombre: si se
borra la carpeta, el resto del proyecto sigue funcionando (sin ese algoritmo);
si se agrega una carpeta nueva, aparece sola.
"""
from __future__ import annotations

import importlib
import pkgutil
from dataclasses import dataclass
from typing import Any, Callable, Dict

from control.controller import Controller
from optimization.strategy import LearningStrategy


@dataclass
class StrategyBundle:
    """Lo que entrega un plugin: el optimizador y cómo convertir sus soluciones en controladores."""

    strategy: LearningStrategy
    controller_factory: Callable[[Any], Controller]


@dataclass(frozen=True)
class StrategyPlugin:
    name: str                                  # identificador usado en la configuración
    label: str                                 # nombre para mostrar
    build: Callable[[dict], StrategyBundle]    # recibe la configuración completa


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
