"""Componentes de la interfaz sobre Pygame: fuentes, formas suavizadas, íconos y controles.

``Toolkit`` reúne lo que comparten todas las vistas (tema, fuentes, cachés).
En cada cuadro una vista pide un ``Ui``, dibuja con él y lo conserva para
resolver los clics: cada control anota su zona pulsable al dibujarse.
"""
from __future__ import annotations

import io
import json
import re
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import pygame

from ui.theme import Theme, get_theme

MONO_FONTS = "dejavusansmono,ubuntumono,liberationmono,couriernew,monospace"
SANS_FONTS = "ubuntu,dejavusans,liberationsans,notosans,arial,helvetica"
ICON_DIR = Path(__file__).parent / "assets" / "icons"
SMOOTH = 3                 # las formas se dibujan a este múltiplo y se reducen para suavizar los bordes


class Fonts:
    """Fuentes de la interfaz (sans y negrita) y monoespaciada (símbolos del mapa y cifras), con caché."""

    def __init__(self) -> None:
        sans = pygame.font.match_font(SANS_FONTS)
        self._paths = {"mono": pygame.font.match_font(MONO_FONTS), "sans": sans,
                       "bold": pygame.font.match_font(SANS_FONTS, bold=True) or sans}
        self._fonts = {}
        self._rendered = {}

    def get(self, size: int, face: str = "mono") -> pygame.font.Font:
        key = (face, size)
        if key not in self._fonts:
            self._fonts[key] = pygame.font.Font(self._paths.get(face), size)
        return self._fonts[key]

    def render(self, text: str, size: int, color, face: str = "mono") -> pygame.Surface:
        key = (text, size, color, face)
        image = self._rendered.get(key)
        if image is None:
            if len(self._rendered) > 5000:
                self._rendered.clear()
            image = self._rendered[key] = self.get(size, face).render(text, True, color)
        return image

    def width(self, text: str, size: int, face: str = "sans") -> int:
        return self.get(size, face).size(text)[0]

    def char_width(self, size: int) -> int:
        return max(1, self.get(size).size("M")[0])

    def wrap(self, text: str, width: int, size: int, face: str = "sans") -> List[str]:
        """Parte un texto en líneas que caben en ``width`` pixeles."""
        font = self.get(size, face)
        lines: List[str] = []
        for paragraph in text.split("\n"):
            line = ""
            for word in paragraph.split():
                candidate = f"{line} {word}".strip()
                if line and font.size(candidate)[0] > width:
                    lines.append(line)
                    line = word
                else:
                    line = candidate
            lines.append(line)
        return lines


class Shapes:
    """Rectángulos redondeados con bordes suaves; el relleno puede ser un degradado vertical."""

    def __init__(self) -> None:
        self._cache: Dict[tuple, pygame.Surface] = {}

    def rounded(self, surface, rect, radius: int, fill=None, border=None, width: int = 1) -> None:
        rect = pygame.Rect(rect)
        if rect.width <= 0 or rect.height <= 0:
            return
        radius = max(0, min(int(radius), rect.width // 2, rect.height // 2))
        key = (rect.size, radius, fill, border, width)
        image = self._cache.get(key)
        if image is None:
            if len(self._cache) > 900:
                self._cache.clear()
            image = self._cache[key] = self._make(rect.size, radius, fill, border, width)
        surface.blit(image, rect.topleft)

    def frame(self, surface, rect, radius: int, outside, border, width: int = 1) -> None:
        """Marco redondeado que tapa las esquinas de lo ya dibujado dentro de ``rect`` (un mapa, una imagen)."""
        rect = pygame.Rect(rect)
        if rect.width <= 0 or rect.height <= 0:
            return
        key = ("frame", rect.size, radius, outside, border, width)
        image = self._cache.get(key)
        if image is None:
            big = pygame.Surface((rect.width * SMOOTH, rect.height * SMOOTH), pygame.SRCALPHA)
            big.fill((*outside, 255))
            pygame.draw.rect(big, (*border, 255), big.get_rect(), border_radius=radius * SMOOTH)
            inner = big.get_rect().inflate(-2 * width * SMOOTH, -2 * width * SMOOTH)
            pygame.draw.rect(big, (0, 0, 0, 0), inner, border_radius=max(0, (radius - width) * SMOOTH))
            image = self._cache[key] = pygame.transform.smoothscale(big, rect.size)
        surface.blit(image, rect.topleft)

    @staticmethod
    def _filled(size, radius, fill) -> pygame.Surface:
        shape = pygame.Surface(size, pygame.SRCALPHA)
        if isinstance(fill[0], (tuple, list)):          # degradado: se pinta entero y se recorta con la forma
            top, bottom = fill
            height = max(size[1] - 1, 1)
            for y in range(size[1]):
                t = y / height
                shape.fill([int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)] + [255], (0, y, size[0], 1))
            mask = pygame.Surface(size, pygame.SRCALPHA)
            pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=radius)
            shape.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        else:
            pygame.draw.rect(shape, (*fill, 255), shape.get_rect(), border_radius=radius)
        return shape

    def _make(self, size, radius, fill, border, width) -> pygame.Surface:
        big = (size[0] * SMOOTH, size[1] * SMOOTH)
        radius, width = radius * SMOOTH, width * SMOOTH
        image = pygame.Surface(big, pygame.SRCALPHA)
        if border is not None:
            pygame.draw.rect(image, (*border, 255), image.get_rect(), border_radius=radius)
            inner = image.get_rect().inflate(-2 * width, -2 * width)
            pygame.draw.rect(image, (0, 0, 0, 0), inner, border_radius=max(0, radius - width))
            if fill is not None and inner.width > 0 and inner.height > 0:
                image.blit(self._filled(inner.size, max(0, radius - width), fill), inner.topleft)
        elif fill is not None:
            image.blit(self._filled(big, radius, fill), (0, 0))
        return pygame.transform.smoothscale(image, size)


