"""Escenas explicativas: un cuadro del simulador con capas dibujadas encima.

Una escena es un diccionario (lo aporta cada plugin como JSON) con el mapa y
una lista de operaciones en coordenadas del mundo: los rayos del LiDAR de ese
instante, recorridos, flechas, sectores... Aquí se convierte en una imagen con
los colores de la paleta activa, usando el mismo dibujo del mapa y del vehículo
que el resto de la aplicación.

Formato (versión 1)::

    {"version": 1, "map": {...MapData...}, "ops": [
        {"op": "heat", "grid": [[0.0, 0.4, ...], ...]},
        {"op": "rays", "origin": [x, y], "ends": [[x, y], ...], "hit": [0, 1, ...], "near": [0, 1, ...]},
        {"op": "circles", "items": [[x, y, radio], ...]},
        {"op": "line", "points": [[x, y], ...], "style": "medium", "width": 1.6, "dash": [2, 4]},
        {"op": "arrow", "from": [x, y], "to": [x, y], "style": "strong", "width": 2.8, "head": 9},
        {"op": "wedge", "center": [x, y], "radius": 2.5, "start": a0, "end": a1, "style": "strong",
         "alpha": 62, "outline": "strong", "width": 1.6},
        {"op": "cross", "at": [x, y], "style": "strong", "size": 5.5, "width": 2.4},
        {"op": "dot", "at": [x, y], "style": "faint", "radius": 1.3},
        {"op": "group", "alpha": 58, "ops": [...]},
        {"op": "vehicle", "x": x, "y": y, "heading": radianes, "moving": true}]}

``style`` es un nivel de énfasis ('strong', 'medium' o 'faint'); los grosores y
tamaños están en pixeles para una imagen de 400 de ancho y se escalan con ella.
"""
from __future__ import annotations

import math
from typing import Dict, Sequence, Tuple

import pygame

from rendering import ascii_renderer as symbols
from rendering.renderer import Viewport, WorldRenderer
from simulation.map_data import MapData

SUPERSAMPLE = 3            # se dibuja más grande y se reduce: líneas suaves
REFERENCE_WIDTH = 400.0
ARC_STEP = math.radians(3.0)


