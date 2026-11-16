"""Dibujo del mundo en Pygame con caracteres ASCII.

Solo lee el estado del simulador; nunca lo modifica. Cada vista se dibuja en
un ``Viewport`` propio, lo que permite mostrar varios mundos en una ventana.
Los colores salen de una ``WorldPalette`` que se puede cambiar en cualquier momento.
"""
from __future__ import annotations

import math
from typing import Optional, Sequence

import pygame

from control.controller import ROUTE_FOLLOWING
from rendering import ascii_renderer as symbols
from rendering.palette import DARK, WorldPalette
from simulation.map_data import MapData
from simulation.vehicle import Status

MOVING = (Status.ACTIVE, Status.REACHED_GOAL)


class Viewport:
    """Transformación mundo <-> pantalla dentro de un rectángulo, conservando la proporción."""

    def __init__(self, rect: pygame.Rect, world_width: float, world_height: float, padding: int = 6) -> None:
        inner = rect.inflate(-2 * padding, -2 * padding)
        self.scale = max(1e-6, min(inner.width / world_width, inner.height / world_height))
        size = (max(1, int(world_width * self.scale)), max(1, int(world_height * self.scale)))
        self.rect = pygame.Rect((0, 0), size)
        self.rect.center = inner.center
        self.ox, self.oy = self.rect.topleft

    def to_screen(self, x: float, y: float):
        return (int(self.ox + x * self.scale), int(self.oy + y * self.scale))

    def to_world(self, px: float, py: float):
        return ((px - self.ox) / self.scale, (py - self.oy) / self.scale)


