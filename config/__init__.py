"""Carga de la configuración externa (JSON).

``default.json`` contiene todos los parámetros ajustables. Un archivo del
usuario solo necesita nombrar las claves que quiere cambiar. El resultado es un
diccionario que se reparte por secciones en el punto de ensamblado
(``bootstrap.py``); ningún módulo lee configuración global.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Optional, Union

DEFAULT_PATH = Path(__file__).with_name("default.json")


def deep_merge(base: dict, extra: dict) -> dict:
    """Devuelve ``base`` con las claves de ``extra`` superpuestas (sin mutar ninguno)."""
    merged = copy.deepcopy(base)
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def load_config(path: Optional[Union[str, Path]] = None, overrides: Optional[dict] = None) -> dict:
    config = json.loads(DEFAULT_PATH.read_text(encoding="utf-8"))
    if path is not None:
        config = deep_merge(config, json.loads(Path(path).read_text(encoding="utf-8")))
    if overrides:
        config = deep_merge(config, overrides)
    return config
