"""Modelo del editor de mapas: operaciones de edición sin interfaz gráfica.

La vista Pygame (``ui/editor_view.py``) traduce el mouse y el teclado a estas
operaciones. La ruta se guarda como lista ordenada de celdas en el orden en
que se dibujó; los caracteres ASCII solo se derivan de ella para mostrarla.
"""
from __future__ import annotations

import math
from typing import List, Optional

from control.controller import NAVIGATION_MODES
from simulation.map_data import Cell, DynamicObstacleSpec, MapData

DEFAULT_EXTENT_CELLS = 3     # medio recorrido de un obstáculo lineal creado con un clic
DEFAULT_ORBIT_CELLS = 2      # radio de un obstáculo circular creado con un clic


def line_cells(a: Cell, b: Cell) -> List[Cell]:
    """Celdas contiguas (8 vecinos) de una recta entre dos celdas (Bresenham)."""
    (x0, y0), (x1, y1) = a, b
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    error = dx + dy
    cells = [(x0, y0)]
    while (x0, y0) != (x1, y1):
        doubled = 2 * error
        if doubled >= dy:
            error += dy
            x0 += sx
        if doubled <= dx:
            error += dx
            y0 += sy
        cells.append((x0, y0))
    return cells


class MapEditor:
    def __init__(self, map_data: Optional[MapData] = None, cols: int = 32, rows: int = 20,
                 cell_size: float = 1.0) -> None:
        self.map = map_data if map_data is not None else MapData(cols=cols, rows=rows, cell_size=cell_size)
        self.revision = 0   # cambia con cada edición (para invalidar cachés de dibujo)

    def _changed(self) -> None:
        self.revision += 1

    # --- mapa completo -----------------------------------------------------
    def set_map(self, map_data: MapData) -> None:
        self.map = map_data
        self._changed()

    def new(self, cols: Optional[int] = None, rows: Optional[int] = None) -> None:
        current = self.map
        self.set_map(MapData(cols=cols or current.cols, rows=rows or current.rows, cell_size=current.cell_size))

    def set_navigation_mode(self, mode: str) -> None:
        if mode not in NAVIGATION_MODES:
            raise ValueError(f"Modo de navegación desconocido: {mode}")
        self.map.navigation_mode = mode
        self._changed()

    def resize(self, cols: int, rows: int) -> None:
        m = self.map
        m.cols, m.rows = max(2, int(cols)), max(2, int(rows))
        m.route = [c for c in m.route if m.in_bounds(c)]
        m.static_obstacles = [c for c in m.static_obstacles if m.in_bounds(c)]
        m.dynamic_obstacles = [d for d in m.dynamic_obstacles if m.in_bounds(m.cell_at(d.x, d.y))]
        if m.start is not None and not m.in_bounds(m.start):
            m.start = None
        if m.goal is not None and not m.in_bounds(m.goal):
            m.goal = None
        self._changed()

    # --- caminos -------------------------------------------------------------
    def add_route_cell(self, cell: Cell) -> None:
        """Extiende la ruta hasta ``cell`` rellenando los saltos del mouse."""
        m = self.map
        if not m.in_bounds(cell):
            return
        if not m.route:
            m.route.append(cell)
        elif m.route[-1] != cell:
            m.route.extend(line_cells(m.route[-1], cell)[1:])
        else:
            return
        self._changed()

    def clear_route(self) -> None:
        self.map.route = []
        self._changed()

    # --- obstáculos ------------------------------------------------------------
    def add_static(self, cell: Cell) -> None:
        m = self.map
        if not m.in_bounds(cell) or cell in m.static_obstacles or cell in (m.start, m.goal):
            return
        m.static_obstacles.append(cell)
        self._changed()

    def add_dynamic(self, kind: str, origin: Cell, drag_to: Cell, speed: float = 1.5) -> DynamicObstacleSpec:
        """Crea un obstáculo móvil a partir de un arrastre del mouse.

        Lineales: ``origin`` es la posición inicial y un extremo; ``drag_to`` el
        otro extremo. Circular: ``origin`` es el centro y ``drag_to`` la posición
        inicial sobre la órbita. Un clic sin arrastre usa un recorrido por defecto.
        """
        m = self.map
        cs = m.cell_size
        ox, oy = m.cell_center(origin)
        tx, ty = m.cell_center(drag_to)
        spec = DynamicObstacleSpec(kind=kind, x=ox, y=oy, speed=speed, radius=0.4 * cs)
        if kind == "circular":
            spec.center_x, spec.center_y = ox, oy
            spec.orbit_radius = math.hypot(tx - ox, ty - oy) or DEFAULT_ORBIT_CELLS * cs
            spec.x, spec.y = (tx, ty) if drag_to != origin else (ox + spec.orbit_radius, oy)
        else:
            horizontal = kind == "horizontal"
            here, there = (ox, tx) if horizontal else (oy, ty)
            limit = (m.width if horizontal else m.height) - 0.5 * cs
            if here == there:
                extent = DEFAULT_EXTENT_CELLS * cs
                spec.range_min, spec.range_max = max(0.5 * cs, here - extent), min(limit, here + extent)
            else:
                spec.range_min, spec.range_max = min(here, there), max(here, there)
                spec.direction = 1 if there > here else -1
        m.dynamic_obstacles.append(spec)
        self._changed()
        return spec

    def dynamic_at(self, cell: Cell) -> Optional[int]:
        for i, spec in enumerate(self.map.dynamic_obstacles):
            if self.map.cell_at(spec.x, spec.y) == cell:
                return i
        return None

    def update_dynamic(self, index: int, **changes) -> None:
        spec = self.map.dynamic_obstacles[index]
        for key, value in changes.items():
            if not hasattr(spec, key):
                raise AttributeError(f"Propiedad de obstáculo desconocida: {key}")
            setattr(spec, key, value)
        spec.__post_init__()   # normaliza sentido y extremos
        # La posición inicial debe seguir sobre la trayectoria tras el cambio.
        if spec.kind == "circular":
            if spec.orbit_radius > 0.0:
                angle = math.atan2(spec.y - spec.center_y, spec.x - spec.center_x)
                spec.x = spec.center_x + spec.orbit_radius * math.cos(angle)
                spec.y = spec.center_y + spec.orbit_radius * math.sin(angle)
        elif spec.kind == "horizontal":
            spec.x = min(max(spec.x, spec.range_min), spec.range_max)
        else:
            spec.y = min(max(spec.y, spec.range_min), spec.range_max)
        self._changed()

    def remove_dynamic(self, index: int) -> None:
        del self.map.dynamic_obstacles[index]
        self._changed()

    # --- inicio y destino --------------------------------------------------------
    def set_start(self, cell: Cell, heading: Optional[float] = None) -> None:
        m = self.map
        if not m.in_bounds(cell):
            return
        m.start = cell
        if heading is not None:
            m.start_heading = heading
        if cell in m.static_obstacles:
            m.static_obstacles.remove(cell)
        self._changed()

    def point_start_towards(self, cell: Cell) -> None:
        """Orienta el vehículo hacia ``cell`` (arrastre con la herramienta de inicio)."""
        m = self.map
        if m.start is None or cell == m.start:
            return
        m.start_heading = math.atan2(cell[1] - m.start[1], cell[0] - m.start[0])
        self._changed()

    def set_goal(self, cell: Cell) -> None:
        m = self.map
        if not m.in_bounds(cell):
            return
        m.goal = cell
        if cell in m.static_obstacles:
            m.static_obstacles.remove(cell)
        self._changed()

    # --- borrado -------------------------------------------------------------------
    def erase(self, cell: Cell) -> bool:
        """Borra lo que haya en la celda. Devuelve si cambió algo."""
        m = self.map
        before = (len(m.route), len(m.static_obstacles), len(m.dynamic_obstacles), m.start, m.goal)
        m.route = [c for c in m.route if c != cell]
        m.static_obstacles = [c for c in m.static_obstacles if c != cell]
        m.dynamic_obstacles = [d for d in m.dynamic_obstacles if m.cell_at(d.x, d.y) != cell]
        if m.start == cell:
            m.start = None
        if m.goal == cell:
            m.goal = None
        changed = before != (len(m.route), len(m.static_obstacles), len(m.dynamic_obstacles), m.start, m.goal)
        if changed:
            self._changed()
        return changed