class Assets:
    """Íconos (SVG de un solo color, teñidos con el del tema) y escenas (JSON), leídos una sola vez."""

    def __init__(self) -> None:
        self._sources: Dict[str, Optional[str]] = {}
        self._icons: Dict[tuple, Optional[pygame.Surface]] = {}
        self._scenes: Dict[str, Optional[dict]] = {}

    def _source(self, path: str) -> Optional[str]:
        if path not in self._sources:
            try:
                self._sources[path] = Path(path).read_text(encoding="utf-8")
            except OSError:
                self._sources[path] = None
        return self._sources[path]

    def icon(self, path: str, size: int, color) -> Optional[pygame.Surface]:
        """Ícono de ``size`` pixeles en ``color``; ``None`` si el archivo falta o no se puede leer."""
        if not path:
            return None
        if "/" not in path and "\\" not in path:        # nombre de un ícono propio de la interfaz
            path = str(ICON_DIR / f"{path}.svg")
        key = (path, size, tuple(color))
        if key not in self._icons:
            if len(self._icons) > 400:
                self._icons.clear()
            self._icons[key] = self._load_icon(path, size, color)
        return self._icons[key]

    def _load_icon(self, path: str, size: int, color) -> Optional[pygame.Surface]:
        source = self._source(path)
        if source is None:
            return None
        pixels = size * SMOOTH
        # El tamaño de dibujo se fija en la etiqueta raíz: el SVG se rasteriza grande y luego se reduce.
        root = re.search(r"<svg\b[^>]*>", source)
        if root is None:
            return None
        tag = re.sub(r'\s(width|height)="[^"]*"', "", root.group(0))
        tag = tag.replace("<svg", f'<svg width="{pixels}" height="{pixels}"', 1)
        try:
            image = pygame.image.load(io.BytesIO((source[:root.start()] + tag + source[root.end():]).encode("utf-8")),
                                      "icon.svg").convert_alpha()
        except (pygame.error, ValueError):
            return None
        image = pygame.transform.smoothscale(image, (size, size))
        image.fill((*color, 255), special_flags=pygame.BLEND_RGBA_MULT)
        return image

    def scene(self, path: str) -> Optional[dict]:
        """Escena de demostración de un plugin; ``None`` si no tiene o no se puede leer."""
        if not path:
            return None
        if path not in self._scenes:
            try:
                scene = json.loads(Path(path).read_text(encoding="utf-8"))
                self._scenes[path] = scene if isinstance(scene, dict) and "map" in scene else None
            except (OSError, ValueError):
                self._scenes[path] = None
        return self._scenes[path]


class TextInput:
    """Campo de texto de una línea (para el nombre del mapa)."""

    def __init__(self, text: str = "") -> None:
        self.text = text
        self.active = False

    def handle_key(self, event) -> None:
        if event.key == pygame.K_BACKSPACE:
            self.text = self.text[:-1]
        elif event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
            self.active = False
        elif event.unicode and (event.unicode.isalnum() or event.unicode in "_-") and len(self.text) < 28:
            self.text += event.unicode


class Toolkit:
    """Lo que comparten las vistas: tema activo, fuentes y cachés de formas, íconos y escenas."""

    def __init__(self, theme_name: str = "light") -> None:
        self.theme = get_theme(theme_name)
        self.fonts = Fonts()
        self.shapes = Shapes()
        self.assets = Assets()

    def set_theme(self, name: str) -> None:
        self.theme = get_theme(name)

    def frame(self, surface, mouse) -> "Ui":
        return Ui(self, surface, mouse)