class _Painter:
    def __init__(self, surface: pygame.Surface, viewport: Viewport, renderer: WorldRenderer) -> None:
        self.surface = surface
        self.viewport = viewport
        self.renderer = renderer
        self.colors = renderer.palette
        self.unit = viewport.rect.width / REFERENCE_WIDTH

    def point(self, p) -> Tuple[float, float]:
        return (self.viewport.ox + p[0] * self.viewport.scale, self.viewport.oy + p[1] * self.viewport.scale)

    def px(self, size: float) -> int:
        return max(1, int(round(size * self.unit)))

    def run(self, ops: Sequence[dict]) -> None:
        for op in ops:
            handler = getattr(self, "_" + op["op"], None)
            if handler is not None:          # una operación desconocida se ignora: escenas de versiones futuras
                handler(op)

    # --- trazos ------------------------------------------------------------------
    def _stroke(self, points, color, width: int, dash=None) -> None:
        if len(points) < 2:
            return
        if dash is None:
            pygame.draw.lines(self.surface, color, False, points, width)
            if width >= 4:                   # uniones redondeadas en los trazos gruesos
                for p in points:
                    pygame.draw.circle(self.surface, color, p, width / 2.0)
            return
        on, off = dash[0] * self.unit, dash[1] * self.unit
        drawing, left = True, on
        for (x0, y0), (x1, y1) in zip(points, points[1:]):
            length = math.hypot(x1 - x0, y1 - y0)
            done = 0.0
            while length - done > 1e-9:
                step = min(left, length - done)
                if drawing:
                    a = (x0 + (x1 - x0) * done / length, y0 + (y1 - y0) * done / length)
                    b = (x0 + (x1 - x0) * (done + step) / length, y0 + (y1 - y0) * (done + step) / length)
                    pygame.draw.line(self.surface, color, a, b, width)
                done += step
                left -= step
                if left <= 1e-9:
                    drawing = not drawing
                    left = on if drawing else off

    def _line(self, op) -> None:
        self._stroke([self.point(p) for p in op["points"]], self.colors.emphasis(op.get("style", "medium")),
                     self.px(op.get("width", 1.0)), op.get("dash"))

    def _arrow(self, op) -> None:
        color = self.colors.emphasis(op.get("style", "strong"))
        (x0, y0), (x1, y1) = self.point(op["from"]), self.point(op["to"])
        length = math.hypot(x1 - x0, y1 - y0)
        if length < 1e-6:
            return
        ux, uy = (x1 - x0) / length, (y1 - y0) / length
        head = min(op.get("head", 7.0) * self.unit, length * 0.6)
        base = (x1 - ux * head, y1 - uy * head)
        self._stroke([(x0, y0), base], color, self.px(op.get("width", 2.0)), op.get("dash"))
        half = head * 0.55
        pygame.draw.polygon(self.surface, color, [(x1, y1), (base[0] - uy * half, base[1] + ux * half),
                                                  (base[0] + uy * half, base[1] - ux * half)])

    def _wedge(self, op) -> None:
        cx, cy = op["center"]
        start, end, radius = op["start"], op["end"], op["radius"]
        steps = max(2, int(abs(end - start) / ARC_STEP) + 1)
        arc = [(cx + radius * math.cos(start + (end - start) * i / (steps - 1)),
                cy + radius * math.sin(start + (end - start) * i / (steps - 1))) for i in range(steps)]
        outline = [self.point(p) for p in [(cx, cy)] + arc]
        layer = pygame.Surface(self.surface.get_size(), pygame.SRCALPHA)
        pygame.draw.polygon(layer, (*self.colors.emphasis(op.get("style", "strong")), int(op.get("alpha", 60))), outline)
        self.surface.blit(layer, (0, 0))
        if op.get("outline"):
            self._stroke(outline + [outline[0]], self.colors.emphasis(op["outline"]), self.px(op.get("width", 1.0)))

    def _cross(self, op) -> None:
        x, y = self.point(op["at"])
        size, width = op.get("size", 4.0) * self.unit, self.px(op.get("width", 1.5))
        color = self.colors.emphasis(op.get("style", "strong"))
        pygame.draw.line(self.surface, color, (x - size, y - size), (x + size, y + size), width)
        pygame.draw.line(self.surface, color, (x - size, y + size), (x + size, y - size), width)

    def _dot(self, op) -> None:
        pygame.draw.circle(self.surface, self.colors.emphasis(op.get("style", "medium")), self.point(op["at"]),
                           op.get("radius", 2.0) * self.unit)

    def _group(self, op) -> None:
        """Varias operaciones como una sola capa translúcida (los trazos que se pisan no se oscurecen)."""
        target = self.surface
        self.surface = pygame.Surface(target.get_size(), pygame.SRCALPHA)
        self.run(op["ops"])
        layer, self.surface = self.surface, target
        layer.set_alpha(int(op.get("alpha", 255)))
        target.blit(layer, (0, 0))

    # --- elementos del simulador ---------------------------------------------------
    def _heat(self, op) -> None:
        self.renderer.draw_heatmap(self.surface, self.viewport, op["grid"])

    def _rays(self, op) -> None:
        colors = self.colors
        origin = self.point(op["origin"])
        ends = [self.point(p) for p in op["ends"]]
        hit = op.get("hit") or [0] * len(ends)
        near = op.get("near") or [0] * len(ends)
        thin, thick = self.px(1.0), self.px(1.4)
        for i, end in enumerate(ends):
            if not hit[i]:
                pygame.draw.line(self.surface, colors.ray, origin, end, thin)
        for i, end in enumerate(ends):
            if hit[i]:
                pygame.draw.line(self.surface, colors.medium if near[i] else colors.ray_hit, origin, end,
                                 thick if near[i] else thin)
        for i, end in enumerate(ends):
            if hit[i]:
                pygame.draw.circle(self.surface, colors.strong if near[i] else colors.hit_point, end,
                                   (2.2 if near[i] else 1.5) * self.unit)

    def _circles(self, op) -> None:
        scale = self.viewport.scale
        for x, y, radius in op["items"]:
            center = self.point((x, y))
            pygame.draw.circle(self.surface, self.colors.trajectory, center, max(2.0, radius * scale), self.px(1.0))
            image = self.renderer.fonts.render(symbols.DYNAMIC, max(8, int(scale * 1.3)), self.colors.dynamic)
            self.surface.blit(image, image.get_rect(center=center))

    def _vehicle(self, op) -> None:
        self.renderer.draw_vehicle(self.surface, self.viewport, op["x"], op["y"], op["heading"], op.get("moving", True))


class SceneRenderer:
    """Convierte escenas en imágenes del tamaño pedido y las recuerda."""

    def __init__(self, renderer: WorldRenderer) -> None:
        self.renderer = renderer
        self._images: Dict[tuple, pygame.Surface] = {}

    def render(self, scene: dict, size: Tuple[int, int]) -> pygame.Surface:
        size = (max(8, int(size[0])), max(8, int(size[1])))
        key = (id(scene), size, self.renderer.palette.name)
        image = self._images.get(key)
        if image is None:
            if len(self._images) > 64:
                self._images.clear()
            image = self._images[key] = self._draw(scene, size)
        return image

    def _draw(self, scene: dict, size: Tuple[int, int]) -> pygame.Surface:
        world_map = MapData.from_dict(scene["map"])
        big = pygame.Surface((size[0] * SUPERSAMPLE, size[1] * SUPERSAMPLE))
        big.fill(self.renderer.palette.background)
        viewport = Viewport(big.get_rect(), world_map.width, world_map.height, padding=0)
        self.renderer.draw_map(big, viewport, world_map)
        _Painter(big, viewport, self.renderer).run(scene.get("ops", []))
        return pygame.transform.smoothscale(big, size)
