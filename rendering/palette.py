"""Paletas del mundo. El renderizador recibe la paleta activa y no la decide."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

Color = Tuple[int, int, int]


@dataclass(frozen=True)
class WorldPalette:
    name: str
    background: Color
    grid: Color
    route: Color
    route_unused: Color      # camino dibujado pero ignorado en modo libre
    static: Color
    block: Color             # celda que ocupa un obstáculo fijo
    dynamic: Color
    trajectory: Color        # recorrido de un obstáculo móvil y su contorno
    selected: Color
    start: Color
    goal: Color
    ray: Color
    ray_hit: Color
    hit_point: Color
    target: Color
    heat: Color              # intensidad por celda que publica una estrategia (p. ej. feromona)
    planned: Color           # ruta planificada por el controlador de un móvil
    trail: Color             # camino ya recorrido por el vehículo
    vehicle: Color
    vehicle_stopped: Color   # chocó o se quedó sin tiempo
    strong: Color            # tres niveles de énfasis para las capas explicativas
    medium: Color
    faint: Color

    def emphasis(self, level: str) -> Color:
        """Color de un nivel de énfasis: 'strong', 'medium' o 'faint'."""
        return {"strong": self.strong, "medium": self.medium}.get(level, self.faint)


DARK = WorldPalette(
    name="dark", background=(12, 13, 15), grid=(48, 51, 56), route=(168, 173, 180), route_unused=(70, 74, 81),
    static=(158, 163, 170), block=(30, 32, 36), dynamic=(240, 242, 245), trajectory=(78, 82, 89),
    selected=(255, 255, 255), start=(170, 175, 182), goal=(255, 255, 255), ray=(33, 35, 39), ray_hit=(74, 79, 86),
    hit_point=(206, 210, 216), target=(100, 105, 112), heat=(255, 255, 255), planned=(255, 255, 255),
    trail=(168, 173, 180), vehicle=(255, 255, 255), vehicle_stopped=(150, 154, 160),
    strong=(255, 255, 255), medium=(168, 173, 180), faint=(100, 105, 112),
)

LIGHT = WorldPalette(
    name="light", background=(245, 246, 248), grid=(196, 200, 206), route=(88, 93, 100), route_unused=(190, 194, 200),
    static=(84, 89, 96), block=(226, 228, 232), dynamic=(16, 18, 21), trajectory=(170, 175, 182),
    selected=(0, 0, 0), start=(100, 105, 112), goal=(0, 0, 0), ray=(229, 231, 235), ray_hit=(180, 185, 192),
    hit_point=(60, 64, 70), target=(150, 155, 162), heat=(0, 0, 0), planned=(0, 0, 0),
    trail=(88, 93, 100), vehicle=(0, 0, 0), vehicle_stopped=(120, 125, 132),
    strong=(0, 0, 0), medium=(88, 93, 100), faint=(150, 155, 162),
)

UBUNTU = WorldPalette(
    name="ubuntu", background=(249, 246, 239), grid=(218, 207, 190),
    route=(94, 39, 80), route_unused=(205, 187, 168), static=(190, 65, 28),
    block=(241, 224, 208), dynamic=(94, 39, 80), trajectory=(184, 139, 153),
    selected=(233, 84, 32), start=(119, 33, 111), goal=(233, 84, 32),
    ray=(233, 222, 207), ray_hit=(207, 141, 108), hit_point=(119, 33, 111),
    target=(207, 120, 64), heat=(233, 84, 32), planned=(119, 33, 111),
    trail=(94, 39, 80), vehicle=(66, 29, 58), vehicle_stopped=(161, 84, 69),
    strong=(94, 39, 80), medium=(190, 65, 28), faint=(174, 151, 132),
)

PALETTES = {palette.name: palette for palette in (LIGHT, DARK, UBUNTU)}
