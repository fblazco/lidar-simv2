"""Dibujo del mundo en Pygame con caracteres ASCII.

Solo lee el estado del simulador; nunca lo modifica. Cada vista se dibuja en
un ``Viewport`` propio, lo que permite mostrar varios mundos en una ventana.
"""
from __future__ import annotations

import math
from typing import Optional

import pygame

from control.controller import ROUTE_FOLLOWING
from rendering import ascii_renderer as symbols
from simulation.map_data import MapData
from simulation.vehicle import Status

MAP_BG = (10, 13, 18)
GRID = (33, 40, 50)
FRAME = (48, 54, 61)
ROUTE = (57, 197, 207)
ROUTE_UNUSED = (52, 78, 92)        # camino dibujado pero ignorado en modo libre
STATIC = (255, 123, 114)
DYNAMIC = (210, 168, 255)
TRAJECTORY = (72, 60, 96)
SELECTED = (255, 255, 255)
START = (227, 179, 65)
GOAL = (86, 211, 100)
RAY = (30, 44, 40)
RAY_HIT = (46, 110, 78)
HIT_POINT = (126, 231, 135)
TARGET = (110, 118, 129)
HEAT = (255, 166, 87)            # intensidad por celda que publica una estrategia (p. ej. feromona)
PLANNED = (121, 192, 255)        # ruta planificada por el controlador de un móvil
VEHICLE_COLORS = {
    Status.ACTIVE: (240, 246, 252),
    Status.COLLIDED: (248, 81, 73),
    Status.REACHED_GOAL: (86, 211, 100),
    Status.TIMED_OUT: (125, 133, 144),
}


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
    def __init__(self, fonts) -> None:
        self.fonts = fonts
        self._layers = {}     # capas estáticas del mapa ya dibujadas
        self._sprites = {}    # vehículo rotado por tamaño, color y ángulo

    # --- mapa (capa estática) ------------------------------------------------
    def draw_map(self, surface, viewport: Viewport, map_data: MapData, cache_key=None) -> None:
        key = (cache_key, viewport.rect.size) if cache_key is not None else None
        layer = self._layers.get(key) if key is not None else None
        if layer is None:
            layer = self._render_map(viewport, map_data)
            if key is not None:
                if len(self._layers) > 32:
                    self._layers.clear()
                self._layers[key] = layer
        surface.blit(layer, viewport.rect.topleft)

    def _render_map(self, viewport: Viewport, m: MapData) -> pygame.Surface:
        layer = pygame.Surface(viewport.rect.size)
        layer.fill(MAP_BG)
        cell = viewport.scale * m.cell_size
        size = max(6, int(cell * 0.95))

        def put(char, where, color):
            image = self.fonts.render(char, size, color)
            layer.blit(image, image.get_rect(center=((where[0] + 0.5) * cell, (where[1] + 0.5) * cell)))

        if cell >= 6:
            for col in range(m.cols):
                for row in range(m.rows):
                    layer.fill(GRID, (int((col + 0.5) * cell), int((row + 0.5) * cell), 1, 1))
        route_color = ROUTE if m.navigation_mode == ROUTE_FOLLOWING else ROUTE_UNUSED
        for where, char in symbols.route_glyphs(m.route).items():
            put(char, where, route_color)
        for where in m.static_obstacles:
            put(symbols.STATIC, where, STATIC)
        if m.goal is not None:
            put(symbols.GOAL, m.goal, GOAL)
        if m.start is not None:
            put(symbols.START, m.start, START)
        pygame.draw.rect(layer, FRAME, layer.get_rect(), 1)
        return layer

    # --- obstáculos dinámicos --------------------------------------------------
    def _star(self, surface, viewport: Viewport, x, y, radius, color) -> None:
        center = viewport.to_screen(x, y)
        pygame.draw.circle(surface, TRAJECTORY, center, max(2, int(radius * viewport.scale)), 1)
        image = self.fonts.render(symbols.DYNAMIC, max(8, int(viewport.scale * 1.3)), color)
        surface.blit(image, image.get_rect(center=center))

    def draw_obstacles(self, surface, viewport: Viewport, world) -> None:
        """Obstáculos móviles en su posición actual."""
        for x, y, radius in world.circles:
            self._star(surface, viewport, x, y, radius, DYNAMIC)

    def draw_dynamic_specs(self, surface, viewport: Viewport, m: MapData, selected: Optional[int] = None) -> None:
        """Vista de edición: posición inicial y trayectoria de cada obstáculo móvil."""
        for i, spec in enumerate(m.dynamic_obstacles):
            color = SELECTED if i == selected else TRAJECTORY
            if spec.kind == "circular":
                center = viewport.to_screen(spec.center_x, spec.center_y)
                pygame.draw.circle(surface, color, center, max(1, int(spec.orbit_radius * viewport.scale)), 1)
            elif spec.kind == "horizontal":
                pygame.draw.line(surface, color, viewport.to_screen(spec.range_min, spec.y),
                                 viewport.to_screen(spec.range_max, spec.y))
            else:
                pygame.draw.line(surface, color, viewport.to_screen(spec.x, spec.range_min),
                                 viewport.to_screen(spec.x, spec.range_max))
            self._star(surface, viewport, spec.x, spec.y, spec.radius, SELECTED if i == selected else DYNAMIC)

    def draw_heading(self, surface, viewport: Viewport, x, y, heading, color=START) -> None:
        """Flecha corta que indica una orientación (inicio del vehículo en el editor)."""
        length = 1.4
        tip = (x + length * math.cos(heading), y + length * math.sin(heading))
        pygame.draw.line(surface, color, viewport.to_screen(x, y), viewport.to_screen(*tip), 2)
        pygame.draw.circle(surface, color, viewport.to_screen(*tip), 3)

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
            sprite = self._sprites[key] = pygame.transform.rotate(base, -(step * 5.0 + 90.0))
        return sprite

    def draw_mobile(self, surface, viewport: Viewport, mobile) -> None:
        """LiDAR (siempre visible) y vehículo como 'o' sobre '| |'."""
        state = mobile.state
        center = viewport.to_screen(state.x, state.y)
        if mobile.sensor is not None and len(mobile.scan):
            points = mobile.sensor.hit_points(state.x, state.y, state.heading, mobile.scan)
            xs = (viewport.ox + points[:, 0] * viewport.scale).astype(int)
            ys = (viewport.oy + points[:, 1] * viewport.scale).astype(int)
            for i in range(len(xs)):
                hit = mobile.scan[i] < 1.0
                pygame.draw.line(surface, RAY_HIT if hit else RAY, center, (xs[i], ys[i]))
                if hit:
                    surface.fill(HIT_POINT, (xs[i] - 1, ys[i] - 1, 3, 3))
        if mobile.navigation is not None and mobile.active:
            tx, ty = viewport.to_screen(*mobile.navigation.target)
            pygame.draw.line(surface, TARGET, (tx - 3, ty), (tx + 3, ty))
            pygame.draw.line(surface, TARGET, (tx, ty - 3), (tx, ty + 3))
        color = VEHICLE_COLORS[mobile.status]
        sprite = self._vehicle_sprite(max(9, int(viewport.scale * 0.6)), color, state.heading)
        surface.blit(sprite, sprite.get_rect(center=center))

    # --- capas opcionales -------------------------------------------------------------
    def draw_heatmap(self, surface, viewport: Viewport, grid, cache_key=None) -> None:
        """Intensidad 0..1 por celda (filas x columnas) como manchas translúcidas sobre el mapa."""
        key = ("heat", cache_key, viewport.rect.size) if cache_key is not None else None
        layer = self._layers.get(key) if key is not None else None
        if layer is None:
            layer = pygame.Surface(viewport.rect.size, pygame.SRCALPHA)
            rows, cols = grid.shape
            width, height = viewport.rect.width / cols, viewport.rect.height / rows
            for row in range(rows):
                for col in range(cols):
                    value = float(grid[row, col])
                    if value > 0.03:
                        layer.fill((*HEAT, int(25 + 95 * value)),
                                   (int(col * width), int(row * height), int(width) + 1, int(height) + 1))
            if key is not None:
                if len(self._layers) > 32:
                    self._layers.clear()
                self._layers[key] = layer
        surface.blit(layer, viewport.rect.topleft)

    def draw_path(self, surface, viewport: Viewport, points, color=PLANNED) -> None:
        """Polilínea en coordenadas del mundo (la ruta que un controlador piensa seguir)."""
        if len(points) >= 2:
            pygame.draw.lines(surface, color, False, [viewport.to_screen(x, y) for x, y in points], 1)

    def draw_simulation(self, surface, viewport: Viewport, simulation, cache_key=None, heatmap=None,
                        heat_key=None) -> None:
        self.draw_map(surface, viewport, simulation.world.map, cache_key)
        if heatmap is not None:
            self.draw_heatmap(surface, viewport, heatmap, heat_key)
        self.draw_obstacles(surface, viewport, simulation.world)
        for mobile in simulation.mobiles:
            planned = getattr(mobile.controller, "planned_path", None)
            if planned is not None:
                self.draw_path(surface, viewport, planned)
            self.draw_mobile(surface, viewport, mobile)