class WorldRenderer:
    def __init__(self, fonts, palette: WorldPalette = DARK) -> None:
        self.fonts = fonts
        self.palette = palette
        self._layers = {}     # capas estáticas del mapa ya dibujadas
        self._sprites = {}    # vehículo rotado por tamaño, color y ángulo

    def set_palette(self, palette: WorldPalette) -> None:
        """Cambia los colores; lo ya dibujado en caché deja de servir."""
        if palette is not self.palette:
            self.palette = palette
            self._layers.clear()
            self._sprites.clear()

    def _remember(self, key, layer) -> None:
        if key is not None:
            if len(self._layers) > 48:
                self._layers.clear()
            self._layers[key] = layer

    # --- mapa (capa estática) ------------------------------------------------
    def draw_map(self, surface, viewport: Viewport, map_data: MapData, cache_key=None) -> None:
        key = (cache_key, viewport.rect.size) if cache_key is not None else None
        layer = self._layers.get(key) if key is not None else None
        if layer is None:
            layer = self._render_map(viewport, map_data)
            self._remember(key, layer)
        surface.blit(layer, viewport.rect.topleft)

    def _render_map(self, viewport: Viewport, m: MapData) -> pygame.Surface:
        colors = self.palette
        layer = pygame.Surface(viewport.rect.size)
        layer.fill(colors.background)
        cell = viewport.scale * m.cell_size
        size = max(6, int(cell * 0.95))

        def put(char, where, color):
            image = self.fonts.render(char, size, color)
            layer.blit(image, image.get_rect(center=((where[0] + 0.5) * cell, (where[1] + 0.5) * cell)))

        if cell >= 6:
            dot = 2 if cell >= 22 else 1
            for col in range(m.cols):
                for row in range(m.rows):
                    layer.fill(colors.grid, (int((col + 0.5) * cell), int((row + 0.5) * cell), dot, dot))
        route_color = colors.route if m.navigation_mode == ROUTE_FOLLOWING else colors.route_unused
        for where, char in symbols.route_glyphs(m.route).items():
            if where not in (m.start, m.goal):       # el inicio y el destino se dibujan encima
                put(char, where, route_color)
        inset = cell * 0.07
        for where in m.static_obstacles:
            block = pygame.Rect(where[0] * cell + inset, where[1] * cell + inset, cell - 2 * inset, cell - 2 * inset)
            pygame.draw.rect(layer, colors.block, block, border_radius=max(1, int(cell * 0.16)))
            put(symbols.STATIC, where, colors.static)
        if m.goal is not None:
            center = ((m.goal[0] + 0.5) * cell, (m.goal[1] + 0.5) * cell)
            pygame.draw.circle(layer, colors.medium, center, cell * 0.62, 1)
            put(symbols.GOAL, m.goal, colors.goal)
        if m.start is not None:
            put(symbols.START, m.start, colors.start)
        return layer

    # --- obstáculos dinámicos --------------------------------------------------
    def _star(self, surface, viewport: Viewport, x, y, radius, color, outline) -> None:
        center = viewport.to_screen(x, y)
        pygame.draw.circle(surface, outline, center, max(2, int(radius * viewport.scale)), 1)
        image = self.fonts.render(symbols.DYNAMIC, max(8, int(viewport.scale * 1.3)), color)
        surface.blit(image, image.get_rect(center=center))

    def draw_obstacles(self, surface, viewport: Viewport, world) -> None:
        """Obstáculos móviles en su posición actual."""
        for x, y, radius in world.circles:
            self._star(surface, viewport, x, y, radius, self.palette.dynamic, self.palette.trajectory)

    def draw_dynamic_specs(self, surface, viewport: Viewport, m: MapData, selected: Optional[int] = None) -> None:
        """Vista de edición: posición inicial y trayectoria de cada obstáculo móvil."""
        colors = self.palette
        for i, spec in enumerate(m.dynamic_obstacles):
            chosen = i == selected
            color, width = (colors.selected, 2) if chosen else (colors.trajectory, 1)
            if spec.kind == "circular":
                center = viewport.to_screen(spec.center_x, spec.center_y)
                pygame.draw.circle(surface, color, center, max(1, int(spec.orbit_radius * viewport.scale)), width)
                if chosen:
                    pygame.draw.circle(surface, color, center, 3)
            elif spec.kind == "horizontal":
                pygame.draw.line(surface, color, viewport.to_screen(spec.range_min, spec.y),
                                 viewport.to_screen(spec.range_max, spec.y), width)
            else:
                pygame.draw.line(surface, color, viewport.to_screen(spec.x, spec.range_min),
                                 viewport.to_screen(spec.x, spec.range_max), width)
            self._star(surface, viewport, spec.x, spec.y, spec.radius,
                       colors.selected if chosen else colors.dynamic, color)

    def draw_heading(self, surface, viewport: Viewport, x, y, heading, color=None) -> None:
        """Flecha corta que indica una orientación (inicio del vehículo en el editor)."""
        color = color or self.palette.start
        cos, sin = math.cos(heading), math.sin(heading)
        tail = viewport.to_screen(x + 0.45 * cos, y + 0.45 * sin)
        tip = viewport.to_screen(x + 1.7 * cos, y + 1.7 * sin)
        pygame.draw.line(surface, color, tail, tip, 2)
        pygame.draw.circle(surface, color, tip, 3)

    # --- móviles ------------------------------------------------------------------
    def _vehicle_sprite(self, size: int, color, heading: float) -> pygame.Surface:
        step = int(round(math.degrees(heading) / 5.0)) % 72
        key = (size, color, step)
        sprite = self._sprites.get(key)
        if sprite is None:
            head = self.fonts.render(symbols.VEHICLE_HEAD, size, color)
            body = self.fonts.render(symbols.VEHICLE_BODY, size, color)
            line = int(size * 0.8)
            base = pygame.Surface((body.get_width(), 2 * line), pygame.SRCALPHA)
            base.blit(head, head.get_rect(center=(base.get_width() // 2, line // 2)))
            base.blit(body, body.get_rect(center=(base.get_width() // 2, line + line // 2)))
            # El dibujo base mira hacia arriba; se rota hasta la orientación del vehículo.
            if len(self._sprites) > 600:
                self._sprites.clear()
            sprite = self._sprites[key] = pygame.transform.rotate(base, -(step * 5.0 + 90.0))
        return sprite

    def draw_vehicle(self, surface, viewport: Viewport, x, y, heading, moving: bool = True) -> None:
        """El vehículo como 'o' sobre '| |', orientado."""
        color = self.palette.vehicle if moving else self.palette.vehicle_stopped
        sprite = self._vehicle_sprite(max(9, int(viewport.scale * 0.6)), color, heading)
        surface.blit(sprite, sprite.get_rect(center=viewport.to_screen(x, y)))

    def draw_mobile(self, surface, viewport: Viewport, mobile) -> None:
        """LiDAR (siempre visible) y vehículo."""
        colors = self.palette
        state = mobile.state
        center = viewport.to_screen(state.x, state.y)
        if mobile.sensor is not None and len(mobile.scan):
            points = mobile.sensor.hit_points(state.x, state.y, state.heading, mobile.scan)
            xs = (viewport.ox + points[:, 0] * viewport.scale).astype(int)
            ys = (viewport.oy + points[:, 1] * viewport.scale).astype(int)
            hits = mobile.scan < 1.0
            for i in range(len(xs)):
                pygame.draw.aaline(surface, colors.ray_hit if hits[i] else colors.ray, center, (int(xs[i]), int(ys[i])))
            for i in range(len(xs)):
                if hits[i]:
                    surface.fill(colors.hit_point, (int(xs[i]) - 1, int(ys[i]) - 1, 3, 3))
        if mobile.navigation is not None and mobile.active:
            tx, ty = viewport.to_screen(*mobile.navigation.target)
            pygame.draw.line(surface, colors.target, (tx - 3, ty), (tx + 3, ty))
            pygame.draw.line(surface, colors.target, (tx, ty - 3), (tx, ty + 3))
        self.draw_vehicle(surface, viewport, state.x, state.y, state.heading, mobile.status in MOVING)

    # --- capas opcionales -------------------------------------------------------------
    def draw_heatmap(self, surface, viewport: Viewport, grid, cache_key=None) -> None:
        """Intensidad 0..1 por celda (filas x columnas) como manchas translúcidas sobre el mapa."""
        key = ("heat", cache_key, viewport.rect.size) if cache_key is not None else None
        layer = self._layers.get(key) if key is not None else None
        if layer is None:
            layer = pygame.Surface(viewport.rect.size, pygame.SRCALPHA)
            rows, cols = len(grid), len(grid[0]) if len(grid) else 0
            width, height = viewport.rect.width / max(cols, 1), viewport.rect.height / max(rows, 1)
            for row in range(rows):
                for col in range(cols):
                    value = float(grid[row][col])
                    if value > 0.03:
                        layer.fill((*self.palette.heat, int(16 + 96 * value)),
                                   (int(col * width), int(row * height), int(width) + 1, int(height) + 1))
            self._remember(key, layer)
        surface.blit(layer, viewport.rect.topleft)

    def draw_path(self, surface, viewport: Viewport, points: Sequence, color=None, width: int = 1) -> None:
        """Polilínea en coordenadas del mundo (la ruta que un controlador piensa seguir)."""
        if len(points) >= 2:
            pygame.draw.lines(surface, color or self.palette.planned, False,
                              [viewport.to_screen(x, y) for x, y in points], width)

    def draw_trail(self, surface, viewport: Viewport, points: Sequence) -> None:
        """Camino ya recorrido por un vehículo."""
        if len(points) >= 2:
            pygame.draw.aalines(surface, self.palette.trail, False, [viewport.to_screen(x, y) for x, y in points])

    def draw_simulation(self, surface, viewport: Viewport, simulation, cache_key=None, heatmap=None,
                        heat_key=None, trail: Optional[Sequence] = None) -> None:
        self.draw_map(surface, viewport, simulation.world.map, cache_key)
        if heatmap is not None:
            self.draw_heatmap(surface, viewport, heatmap, heat_key)
        self.draw_obstacles(surface, viewport, simulation.world)
        if trail:
            self.draw_trail(surface, viewport, trail)
        for mobile in simulation.mobiles:
            planned = getattr(mobile.controller, "planned_path", None)
            if planned is not None:
                self.draw_path(surface, viewport, planned)
            self.draw_mobile(surface, viewport, mobile)
