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
from rendering.renderer import Viewport, WorldRenderer
from ui.widgets import TextInput, Toolkit, Ui

# (herramienta, etiqueta, símbolo que coloca en el mapa; vacío = ícono)
TOOLS = [("route", "Camino", "/"), ("erase", "Borrar", ""), ("static", "Obstáculo", "X"),
         ("dynamic", "Móvil", "*"), ("start", "Inicio", "S"), ("goal", "Destino", "G")]
TOOL_LABELS = {tool: label for tool, label, _ in TOOLS}
KINDS = [("horizontal", "Horizontal"), ("vertical", "Vertical"), ("circular", "Circular")]
KIND_LABELS = dict(KINDS)
DIRECTIONS = {"horizontal": ("Derecha", "Izquierda"), "vertical": ("Abajo", "Arriba"),
              "circular": ("Horario", "Antihorario")}          # sentido +1 y -1 de cada trayectoria
MODES = [(ROUTE_FOLLOWING, "Seguir la ruta"), (FREE_NAVIGATION, "Navegación libre")]
TOOL_KEYS = {getattr(pygame, f"K_{i + 1}"): tool for i, (tool, _, _) in enumerate(TOOLS)}
HINTS = {
    "route": "Arrastra para dibujar el camino en orden.",
    "erase": "Clic o arrastre para borrar lo que haya en la celda.",
    "static": "Clic o arrastre para poner obstáculos fijos.",
    "dynamic": "Arrastra: en lineales marca los dos extremos; en circular, centro y radio. "
               "Clic sobre uno existente para editarlo.",
    "start": "Clic para ubicar el vehículo; arrastra para orientarlo.",
    "goal": "Clic para ubicar el destino.",
}
HEADER, FOOTER = 50, 44        # franjas de la tarjeta del mapa
TOOL_SIZE, TOOL_GAP = 64, 6
LISTED_MAPS = 9


