"""Modo 1: editor visual de mapas. Traduce mouse y teclado a operaciones de ``MapEditor``."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

import pygame

from control.controller import FREE_NAVIGATION, ROUTE_FOLLOWING
from editor.map_editor import MapEditor
from editor.map_generator import MapGenerator
from editor.map_manager import MapFormatError, MapManager
from rendering.renderer import SELECTED, Viewport, WorldRenderer
from ui.widgets import GOOD, MUTED, WARN, Fonts, Panel, TextInput

PANEL_WIDTH = 330
TOOLS = [("route", "1 Camino"), ("erase", "2 Borrar"), ("static", "3 Obstáculo X"),
         ("dynamic", "4 Móvil *"), ("start", "5 Inicio S"), ("goal", "6 Destino G")]
KINDS = [("horizontal", "Horizontal"), ("vertical", "Vertical"), ("circular", "Circular")]
TOOL_KEYS = {getattr(pygame, f"K_{i + 1}"): tool for i, (tool, _) in enumerate(TOOLS)}
HINTS = {
    "route": "Arrastra para dibujar el camino en orden.",
    "erase": "Clic o arrastre para borrar lo que haya en la celda.",
    "static": "Clic o arrastre para poner obstáculos fijos.",
    "dynamic": "Arrastra: en lineales marca los dos extremos; en circular, centro y radio. "
               "Clic sobre uno existente para editarlo.",
    "start": "Clic para ubicar el vehículo; arrastra para orientarlo.",
    "goal": "Clic para ubicar el destino.",
}


class EditorView:
    def __init__(self, config: dict, fonts: Fonts, renderer: WorldRenderer, manager: MapManager,
                 generator: MapGenerator) -> None:
        grid = config["map"]
        self.fonts = fonts
        self.renderer = renderer
        self.manager = manager
        self.generator = generator
        self.editor = MapEditor(cols=grid["cols"], rows=grid["rows"], cell_size=grid["cell_size"])
        self.tool = "route"
        self.dynamic_kind = "horizontal"
        self.selected_dynamic: Optional[int] = None
        self.name_input = TextInput("mi_mapa")
        self.show_maps = False
        self.message = "Dibuja un camino, ubica S y G, y pasa a Simulación (F2)."
        self.panel: Optional[Panel] = None
        self._dragging = False
        self._drag_origin = None
        self._drag_cell = None
        self.layout(pygame.Rect(0, 0, 800, 600))

    # --- geometría de la vista -----------------------------------------------
    def layout(self, area: pygame.Rect) -> None:
        self.canvas = pygame.Rect(area.x, area.y, max(50, area.width - PANEL_WIDTH), area.height)
        self.panel_rect = pygame.Rect(self.canvas.right, area.y, area.right - self.canvas.right, area.height)

    def viewport(self) -> Viewport:
        return Viewport(self.canvas, self.editor.map.width, self.editor.map.height, padding=14)

    def cell_to_screen(self, cell):
        return self.viewport().to_screen(*self.editor.map.cell_center(cell))

    def _cell_at(self, pos):
        return self.editor.map.cell_at(*self.viewport().to_world(*pos))

    # --- acciones --------------------------------------------------------------
    def select_tool(self, tool: str) -> None:
        self.tool = tool
        self.message = HINTS[tool]

    def select_dynamic_kind(self, kind: str) -> None:
        self.dynamic_kind = kind

    def save_map(self, name: Optional[str] = None) -> Optional[Path]:
        try:
            path = self.manager.save(self.editor.map, name or self.name_input.text)
        except OSError as error:
            self.message = f"No se pudo guardar: {error}"
            return None
        self.name_input.text = self.editor.map.name
        self.message = f"Guardado en {path.name}"
        return path

    def load_map(self, name: str) -> None:
        try:
            self.editor.set_map(self.manager.load(name))
        except MapFormatError as error:
            self.message = str(error)
            return
        self.selected_dynamic = None
        self.show_maps = False
        self.name_input.text = self.editor.map.name
        self.message = f"Mapa '{name}' cargado"

    def random_map(self) -> None:
        seed = int(time.time() * 1000) % 1_000_000
        self.editor.set_map(self.generator.generate(seed))
        self.selected_dynamic = None
        self.name_input.text = self.editor.map.name
        self.message = f"Mapa aleatorio generado con la semilla {seed}"

    def new_map(self) -> None:
        self.editor.new()
        self.selected_dynamic = None
        self.message = "Mapa vacío"

    def _update_selected(self, **changes) -> None:
        if self.selected_dynamic is not None:
            self.editor.update_dynamic(self.selected_dynamic, **changes)

    def _remove_selected(self) -> None:
        if self.selected_dynamic is not None:
            self.editor.remove_dynamic(self.selected_dynamic)
            self.selected_dynamic = None

    # --- eventos -----------------------------------------------------------------
    def handle_event(self, event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.name_input.active = False
            if self.panel is not None and self.panel.click(event.pos):
                return
            if self.canvas.collidepoint(event.pos):
                self._dragging = True
                self._press(self._cell_at(event.pos))
        elif event.type == pygame.MOUSEMOTION and self._dragging:
            self._drag(self._cell_at(event.pos))
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self._dragging:
            self._dragging = False
            self._release()
        elif event.type == pygame.KEYDOWN:
            if self.name_input.active:
                self.name_input.handle_key(event)
            elif event.key in TOOL_KEYS:
                self.select_tool(TOOL_KEYS[event.key])
            elif event.key in (pygame.K_DELETE, pygame.K_BACKSPACE):
                self._remove_selected()

    def _press(self, cell) -> None:
        editor = self.editor
        if not editor.map.in_bounds(cell):
            return
        if self.tool == "route":
            editor.add_route_cell(cell)
        elif self.tool == "erase":
            self._erase(cell)
        elif self.tool == "static":
            editor.add_static(cell)
        elif self.tool == "start":
            editor.set_start(cell)
        elif self.tool == "goal":
            editor.set_goal(cell)
        elif self.tool == "dynamic":
            existing = editor.dynamic_at(cell)
            if existing is not None:
                self.selected_dynamic = existing
            else:
                self._drag_origin = self._drag_cell = cell

    def _drag(self, cell) -> None:
        editor = self.editor
        if not editor.map.in_bounds(cell):
            return
        if self.tool == "route":
            editor.add_route_cell(cell)
        elif self.tool == "erase":
            self._erase(cell)
        elif self.tool == "static":
            editor.add_static(cell)
        elif self.tool == "start":
            editor.point_start_towards(cell)
        elif self.tool == "dynamic" and self._drag_origin is not None:
            self._drag_cell = cell

    def _release(self) -> None:
        if self.tool == "dynamic" and self._drag_origin is not None:
            self.editor.add_dynamic(self.dynamic_kind, self._drag_origin, self._drag_cell)
            self.selected_dynamic = len(self.editor.map.dynamic_obstacles) - 1
        self._drag_origin = self._drag_cell = None

    def _erase(self, cell) -> None:
        count = len(self.editor.map.dynamic_obstacles)
        self.editor.erase(cell)
        if len(self.editor.map.dynamic_obstacles) != count:
            self.selected_dynamic = None

    def update(self, dt: float) -> None:
        """El editor no tiene estado que avance con el tiempo."""

    # --- dibujo --------------------------------------------------------------------
    def draw(self, surface, mouse) -> None:
        m = self.editor.map
        viewport = self.viewport()
        self.renderer.draw_map(surface, viewport, m, cache_key=("editor", self.editor.revision))
        self.renderer.draw_dynamic_specs(surface, viewport, m, self.selected_dynamic)
        if m.start is not None:
            self.renderer.draw_heading(surface, viewport, *m.cell_center(m.start), m.start_heading)
        if self._drag_origin is not None:
            pygame.draw.line(surface, SELECTED, self.cell_to_screen(self._drag_origin),
                             self.cell_to_screen(self._drag_cell))
        self.panel = self._build_panel(surface, mouse)

    def _build_panel(self, surface, mouse) -> Panel:
        m, editor = self.editor.map, self.editor
        panel = Panel(self.fonts, self.panel_rect, mouse)
        panel.begin(surface)
        panel.title("EDITOR DE MAPAS")
        for row in (TOOLS[0:2], TOOLS[2:4], TOOLS[4:6]):
            panel.buttons([(label, lambda t=tool: self.select_tool(t), self.tool == tool) for tool, label in row])
        if self.tool == "dynamic":
            panel.buttons([(label, lambda k=kind: self.select_dynamic_kind(k), self.dynamic_kind == kind)
                           for kind, label in KINDS])
        if self.selected_dynamic is not None and self.selected_dynamic < len(m.dynamic_obstacles):
            self._dynamic_properties(panel, m.dynamic_obstacles[self.selected_dynamic])

        panel.gap()
        panel.text("Navegación", MUTED, 12)
        panel.buttons([
            ("Seguir ruta", lambda: editor.set_navigation_mode(ROUTE_FOLLOWING), m.navigation_mode == ROUTE_FOLLOWING),
            ("Libre", lambda: editor.set_navigation_mode(FREE_NAVIGATION), m.navigation_mode == FREE_NAVIGATION),
        ])
        panel.stepper("Columnas", str(m.cols), lambda: editor.resize(m.cols - 1, m.rows),
                      lambda: editor.resize(m.cols + 1, m.rows))
        panel.stepper("Filas", str(m.rows), lambda: editor.resize(m.cols, m.rows - 1),
                      lambda: editor.resize(m.cols, m.rows + 1))

        panel.gap()
        panel.text_field(self.name_input, "Nombre del mapa (clic para editar)")
        panel.buttons([("Guardar", self.save_map),
                       ("Cargar...", lambda: setattr(self, "show_maps", not self.show_maps), self.show_maps)])
        if self.show_maps:
            names = self.manager.list_maps()
            if not names:
                panel.text("No hay mapas guardados en maps/.", MUTED)
            for name in names[:8]:
                panel.buttons([(name, lambda n=name: self.load_map(n))], height=22)
        panel.buttons([("Nuevo", self.new_map), ("Aleatorio", self.random_map)])
        panel.buttons([("Borrar todo el camino", editor.clear_route)])

        panel.gap()
        problems = m.validate()
        if problems:
            for problem in problems[:3]:
                panel.text("! " + problem, WARN, 12)
        else:
            panel.text("Mapa listo para simular (F2).", GOOD, 12)
        panel.gap(4)
        panel.text(self.message, MUTED, 12)
        return panel

    def _dynamic_properties(self, panel: Panel, spec) -> None:
        cell = self.editor.map.cell_size
        panel.gap(4)
        panel.text(f"Móvil #{self.selected_dynamic + 1}: {spec.kind}", SELECTED)
        panel.stepper("Velocidad", f"{spec.speed:.2f}",
                      lambda: self._update_selected(speed=max(0.0, spec.speed - 0.25)),
                      lambda: self._update_selected(speed=spec.speed + 0.25))
        if spec.kind == "circular":
            panel.stepper("Radio de órbita", f"{spec.orbit_radius:.1f}",
                          lambda: self._update_selected(orbit_radius=max(cell, spec.orbit_radius - 0.5 * cell)),
                          lambda: self._update_selected(orbit_radius=spec.orbit_radius + 0.5 * cell))
        else:
            panel.stepper("Pausa en extremos", f"{spec.pause:.1f} s",
                          lambda: self._update_selected(pause=max(0.0, spec.pause - 0.5)),
                          lambda: self._update_selected(pause=spec.pause + 0.5))
            panel.stepper("Extremo mínimo", f"{spec.range_min:.1f}",
                          lambda: self._update_selected(range_min=spec.range_min - cell),
                          lambda: self._update_selected(range_min=min(spec.range_min + cell, spec.range_max)))
            panel.stepper("Extremo máximo", f"{spec.range_max:.1f}",
                          lambda: self._update_selected(range_max=max(spec.range_max - cell, spec.range_min)),
                          lambda: self._update_selected(range_max=spec.range_max + cell))
        sense = "+" if spec.direction > 0 else "-"
        panel.buttons([(f"Sentido: {sense}", lambda: self._update_selected(direction=-spec.direction)),
                       ("Eliminar", self._remove_selected)])
