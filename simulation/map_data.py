"""Descripción serializable de un escenario (lo que se guarda en JSON).

Las celdas son pares (columna, fila). El mundo continuo mide
``cols * cell_size`` por ``rows * cell_size`` con el eje Y hacia abajo. La ruta
es una lista ORDENADA de celdas: la navegación nunca interpreta caracteres ASCII.
"""
from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass, field, fields
from typing import List, Optional, Tuple

from control.controller import FREE_NAVIGATION, NAVIGATION_MODES, ROUTE_FOLLOWING

Cell = Tuple[int, int]
FORMAT_VERSION = 1
OBSTACLE_KINDS = ("horizontal", "vertical", "circular")


def _cell(value) -> Cell:
    return (int(value[0]), int(value[1]))


@dataclass
class DynamicObstacleSpec:
    """Obstáculo móvil. Posiciones en unidades del mundo (no en celdas)."""

    kind: str = "horizontal"   # horizontal | vertical | circular
    x: float = 0.0             # posición inicial
    y: float = 0.0
    speed: float = 1.5         # unidades/s (tangencial en el movimiento circular)
    radius: float = 0.4        # tamaño del cuerpo
    direction: int = 1         # sentido inicial: +1 hacia range_max / horario en pantalla
    pause: float = 0.0         # segundos detenido en cada extremo (lineales)
    range_min: float = 0.0     # extremos sobre el eje de movimiento (lineales)
    range_max: float = 0.0
    center_x: float = 0.0      # centro y radio de la órbita (circular)
    center_y: float = 0.0
    orbit_radius: float = 0.0

    def __post_init__(self) -> None:
        if self.kind not in OBSTACLE_KINDS:
            raise ValueError(f"Tipo de obstáculo dinámico desconocido: {self.kind!r}")
        self.direction = 1 if self.direction >= 0 else -1
        if self.range_max < self.range_min:
            self.range_min, self.range_max = self.range_max, self.range_min

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "DynamicObstacleSpec":
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class MapData:
    name: str = "sin_titulo"
    cols: int = 32
    rows: int = 20
    cell_size: float = 1.0
    navigation_mode: str = ROUTE_FOLLOWING
    route: List[Cell] = field(default_factory=list)
    start: Optional[Cell] = None
    start_heading: float = 0.0          # radianes; 0 apunta a +x
    goal: Optional[Cell] = None
    static_obstacles: List[Cell] = field(default_factory=list)
    dynamic_obstacles: List[DynamicObstacleSpec] = field(default_factory=list)
    seed: Optional[int] = None          # semilla del generador, si el mapa es aleatorio

    def __post_init__(self) -> None:
        self.route = [_cell(c) for c in self.route]
        self.static_obstacles = [_cell(c) for c in self.static_obstacles]
        self.start = _cell(self.start) if self.start is not None else None
        self.goal = _cell(self.goal) if self.goal is not None else None
        self.dynamic_obstacles = [
            d if isinstance(d, DynamicObstacleSpec) else DynamicObstacleSpec.from_dict(d)
            for d in self.dynamic_obstacles
        ]

    # --- geometría -------------------------------------------------------
    @property
    def width(self) -> float:
        return self.cols * self.cell_size

    @property
    def height(self) -> float:
        return self.rows * self.cell_size

    def cell_center(self, cell: Cell) -> Tuple[float, float]:
        return ((cell[0] + 0.5) * self.cell_size, (cell[1] + 0.5) * self.cell_size)

    def cell_at(self, x: float, y: float) -> Cell:
        return (int(x // self.cell_size), int(y // self.cell_size))

    def in_bounds(self, cell: Cell) -> bool:
        return 0 <= cell[0] < self.cols and 0 <= cell[1] < self.rows

    def path_cells(self) -> List[Cell]:
        """Celdas ordenadas que el vehículo debe recorrer: inicio, ruta y destino."""
        middle = self.route if self.navigation_mode == ROUTE_FOLLOWING else []
        cells: List[Cell] = []
        for cell in [self.start, *middle, self.goal]:
            if cell is not None and (not cells or cells[-1] != cell):
                cells.append(cell)
        return cells

    # --- persistencia ----------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "format_version": FORMAT_VERSION,
            "name": self.name,
            "cols": self.cols,
            "rows": self.rows,
            "cell_size": self.cell_size,
            "navigation_mode": self.navigation_mode,
            "route": [list(c) for c in self.route],
            "start": list(self.start) if self.start is not None else None,
            "start_heading": self.start_heading,
            "goal": list(self.goal) if self.goal is not None else None,
            "static_obstacles": [list(c) for c in self.static_obstacles],
            "dynamic_obstacles": [d.to_dict() for d in self.dynamic_obstacles],
            "seed": self.seed,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MapData":
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})

    def copy(self) -> "MapData":
        return MapData.from_dict(self.to_dict())

    # --- validación ------------------------------------------------------
    def validate(self) -> List[str]:
        """Devuelve los problemas que impiden simular el mapa (vacío si es válido)."""
        problems: List[str] = []
        if self.cols < 2 or self.rows < 2:
            problems.append("La grilla debe tener al menos 2x2 celdas")
        if self.navigation_mode not in NAVIGATION_MODES:
            problems.append(f"Modo de navegación desconocido: {self.navigation_mode}")
        if self.start is None:
            problems.append("Falta el inicio (S)")
        if self.goal is None:
            problems.append("Falta el destino (G)")
        blocked = set(self.static_obstacles)
        for label, cell in (("inicio", self.start), ("destino", self.goal)):
            if cell is None:
                continue
            if not self.in_bounds(cell):
                problems.append(f"El {label} está fuera de la grilla")
            elif cell in blocked:
                problems.append(f"El {label} está sobre un obstáculo estático")
        if any(not self.in_bounds(c) for c in [*self.route, *self.static_obstacles]):
            problems.append("Hay caminos u obstáculos fuera de la grilla")
        if self.navigation_mode == ROUTE_FOLLOWING and len(self.route) < 2:
            problems.append("El modo de seguimiento de ruta necesita un camino de al menos 2 celdas")
        if not problems:
            if self.start == self.goal:
                problems.append("El inicio y el destino coinciden")
            elif not self._goal_reachable(blocked):
                problems.append("El destino no es alcanzable: los obstáculos estáticos lo bloquean")
        return problems

    def _goal_reachable(self, blocked: set) -> bool:
        """Búsqueda en anchura sobre celdas libres, sin cortar esquinas en diagonal."""
        frontier = deque([self.start])
        seen = {self.start}
        while frontier:
            col, row = frontier.popleft()
            if (col, row) == self.goal:
                return True
            for dc in (-1, 0, 1):
                for dr in (-1, 0, 1):
                    nxt = (col + dc, row + dr)
                    if nxt in seen or nxt in blocked or not self.in_bounds(nxt):
                        continue
                    if dc and dr and ((col + dc, row) in blocked or (col, row + dr) in blocked):
                        continue
                    seen.add(nxt)
                    frontier.append(nxt)
        return False
