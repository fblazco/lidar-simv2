"""Controles mínimos sobre Pygame: colores, fuentes monoespaciadas y paneles con botones."""
from __future__ import annotations

import textwrap
from typing import Callable, List, Optional, Sequence, Tuple

import pygame

BACKGROUND = (13, 17, 23)
PANEL_BG = (22, 27, 34)
BORDER = (48, 54, 61)
TEXT = (201, 209, 217)
MUTED = (125, 133, 144)
ACCENT = (88, 166, 255)
GOOD = (63, 185, 80)
WARN = (210, 153, 34)
BAD = (248, 81, 73)
BUTTON = (33, 38, 45)
BUTTON_HOVER = (48, 54, 61)
BUTTON_ACTIVE = (31, 80, 140)

MONO_FONTS = "dejavusansmono,liberationmono,ubuntumono,couriernew,monospace"


class Fonts:
    """Fuente monoespaciada en cualquier tamaño, con caché de textos ya dibujados."""

    def __init__(self) -> None:
        self._path = pygame.font.match_font(MONO_FONTS)
        self._fonts = {}
        self._rendered = {}

    def get(self, size: int) -> pygame.font.Font:
        if size not in self._fonts:
            self._fonts[size] = pygame.font.Font(self._path, size)
        return self._fonts[size]

    def render(self, text: str, size: int, color) -> pygame.Surface:
        key = (text, size, color)
        image = self._rendered.get(key)
        if image is None:
            if len(self._rendered) > 4000:
                self._rendered.clear()
            image = self._rendered[key] = self.get(size).render(text, True, color)
        return image

    def char_width(self, size: int) -> int:
        return max(1, self.get(size).size("M")[0])


def draw_text(surface, fonts: Fonts, text: str, pos, size: int = 14, color=TEXT, anchor: str = "topleft"):
    image = fonts.render(text, size, color)
    rect = image.get_rect(**{anchor: pos})
    surface.blit(image, rect)
    return rect


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


ButtonSpec = Tuple  # (etiqueta, acción, activo=False, habilitado=True)


class Panel:
    """Columna de controles que se reconstruye en cada cuadro.

    Dibuja de arriba hacia abajo y recuerda las zonas pulsables; la vista
    conserva el panel del último cuadro para resolver los clics.
    """

    def __init__(self, fonts: Fonts, rect: pygame.Rect, mouse) -> None:
        self.fonts = fonts
        self.rect = rect
        self.mouse = mouse
        self.x = rect.x + 12
        self.width = rect.width - 24
        self.y = rect.y + 10
        self.surface: Optional[pygame.Surface] = None
        self._hits: List[Tuple[pygame.Rect, Callable[[], None]]] = []

    def begin(self, surface: pygame.Surface) -> None:
        self.surface = surface
        surface.fill(PANEL_BG, self.rect)
        pygame.draw.line(surface, BORDER, self.rect.topleft, self.rect.bottomleft)

    def title(self, text: str) -> None:
        draw_text(self.surface, self.fonts, text, (self.x, self.y), 15, ACCENT)
        self.y += 24

    def text(self, text: str, color=TEXT, size: int = 13) -> None:
        columns = max(8, self.width // self.fonts.char_width(size))
        for line in textwrap.wrap(text, columns) or [""]:
            draw_text(self.surface, self.fonts, line, (self.x, self.y), size, color)
            self.y += size + 5

    def gap(self, height: int = 8) -> None:
        self.y += height

    def reserve(self, height: int) -> pygame.Rect:
        rect = pygame.Rect(self.x, self.y, self.width, height)
        self.y += height + 6
        return rect

    def _button(self, rect: pygame.Rect, label: str, action, active: bool = False, enabled: bool = True) -> None:
        hover = enabled and rect.collidepoint(self.mouse)
        color = BUTTON_ACTIVE if active else BUTTON_HOVER if hover else BUTTON
        pygame.draw.rect(self.surface, color, rect, border_radius=4)
        pygame.draw.rect(self.surface, BORDER, rect, 1, border_radius=4)
        draw_text(self.surface, self.fonts, label, rect.center, 13, TEXT if enabled else MUTED, "center")
        if enabled and action is not None:
            self._hits.append((rect, action))

    def buttons(self, specs: Sequence[ButtonSpec], height: int = 26) -> None:
        """Una fila de botones de igual ancho."""
        gap = 6
        width = (self.width - gap * (len(specs) - 1)) // len(specs)
        for i, spec in enumerate(specs):
            rect = pygame.Rect(self.x + i * (width + gap), self.y, width, height)
            self._button(rect, *spec)
        self.y += height + 6

    def stepper(self, label: str, value: str, on_minus, on_plus) -> None:
        """Etiqueta con valor y botones - / + a la derecha."""
        draw_text(self.surface, self.fonts, f"{label}: {value}", (self.x, self.y + 5), 13)
        right = self.x + self.width
        self._button(pygame.Rect(right - 62, self.y, 28, 24), "-", on_minus)
        self._button(pygame.Rect(right - 28, self.y, 28, 24), "+", on_plus)
        self.y += 30

    def text_field(self, field: TextInput, label: str) -> None:
        draw_text(self.surface, self.fonts, label, (self.x, self.y), 12, MUTED)
        self.y += 17
        rect = pygame.Rect(self.x, self.y, self.width, 26)
        pygame.draw.rect(self.surface, BACKGROUND, rect, border_radius=4)
        pygame.draw.rect(self.surface, ACCENT if field.active else BORDER, rect, 1, border_radius=4)
        draw_text(self.surface, self.fonts, field.text + ("_" if field.active else ""), (rect.x + 8, rect.y + 5), 13)
        self._hits.append((rect, lambda: setattr(field, "active", True)))
        self.y += 32

    def click(self, pos) -> bool:
        for rect, action in self._hits:
            if rect.collidepoint(pos):
                action()
                return True
        return self.rect.collidepoint(pos)
