"""Guardado y carga de mapas en archivos JSON."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List, Optional, Union

from simulation.map_data import MapData


class MapFormatError(ValueError):
    """El archivo no existe o no contiene un mapa válido."""


def safe_name(name: str) -> str:
    """Nombre de archivo sin separadores ni espacios."""
    return re.sub(r"[^\w\-]+", "_", name).strip("_") or "mapa"


def save_map(map_data: MapData, path: Union[str, Path]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(map_data.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def load_map(path: Union[str, Path]) -> MapData:
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise MapFormatError(f"No existe el mapa {path.name}") from error
    except (OSError, json.JSONDecodeError) as error:
        raise MapFormatError(f"No se pudo leer {path.name}: {error}") from error
    if not isinstance(data, dict):
        raise MapFormatError(f"{path.name} no contiene un mapa")
    try:
        return MapData.from_dict(data)
    except (TypeError, ValueError, KeyError, IndexError) as error:
        raise MapFormatError(f"{path.name} tiene un formato de mapa inválido: {error}") from error


class MapManager:
    """Administra los mapas de un directorio (por defecto ``maps/``)."""

    def __init__(self, directory: Union[str, Path]) -> None:
        self.directory = Path(directory)

    def path_for(self, name: str) -> Path:
        return self.directory / f"{safe_name(name)}.json"

    def save(self, map_data: MapData, name: Optional[str] = None) -> Path:
        map_data.name = safe_name(name if name is not None else map_data.name)
        return save_map(map_data, self.path_for(map_data.name))

    def load(self, name: str) -> MapData:
        return load_map(self.path_for(name))

    def list_maps(self) -> List[str]:
        if not self.directory.is_dir():
            return []
        return sorted(p.stem for p in self.directory.glob("*.json"))
