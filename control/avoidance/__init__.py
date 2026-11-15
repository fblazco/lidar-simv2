"""Algoritmos de evasión de obstáculos, descubiertos como plugins.

Cada módulo de este paquete que exponga ``PLUGIN`` es una opción de evasión.
Agregar otro algoritmo (DWA, VFH…) es agregar un archivo aquí.
"""
from __future__ import annotations

import importlib
import pkgutil
from typing import Dict

from control.avoidance.base import AvoidancePlugin

DEFAULT = "learned"


def discover_avoidance() -> Dict[str, AvoidancePlugin]:
    """Opciones disponibles: primero la evasión propia del algoritmo y luego las demás por nombre."""
    import control.avoidance as package

    found = {}
    for info in pkgutil.iter_modules(package.__path__):
        plugin = getattr(importlib.import_module(f"control.avoidance.{info.name}"), "PLUGIN", None)
        if isinstance(plugin, AvoidancePlugin):
            found[plugin.name] = plugin
    return {name: found[name] for name in sorted(found, key=lambda n: (n != DEFAULT, n))}
