"""Temas de la interfaz, paletas del mundo, íconos y escenas de los plugins (sin ventana real)."""
import json
from pathlib import Path

import pygame
import pytest

import bootstrap
from rendering.palette import DARK, LIGHT, PALETTES, UBUNTU, WorldPalette
from rendering.renderer import Viewport, WorldRenderer
from rendering.scene import SceneRenderer
from ui.theme import THEMES, contrast, get_theme, other_theme
from ui.widgets import Toolkit

from helpers import corridor_map


@pytest.fixture
def kit():
    pygame.init()
    pygame.display.set_mode((320, 240))
    yield Toolkit("light")
    pygame.quit()


def plugins():
    return list(bootstrap.available_strategies().values()) + list(bootstrap.available_avoidance().values())


def close_to(pixel, color, tolerance=3):
    """El suavizado al reducir una imagen puede mover cada canal un par de niveles."""
    return all(abs(int(pixel[i]) - color[i]) <= tolerance for i in range(3))


def test_there_are_three_themes_and_unknown_names_fall_back_to_light():
    assert set(THEMES) == {"light", "dark", "ubuntu"}
    assert get_theme("no-existe").name == "light"
    assert [other_theme(THEMES[name]).name for name in ("light", "dark", "ubuntu")] == ["dark", "ubuntu", "light"]


@pytest.mark.parametrize("name", ["light", "dark", "ubuntu"])
def test_text_is_readable_on_every_surface_of_a_theme(name):
    theme = THEMES[name]
    for background in (theme.background, theme.soft, theme.control, *theme.surface):
        assert contrast(theme.text, background) >= 7.0
        assert contrast(theme.muted, background) >= 4.5
    for shade in theme.primary:                 # botón principal y elementos elegidos
        assert contrast(theme.on_primary, shade) >= 4.5


@pytest.mark.parametrize("name", ["light", "dark"])
def test_themes_only_use_whites_greys_and_blacks(name):
    theme = THEMES[name]
    colors = [theme.background, theme.soft, theme.line, theme.control, theme.control_line, theme.outline, theme.text,
              theme.muted, theme.on_primary, theme.track, *theme.surface, *theme.primary, *theme.chrome]
    colors += [value for value in vars(theme.world).values() if isinstance(value, tuple)]
    assert all(max(color) - min(color) <= 16 for color in colors)      # casi sin tono: grises fríos


def test_world_palettes_tell_the_elements_apart_by_brightness():
    assert PALETTES == {"light": LIGHT, "dark": DARK, "ubuntu": UBUNTU}
    for palette in (LIGHT, DARK, UBUNTU):
        assert isinstance(palette, WorldPalette)
        assert contrast(palette.vehicle, palette.background) >= 12.0
        assert contrast(palette.static, palette.background) >= 3.0
        assert contrast(palette.ray_hit, palette.background) > contrast(palette.ray, palette.background)
        assert palette.emphasis("strong") == palette.strong and palette.emphasis("otro") == palette.faint


def test_renderer_repaints_the_map_when_the_palette_changes(kit):
    renderer = WorldRenderer(kit.fonts, DARK)
    surface = pygame.Surface((320, 200))
    world_map = corridor_map()
    viewport = Viewport(surface.get_rect(), world_map.width, world_map.height, padding=0)
    renderer.draw_map(surface, viewport, world_map, cache_key="mapa")
    dark = tuple(surface.get_at(viewport.rect.topleft))[:3]
    renderer.set_palette(LIGHT)
    renderer.draw_map(surface, viewport, world_map, cache_key="mapa")
    assert dark == DARK.background and tuple(surface.get_at(viewport.rect.topleft))[:3] == LIGHT.background


def test_every_plugin_ships_an_icon_and_a_demo_scene():
    assert plugins()
    for plugin in plugins():
        assert Path(plugin.icon).is_file(), plugin.name
        scene = json.loads(Path(plugin.demo).read_text(encoding="utf-8"))
        assert scene["version"] == 1 and scene["map"]["cols"] > 0 and scene["ops"], plugin.name
        assert Path(plugin.icon).parent == Path(plugin.demo).parent      # viajan juntos, dentro del plugin


def test_icons_are_tinted_with_the_requested_colour_and_missing_ones_are_none(kit):
    for plugin in plugins():
        icon = kit.assets.icon(plugin.icon, 30, (200, 10, 10))
        assert icon is not None and icon.get_size() == (30, 30), plugin.name
        painted = [icon.get_at((x, y)) for x in range(30) for y in range(30) if icon.get_at((x, y)).a > 200]
        assert painted and all(p.r > 150 and p.g < 40 for p in painted)
    assert kit.assets.icon("train", 20, (0, 0, 0)) is not None            # ícono propio de la interfaz, por nombre
    assert kit.assets.icon("no/existe.svg", 20, (0, 0, 0)) is None
    assert kit.assets.icon("", 20, (0, 0, 0)) is None


def test_demo_scenes_are_drawn_in_the_colours_of_the_active_palette(kit):
    renderer = WorldRenderer(kit.fonts, DARK)
    scenes = SceneRenderer(renderer)
    for plugin in plugins():
        scene = kit.assets.scene(plugin.demo)
        dark = scenes.render(scene, (200, 120))
        assert dark.get_size() == (200, 120)
        assert scenes.render(scene, (200, 120)) is dark                    # se recuerda
        assert close_to(dark.get_at((1, 1)), DARK.background)
        for palette in (LIGHT, UBUNTU):
            renderer.set_palette(palette)
            image = scenes.render(scene, (200, 120))
            assert close_to(image.get_at((1, 1)), palette.background)
            assert len({tuple(image.get_at((x, y)))[:3] for x in range(0, 200, 3) for y in range(0, 120, 3)}) > 4
        renderer.set_palette(DARK)
    assert kit.assets.scene("no/existe.json") is None and kit.assets.scene("") is None


def test_a_scene_with_an_unknown_operation_is_still_drawn(kit):
    scenes = SceneRenderer(WorldRenderer(kit.fonts, DARK))
    scene = {"version": 2, "map": corridor_map().to_dict(), "ops": [{"op": "del-futuro"}, {"op": "dot", "at": [2, 2]}]}
    assert scenes.render(scene, (160, 100)).get_size() == (160, 100)


def test_controls_register_what_they_do_when_clicked(kit):
    surface = pygame.Surface((320, 240))
    ui = kit.frame(surface, (0, 0))
    pressed = []
    ui.button((10, 10, 100, 36), "Guardar", lambda: pressed.append("guardar"), "primary")
    ui.button((10, 60, 100, 36), "Apagado", lambda: pressed.append("apagado"), enabled=False)
    ui.segmented((10, 110, 240, 36), [("a", "Uno"), ("b", "Dos"), ("c", "Tres")], "a", pressed.append)
    ui.stepper(300, 180, "30", lambda: pressed.append("menos"), lambda: pressed.append("más"))
    assert ui.click((20, 20)) and ui.click((130, 120)) and ui.click((290, 180)) and ui.click((200, 180))
    assert not ui.click((20, 70)) and not ui.click((315, 235))
    assert pressed == ["guardar", "b", "más", "menos"]
    assert ui.fit("un texto demasiado largo para su caja", 80, 13).endswith("…")
    assert len(kit.fonts.wrap("uno dos tres cuatro cinco seis siete ocho nueve diez", 90, 13)) > 2
