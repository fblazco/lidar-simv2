"""Representación ASCII de un mapa. Funciones puras, sin Pygame.

Los caracteres se DERIVAN de los datos del mapa para mostrarlo; la navegación
nunca los interpreta.
"""
from __future__ import annotations

from typing import Dict, List

from simulation.map_data import Cell, MapData

VERTICAL, HORIZONTAL, DIAGONAL, BACK_DIAGONAL = "|", "-", "/", "\\"
STATIC, DYNAMIC, START, GOAL, EMPTY = "X", "*", "S", "G", "."
VEHICLE_HEAD, VEHICLE_BODY = "o", "| |"


def _sign(value: int) -> int:
    return (value > 0) - (value < 0)


def route_glyphs(route: List[Cell]) -> Dict[Cell, str]:
    """Carácter de cada celda del camino según el sentido entre su waypoint anterior y el siguiente."""
    glyphs: Dict[Cell, str] = {}
    for i, cell in enumerate(route):
        previous = route[i - 1] if i > 0 else cell
        following = route[i + 1] if i + 1 < len(route) else cell
        dx, dy = _sign(following[0] - previous[0]), _sign(following[1] - previous[1])
        if dy == 0:
            glyphs[cell] = HORIZONTAL
        elif dx == 0:
            glyphs[cell] = VERTICAL
        else:  # Y crece hacia abajo: bajar a la derecha se ve como "\"
            glyphs[cell] = BACK_DIAGONAL if dx * dy > 0 else DIAGONAL
    return glyphs


def ascii_grid(map_data: MapData, empty: str = EMPTY) -> List[str]:
    """El mapa en su estado inicial como filas de texto monoespaciado."""
    cells = dict(route_glyphs(map_data.route))
    for spec in map_data.dynamic_obstacles:
        cells[map_data.cell_at(spec.x, spec.y)] = DYNAMIC
    for cell in map_data.static_obstacles:
        cells[cell] = STATIC
    if map_data.goal is not None:
        cells[map_data.goal] = GOAL
    if map_data.start is not None:
        cells[map_data.start] = START
    return ["".join(cells.get((col, row), empty) for col in range(map_data.cols)) for row in range(map_data.rows)]
