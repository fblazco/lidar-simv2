"""Temas de la interfaz. Todos comparten disposición y componentes."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from rendering.palette import DARK as DARK_WORLD, LIGHT as LIGHT_WORLD, UBUNTU as UBUNTU_WORLD, WorldPalette

Color = Tuple[int, int, int]
Gradient = Tuple[Color, Color]      # (arriba, abajo)


@dataclass(frozen=True)
class Theme:
    name: str
    label: str                 # cómo se llama en la interfaz
    background: Color          # fondo de la ventana
    surface: Gradient          # tarjetas
    soft: Color                # recuadros secundarios dentro de una tarjeta
    line: Color                # bordes y separadores
    control: Color             # botones secundarios y segmentos sin elegir
    control_line: Color
    outline: Color             # borde de los botones secundarios
    text: Color
    muted: Color               # texto secundario
    primary: Gradient          # botón principal y todo lo que está elegido
    on_primary: Color          # texto sobre ``primary``
    track: Color               # fondo de barras de progreso y de comparación
    chrome: Tuple[Color, ...]  # franja metálica bajo la barra superior, de izquierda a derecha
    world: WorldPalette        # colores del simulador


LIGHT = Theme(
    name="light", label="Modo claro", background=(255, 255, 255), surface=((255, 255, 255), (255, 255, 255)),
    soft=(244, 245, 246), line=(220, 223, 227), control=(255, 255, 255), control_line=(196, 200, 206),
    outline=(11, 12, 14), text=(11, 12, 14), muted=(92, 98, 106), primary=((11, 12, 14), (11, 12, 14)),
    on_primary=(255, 255, 255), track=(228, 230, 233),
    chrome=((196, 200, 206), (246, 247, 248), (169, 174, 181), (241, 242, 244), (196, 200, 206)),
    world=LIGHT_WORLD,
)

DARK = Theme(
    name="dark", label="Modo oscuro", background=(11, 12, 14), surface=((26, 28, 32), (19, 21, 24)),
    soft=(16, 18, 20), line=(43, 46, 51), control=(29, 32, 36), control_line=(58, 62, 68),
    outline=(123, 128, 135), text=(236, 238, 240), muted=(162, 167, 174),
    primary=((255, 255, 255), (180, 185, 193)), on_primary=(11, 12, 14), track=(39, 42, 47),
    chrome=((58, 62, 68), (201, 206, 212), (43, 46, 51), (174, 179, 186), (58, 62, 68)),
    world=DARK_WORLD,
)

UBUNTU = Theme(
    name="ubuntu", label="Modo Ubuntu", background=(249, 246, 239),
    surface=((255, 252, 247), (247, 241, 231)), soft=(239, 231, 218),
    line=(211, 197, 179), control=(255, 252, 247), control_line=(177, 153, 133),
    outline=(74, 44, 60), text=(43, 32, 40), muted=(91, 67, 80),
    primary=((119, 33, 111), (94, 39, 80)), on_primary=(255, 252, 247),
    track=(225, 211, 194),
    chrome=((233, 84, 32), (119, 33, 111), (245, 160, 67), (94, 39, 80), (233, 84, 32)),
    world=UBUNTU_WORLD,
)

THEMES = {theme.name: theme for theme in (LIGHT, DARK, UBUNTU)}
DEFAULT_THEME = "light"


def get_theme(name: str) -> Theme:
    """El tema pedido o, si el nombre no existe, el claro."""
    return THEMES.get(name, THEMES[DEFAULT_THEME])


def other_theme(theme: Theme) -> Theme:
    """Siguiente tema en el ciclo de la barra superior."""
    order = (LIGHT, DARK, UBUNTU)
    index = next((i for i, item in enumerate(order) if item.name == theme.name), -1)
    return order[(index + 1) % len(order)]


def _luminance(color: Color) -> float:
    def channel(value: int) -> float:
        value = value / 255.0
        return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4
    red, green, blue = (channel(v) for v in color)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast(a: Color, b: Color) -> float:
    """Contraste entre dos colores según WCAG (de 1 a 21)."""
    high, low = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)