class Ui:
    """Dibujo de un cuadro. Los controles anotan su zona pulsable; ``click`` la resuelve después."""

    def __init__(self, kit: Toolkit, surface, mouse) -> None:
        self.kit = kit
        self.theme: Theme = kit.theme
        self.fonts = kit.fonts
        self.surface = surface
        self.mouse = mouse
        self._hits: List[Tuple[pygame.Rect, Callable[[], None]]] = []

    # --- clics -------------------------------------------------------------------
    def hit(self, rect, action) -> None:
        if action is not None:
            self._hits.append((pygame.Rect(rect), action))

    def click(self, pos) -> bool:
        """Ejecuta el control que está bajo ``pos``. Devuelve si había alguno."""
        for rect, action in reversed(self._hits):       # lo último dibujado queda encima
            if rect.collidepoint(pos):
                action()
                return True
        return False

    def hover(self, rect) -> bool:
        return pygame.Rect(rect).collidepoint(self.mouse)

    # --- texto -------------------------------------------------------------------
    def text(self, text: str, pos, size: int = 14, color=None, face: str = "sans", anchor: str = "topleft"):
        image = self.fonts.render(str(text), size, color or self.theme.text, face)
        rect = image.get_rect(**{anchor: pos})
        self.surface.blit(image, rect)
        return rect

    def paragraph(self, text: str, x: int, y: int, width: int, size: int = 13, color=None, face: str = "sans",
                  max_lines: Optional[int] = None, spacing: int = 4) -> int:
        """Texto en varias líneas. Devuelve la coordenada y donde termina."""
        lines = self.fonts.wrap(text, width, size, face)
        if max_lines is not None and len(lines) > max_lines:
            lines = lines[:max_lines]
            lines[-1] = lines[-1].rstrip(" .,;:") + "…"
        for line in lines:
            self.text(line, (x, y), size, color or self.theme.muted, face)
            y += size + spacing
        return y

    def fit(self, text: str, width: int, size: int, face: str = "sans") -> str:
        """El texto, recortado con puntos suspensivos si no cabe en ``width``."""
        if self.fonts.width(text, size, face) <= width:
            return text
        while len(text) > 1 and self.fonts.width(text + "…", size, face) > width:
            text = text[:-1]
        return text.rstrip() + "…"

    # --- superficies ----------------------------------------------------------------
    def card(self, rect, radius: int = 18, fill=None, border=True) -> pygame.Rect:
        rect = pygame.Rect(rect)
        self.kit.shapes.rounded(self.surface, rect, radius, fill if fill is not None else self.theme.surface,
                                self.theme.line if border is True else border or None)
        return rect

    def box(self, rect, radius: int = 12) -> pygame.Rect:
        """Recuadro secundario dentro de una tarjeta."""
        return self.card(rect, radius, self.theme.soft)

    def divider(self, x: int, y: int, width: int) -> None:
        pygame.draw.line(self.surface, self.theme.line, (x, y), (x + width - 1, y))

    def frame(self, rect, radius: int = 18, outside=None) -> None:
        """Borde redondeado sobre un mapa o una imagen ya dibujados: les recorta las esquinas."""
        self.kit.shapes.frame(self.surface, rect, radius, outside or self.theme.background, self.theme.line)

    # --- íconos ------------------------------------------------------------------------
    def icon(self, path: str, center, size: int = 20, color=None, fallback: str = "") -> None:
        image = self.kit.assets.icon(path, size, color or self.theme.text)
        if image is not None:
            self.surface.blit(image, image.get_rect(center=center))
        elif fallback:                                   # sin ícono: la inicial del nombre
            self.text(fallback[:1].upper(), center, max(10, int(size * 0.7)), color, "bold", "center")

    # --- controles ---------------------------------------------------------------------
    def button(self, rect, label: str, action=None, kind: str = "outline", enabled: bool = True,
               icon: str = "", size: int = 14, radius: Optional[int] = None) -> pygame.Rect:
        """``kind``: 'primary' (acción principal o elegido), 'outline', 'control' o 'ghost'."""
        theme, rect = self.theme, pygame.Rect(rect)
        radius = rect.height // 2 if radius is None else radius
        hover = enabled and action is not None and self.hover(rect)
        if kind == "primary":
            fill, border, color, face = theme.primary, None, theme.on_primary, "bold"
        elif kind == "outline":
            fill, border, color, face = (theme.soft if hover else theme.background), theme.outline, theme.text, "sans"
        elif kind == "control":
            fill, border, color, face = (theme.soft if hover else theme.control), theme.control_line, theme.text, "sans"
        else:
            fill, border, color, face = (theme.soft if hover else None), None, theme.text, "sans"
        if not enabled:
            color, border = theme.muted, (theme.line if border is not None else None)
            fill = theme.soft if kind == "primary" else fill
        if fill is not None or border is not None:
            self.kit.shapes.rounded(self.surface, rect, radius, fill, border)
        label_image = self.fonts.render(label, size, color, face) if label else None
        content = (label_image.get_width() if label_image else 0) + ((size + 8) if icon and label else size if icon else 0)
        x = rect.centerx - content // 2
        if icon:
            self.icon(icon, (x + size // 2 + 1, rect.centery), size + 2, color)
            x += size + 8
        if label_image is not None:
            self.surface.blit(label_image, label_image.get_rect(midleft=(x, rect.centery)))
        if enabled:
            self.hit(rect, action)
        return rect

    def segmented(self, rect, options: Sequence[Tuple[str, str]], selected, on_select, gap: int = 6,
                  size: int = 13) -> None:
        """Opciones excluyentes en píldoras de igual ancho. ``options``: (clave, etiqueta)."""
        rect = pygame.Rect(rect)
        width = (rect.width - gap * (len(options) - 1)) // max(len(options), 1)
        for i, (key, label) in enumerate(options):
            cell = pygame.Rect(rect.x + i * (width + gap), rect.y, width, rect.height)
            self.button(cell, self.fit(label, width - 12, size), lambda k=key: on_select(k),
                        "primary" if key == selected else "control", size=size)

    def stepper(self, right: int, center_y: int, value: str, on_minus, on_plus, value_width: int = 46,
                button: int = 36) -> None:
        """Valor con un botón para bajar y otro para subir, alineado a la derecha."""
        plus = pygame.Rect(right - button, center_y - button // 2, button, button)
        minus = pygame.Rect(plus.x - value_width - button - 12, plus.y, button, button)
        self.button(minus, "−", on_minus, "control", size=17)
        self.button(plus, "+", on_plus, "control", size=17)
        self.text(value, ((minus.right + plus.x) // 2, center_y), 15, face="mono", anchor="center")

    def toggle(self, right: int, center_y: int, value: bool, action) -> None:
        """Interruptor de dos posiciones."""
        theme = self.theme
        rect = pygame.Rect(right - 46, center_y - 13, 46, 26)
        self.kit.shapes.rounded(self.surface, rect, 13, theme.primary if value else theme.track,
                                None if value else theme.control_line)
        knob = pygame.Rect(0, 0, 20, 20)
        knob.center = (rect.right - 13 if value else rect.x + 13, rect.centery)
        self.kit.shapes.rounded(self.surface, knob, 10, theme.on_primary if value else theme.muted)
        self.hit(rect, action)

    def link(self, text: str, pos, action, size: int = 13, anchor: str = "topleft") -> pygame.Rect:
        rect = self.text(text, pos, size, self.theme.text, "sans", anchor)
        pygame.draw.line(self.surface, self.theme.text, (rect.x, rect.bottom), (rect.right, rect.bottom))
        self.hit(rect.inflate(10, 10), action)
        return rect

    def progress(self, rect, fraction: float) -> None:
        rect = pygame.Rect(rect)
        self.kit.shapes.rounded(self.surface, rect, rect.height // 2, self.theme.track)
        width = int(rect.width * max(0.0, min(1.0, fraction)))
        if width >= rect.height:
            self.kit.shapes.rounded(self.surface, (rect.x, rect.y, width, rect.height), rect.height // 2,
                                    self.theme.primary)

    def badge(self, center, letter: str, filled: bool = True, size: int = 22) -> None:
        """Marca redonda con una letra (corridas A y B)."""
        rect = pygame.Rect(0, 0, size, size)
        rect.center = center
        if filled:
            self.kit.shapes.rounded(self.surface, rect, size // 2, self.theme.primary)
            self.text(letter, rect.center, 12, self.theme.on_primary, "mono", "center")
        else:
            self.kit.shapes.rounded(self.surface, rect, size // 2, None, self.theme.text, 2)
            self.text(letter, rect.center, 12, self.theme.text, "mono", "center")

    def stat(self, x: int, y: int, label: str, value: str, size: int = 20) -> None:
        """Etiqueta pequeña con su cifra debajo."""
        self.text(label, (x, y), 12, self.theme.muted)
        self.text(value, (x, y + 17), size, face="mono")