class EditorView:
    def __init__(self, config: dict, kit: Toolkit, renderer: WorldRenderer, manager: MapManager,
                 generator: MapGenerator) -> None:
        grid = config["map"]
        self.kit = kit
        self.fonts = kit.fonts
        self.renderer = renderer
        self.manager = manager
        self.generator = generator
        self.editor = MapEditor(cols=grid["cols"], rows=grid["rows"], cell_size=grid["cell_size"])
        self.tool = "route"
        self.dynamic_kind = "horizontal"
        self.selected_dynamic: Optional[int] = None
        self.name_input = TextInput("mi_mapa")
        self.show_maps = False
        self.message = "Dibuja un camino, ubica S y G, y pasa a Conducir o a Entrenar."
        self.ui: Optional[Ui] = None
        self._dragging = False
        self._drag_origin = None
        self._drag_cell = None
        self.layout(pygame.Rect(0, 0, 800, 600))

    # --- geometría de la vista -----------------------------------------------
    def layout(self, area: pygame.Rect) -> None:
        self.area = pygame.Rect(area)
        wide = area.width >= 1150
        pad = 32 if wide else 20
        top, height = area.y + 18, max(120, area.height - 36)
        tools = len(TOOLS) * TOOL_SIZE + (len(TOOLS) - 1) * TOOL_GAP + 16
        self.rail = pygame.Rect(area.x + pad, top, 84, min(height, tools))
        panel_width = 300 if wide else 270
        self.panel_rect = pygame.Rect(area.right - pad - panel_width, top, panel_width, height)
        left = self.rail.right + 16
        self._slot = pygame.Rect(left, top, max(120, self.panel_rect.x - 16 - left), height)
        self._arrange()

    def _arrange(self) -> None:
        """La tarjeta del mapa se ajusta a la proporción del mapa, sin pasarse del espacio disponible."""
        m, slot = self.editor.map, self._slot
        ideal = int((slot.width - 2) * m.height / m.width) + HEADER + FOOTER + 2
        self.card = pygame.Rect(slot.x, slot.y, slot.width, max(HEADER + FOOTER + 60, min(slot.height, ideal)))
        self.canvas = pygame.Rect(self.card.x + 1, self.card.y + HEADER, self.card.width - 2,
                                  self.card.height - HEADER - FOOTER)

    def viewport(self) -> Viewport:
        self._arrange()
        return Viewport(self.canvas, self.editor.map.width, self.editor.map.height, padding=0)

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

    def toggle_maps(self) -> None:
        self.show_maps = not self.show_maps

    def _update_selected(self, **changes) -> None:
        if self.selected_dynamic is not None:
            self.editor.update_dynamic(self.selected_dynamic, **changes)

    def _remove_selected(self) -> None:
        if self.selected_dynamic is not None:
            self.editor.remove_dynamic(self.selected_dynamic)
            self.selected_dynamic = None

    def _edit_name(self) -> None:
        self.name_input.active = True

    # --- eventos -----------------------------------------------------------------
    def handle_event(self, event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.name_input.active = False
            if self.ui is not None and self.ui.click(event.pos):
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
        ui = self.kit.frame(surface, mouse)
        m = self.editor.map
        viewport = self.viewport()
        ui.card(self.card)
        surface.fill(ui.theme.world.background, self.canvas)
        self.renderer.draw_map(surface, viewport, m, cache_key=("editor", self.editor.revision))
        self.renderer.draw_dynamic_specs(surface, viewport, m, self.selected_dynamic)
        if m.start is not None:
            self.renderer.draw_heading(surface, viewport, *m.cell_center(m.start), m.start_heading)
        if self._drag_origin is not None:
            pygame.draw.line(surface, ui.theme.world.selected, self.cell_to_screen(self._drag_origin),
                             self.cell_to_screen(self._drag_cell), 2)
        ui.divider(self.card.x + 1, self.canvas.y - 1, self.card.width - 2)
        ui.divider(self.card.x + 1, self.canvas.bottom, self.card.width - 2)
        self._draw_header(ui, m)
        self._draw_footer(ui, m)
        self._draw_tools(ui)
        self._draw_panel(ui, m)
        self.ui = ui

    def _draw_header(self, ui: Ui, m) -> None:
        theme, card = ui.theme, self.card
        middle = card.y + HEADER // 2
        segment = min(124, max(70, (card.width - 320) // 2))
        modes = pygame.Rect(card.right - 14 - 2 * segment - 6, middle - 17, 2 * segment + 6, 34)
        ui.segmented(modes, MODES, m.navigation_mode, self.editor.set_navigation_mode)
        # nombre del mapa: se edita en el lugar
        field = self.name_input
        text = field.text + ("_" if field.active else "")
        width = min(max(110, self.fonts.width(text, 14, "mono") + 46), max(110, modes.x - card.x - 28))
        name = pygame.Rect(card.x + 14, middle - 17, width, 34)
        self.kit.shapes.rounded(ui.surface, name, 10, theme.soft if field.active else theme.background,
                                theme.outline if field.active else theme.control_line)
        ui.text(ui.fit(text, name.width - 40, 14, "mono"), (name.x + 12, middle), 14, face="mono", anchor="midleft")
        ui.icon("edit", (name.right - 16, middle), 14, theme.muted)
        ui.hit(name, self._edit_name)
        size = f"{m.cols} × {m.rows} celdas"
        if name.right + 12 + self.fonts.width(size, 12) < modes.x - 8:
            ui.text(size, (name.right + 12, middle), 12, theme.muted, anchor="midleft")

    def _draw_footer(self, ui: Ui, m) -> None:
        theme, card = ui.theme, self.card
        middle = self.canvas.bottom + FOOTER // 2
        problems = m.validate()
        mark = pygame.Rect(card.x + 14, middle - 9, 18, 18)
        if problems:
            self.kit.shapes.rounded(ui.surface, mark, 9, None, theme.text, 2)
            ui.text("!", mark.center, 12, face="bold", anchor="center")
            status = "Falta: " + problems[0]
        else:
            self.kit.shapes.rounded(ui.surface, mark, 9, theme.primary)
            ui.icon("check", mark.center, 12, theme.on_primary)
            status = "Mapa listo para simular"
        room = card.width - 28 - 26
        end = ui.text(ui.fit(status, int(room * 0.55), 14, "bold"), (mark.right + 8, middle), 14, face="bold",
                      anchor="midleft").right
        remaining = card.right - 14 - end - 16
        if remaining > 80:
            ui.text(ui.fit(self.message, remaining, 12), (card.right - 14, middle), 12, theme.muted, anchor="midright")

    def _draw_tools(self, ui: Ui) -> None:
        theme, rail = ui.theme, self.rail
        ui.card(rail)
        step = min(TOOL_SIZE + TOOL_GAP, (rail.height - 16 + TOOL_GAP) // len(TOOLS))
        for index, (tool, label, glyph) in enumerate(TOOLS):
            cell = pygame.Rect(rail.x + 9, rail.y + 8 + index * step, rail.width - 18, step - TOOL_GAP)
            active = tool == self.tool
            color = theme.on_primary if active else theme.text
            if active:
                self.kit.shapes.rounded(ui.surface, cell, 14, theme.primary)
            elif ui.hover(cell):
                self.kit.shapes.rounded(ui.surface, cell, 14, theme.soft)
            if glyph:
                ui.text(glyph, (cell.centerx, cell.centery - 8), 22, color, "mono", "center")
            else:
                ui.icon("eraser", (cell.centerx, cell.centery - 8), 24, color)
            ui.text(label, (cell.centerx, cell.bottom - 13), 11, color, anchor="center")
            ui.hit(cell, lambda t=tool: self.select_tool(t))

    def _row(self, ui: Ui, y: int, row: int, label: str, value: str, on_minus, on_plus) -> int:
        panel = self.panel_rect
        ui.text(label, (panel.x + 16, y + row // 2), 14, anchor="midleft")
        ui.stepper(panel.right - 16, y + row // 2, value, on_minus, on_plus, button=min(36, row - 4))
        return y + row

    def _draw_panel(self, ui: Ui, m) -> None:
        theme, panel, editor = ui.theme, self.panel_rect, self.editor
        ui.card(panel)
        x, width = panel.x + 16, panel.width - 32
        row = 40 if panel.height >= 600 else 34
        y = panel.y + 16
        if self.show_maps:
            y = self._draw_map_list(ui, x, y, width, row)
        else:
            selected = (m.dynamic_obstacles[self.selected_dynamic]
                        if self.selected_dynamic is not None and self.selected_dynamic < len(m.dynamic_obstacles)
                        else None)
            if selected is not None:
                y = self._draw_dynamic(ui, selected, x, y, width, row)
            else:
                ui.text("Herramienta", (x, y), 12, theme.muted)
                ui.text(TOOL_LABELS[self.tool], (x, y + 17), 18, face="bold")
                y = ui.paragraph(HINTS[self.tool], x, y + 46, width, 13) + 6
            if self.tool == "dynamic":
                ui.text("Trayectoria de los móviles nuevos", (x, y), 12, theme.muted)
                ui.segmented((x, y + 20, width, 36), KINDS, self.dynamic_kind, self.select_dynamic_kind, size=12)
                y += 68
            ui.divider(x, y, width)
            ui.text("Tamaño del mapa", (x, y + 12), 12, theme.muted)
            y = self._row(ui, y + 30, row, "Columnas", str(m.cols), lambda: editor.resize(m.cols - 1, m.rows),
                          lambda: editor.resize(m.cols + 1, m.rows))
            y = self._row(ui, y, row, "Filas", str(m.rows), lambda: editor.resize(m.cols, m.rows - 1),
                          lambda: editor.resize(m.cols, m.rows + 1)) + 8
        # archivo: siempre al pie de la tarjeta
        height = 38 if row == 40 else 34
        y = max(y + 4, panel.bottom - 16 - 2 * height - 8 - 30)
        ui.divider(x, y, width)
        y += 12
        half = (width - 8) // 2
        ui.button((x, y, half, height), "Guardar", self.save_map, "primary")
        ui.button((x + half + 8, y, half, height), "Cerrar lista" if self.show_maps else "Cargar…", self.toggle_maps)
        ui.button((x, y + height + 8, half, height), "Nuevo", self.new_map)
        ui.button((x + half + 8, y + height + 8, half, height), "Aleatorio", self.random_map)
        if y + 2 * height + 30 <= panel.bottom:
            ui.link("Borrar todo el camino", (panel.centerx, y + 2 * height + 18), editor.clear_route, 12, "midtop")

    def _draw_dynamic(self, ui: Ui, spec, x: int, y: int, width: int, row: int) -> int:
        theme, cell = ui.theme, self.editor.map.cell_size
        ui.text("Obstáculo móvil seleccionado", (x, y), 12, theme.muted)
        ui.text(f"Móvil {self.selected_dynamic + 1} · {KIND_LABELS[spec.kind].lower()}", (x, y + 17), 18, face="bold")
        y += 48
        y = self._row(ui, y, row, "Velocidad", f"{spec.speed:.2f}",
                      lambda: self._update_selected(speed=max(0.0, spec.speed - 0.25)),
                      lambda: self._update_selected(speed=spec.speed + 0.25))
        if spec.kind == "circular":
            y = self._row(ui, y, row, "Radio de órbita", f"{spec.orbit_radius:.1f}",
                          lambda: self._update_selected(orbit_radius=max(cell, spec.orbit_radius - 0.5 * cell)),
                          lambda: self._update_selected(orbit_radius=spec.orbit_radius + 0.5 * cell))
        else:
            y = self._row(ui, y, row, "Pausa en extremos", f"{spec.pause:.1f} s",
                          lambda: self._update_selected(pause=max(0.0, spec.pause - 0.5)),
                          lambda: self._update_selected(pause=spec.pause + 0.5))
            y = self._row(ui, y, row, "Extremo mínimo", f"{spec.range_min:.1f}",
                          lambda: self._update_selected(range_min=spec.range_min - cell),
                          lambda: self._update_selected(range_min=min(spec.range_min + cell, spec.range_max)))
            y = self._row(ui, y, row, "Extremo máximo", f"{spec.range_max:.1f}",
                          lambda: self._update_selected(range_max=max(spec.range_max - cell, spec.range_min)),
                          lambda: self._update_selected(range_max=spec.range_max + cell))
        forward, backward = DIRECTIONS[spec.kind]
        ui.text("Sentido", (x, y + row // 2), 14, anchor="midleft")
        ui.segmented((x + width - 176, y + (row - 32) // 2, 176, 32), [(1, forward), (-1, backward)],
                     1 if spec.direction > 0 else -1, lambda value: self._update_selected(direction=value), size=12)
        y += row + 8
        ui.button((x, y, width, 36), "Eliminar este móvil", self._remove_selected)
        return y + 36 + 14

    def _draw_map_list(self, ui: Ui, x: int, y: int, width: int, row: int) -> int:
        theme = ui.theme
        ui.text("Mapas guardados", (x, y), 18, face="bold")
        y += 34
        names = self.manager.list_maps()
        if not names:
            return ui.paragraph("No hay mapas guardados en maps/.", x, y, width, 13) + 8
        for name in names[:LISTED_MAPS]:
            ui.button((x, y, width, row - 6), ui.fit(name, width - 24, 13, "mono"), lambda n=name: self.load_map(n),
                      "control", radius=10)
            y += row
        if len(names) > LISTED_MAPS:
            ui.text(f"… y {len(names) - LISTED_MAPS} más en maps/", (x, y), 12, theme.muted)
            y += 20
        return y + 4
