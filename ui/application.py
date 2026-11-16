"""Ventana única de la aplicación: barra superior con las cuatro secciones y el cambio de tema."""
from __future__ import annotations

from pathlib import Path

import pygame

from bootstrap import build_map_generator
from editor.map_manager import MapManager
from rendering.renderer import WorldRenderer
from rendering.scene import SceneRenderer
from ui.editor_view import EditorView
from ui.simulation_view import SimulationView
from ui.theme import DEFAULT_THEME, other_theme
from ui.widgets import Toolkit, Ui

BAR = 64                  # barra superior
CHROME = 3                # franja metálica bajo la barra
TOP_BAR = BAR + CHROME
# (sección, etiqueta, ícono). "editor" es un modo propio; las demás son vistas de la simulación.
TABS = [("editor", "Editor de mapas", "edit"), ("manual", "Conducir", "drive"),
        ("training", "Entrenar", "train"), ("results", "Resultados", "results")]
MODE_KEYS = {pygame.K_F1: "editor", pygame.K_F2: "simulation"}


class Application:
    def __init__(self, config: dict, base_dir=".") -> None:
        pygame.init()
        window = config["window"]
        pygame.display.set_caption("Simulador LiDAR - navegación con algoritmos evolutivos")
        self.screen = pygame.display.set_mode((window["width"], window["height"]), pygame.RESIZABLE)
        self.fps = window["fps"]
        self.clock = pygame.time.Clock()
        self.kit = Toolkit(window.get("theme", DEFAULT_THEME))
        self.fonts = self.kit.fonts
        self.renderer = WorldRenderer(self.fonts, self.kit.theme.world)
        self.scenes = SceneRenderer(self.renderer)
        base = Path(base_dir)
        self.editor_view = EditorView(config, self.kit, self.renderer, MapManager(base / "maps"),
                                      build_map_generator(config))
        self.simulation_view = SimulationView(config, self.kit, self.renderer, self.scenes, self.editor_view, base)
        self.mode = "editor"
        self.running = True
        self.ui: Ui = self.kit.frame(self.screen, (0, 0))
        self._chrome = {}
        self._layout()

    @property
    def view(self):
        return self.editor_view if self.mode == "editor" else self.simulation_view

    @property
    def tab(self) -> str:
        """Sección que se está viendo: 'editor', 'manual', 'training' o 'results'."""
        return "editor" if self.mode == "editor" else self.simulation_view.sub_mode

    def set_mode(self, mode: str) -> None:
        if mode == self.mode:
            return
        self.mode = mode
        if mode == "simulation":
            self.simulation_view.enter()

    def open_tab(self, tab: str) -> None:
        if tab == "editor":
            self.set_mode("editor")
        else:
            self.set_mode("simulation")
            self.simulation_view.set_sub_mode(tab)

    # --- tema -----------------------------------------------------------------
    @property
    def theme(self):
        return self.kit.theme

    def set_theme(self, name: str) -> None:
        self.kit.set_theme(name)
        self.renderer.set_palette(self.kit.theme.world)

    def toggle_theme(self) -> None:
        self.set_theme(other_theme(self.kit.theme).name)

    def _layout(self) -> None:
        self.screen = pygame.display.get_surface()
        width, height = self.screen.get_size()
        area = pygame.Rect(0, TOP_BAR, width, height - TOP_BAR)
        self.editor_view.layout(area)
        self.simulation_view.layout(area)

    # --- ciclo principal ------------------------------------------------------
    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type in (pygame.VIDEORESIZE, pygame.WINDOWSIZECHANGED):
                self._layout()
            elif event.type == pygame.KEYDOWN and event.key in MODE_KEYS:
                self.set_mode(MODE_KEYS[event.key])
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and event.pos[1] < TOP_BAR:
                self.ui.click(event.pos)
            else:
                self.view.handle_event(event)

    def _chrome_strip(self, width: int) -> pygame.Surface:
        """Franja metálica: un degradado horizontal entre los tonos del tema."""
        key = (width, self.theme.name)
        strip = self._chrome.get(key)
        if strip is None:
            stops = self.theme.chrome
            strip = pygame.Surface((width, CHROME))
            spans = len(stops) - 1
            for x in range(width):
                position = x / max(width - 1, 1) * spans
                index = min(int(position), spans - 1)
                t = position - index
                color = [int(stops[index][i] + (stops[index + 1][i] - stops[index][i]) * t) for i in range(3)]
                strip.fill(color, (x, 0, 1, CHROME))
            self._chrome = {key: strip}
        return strip

    def _draw_bar(self, ui: Ui) -> None:
        theme, width = ui.theme, self.screen.get_width()
        compact = width < 1150
        pad = 20 if compact else 32
        self.screen.fill(theme.background, (0, 0, width, BAR))
        self.screen.blit(self._chrome_strip(width), (0, BAR))
        # marca
        mark = pygame.Rect(pad, (BAR - 32) // 2, 32, 32)
        self.kit.shapes.rounded(self.screen, mark, 16, None, theme.text, 2)
        ui.text("o", (mark.centerx, mark.centery - 1), 15, face="mono", anchor="center")
        x = mark.right + 11
        if not compact:
            x = ui.text("Simulador LiDAR", (x, BAR // 2), 18, face="bold", anchor="midleft").right
        # secciones
        x += 20 if compact else 36
        for tab, label, icon in TABS:
            active = tab == self.tab
            color = theme.text if active else theme.muted
            text_width = self.fonts.width(label, 15, "bold" if active else "sans")
            rect = pygame.Rect(x, 0, text_width + 18 + 8 + 28, BAR)
            ui.icon(icon, (rect.x + 14 + 9, BAR // 2), 18, color)
            ui.text(label, (rect.x + 14 + 26, BAR // 2), 15, color, "bold" if active else "sans", "midleft")
            if active:
                self.screen.fill(theme.text, (rect.x, BAR - 3, rect.width, 3))
            ui.hit(rect, lambda t=tab: self.open_tab(t))
            x = rect.right + 4
        # cambio de tema y cuadros por segundo
        right = width - pad
        right = ui.text(f"{self.clock.get_fps():3.0f} fps", (right, BAR // 2), 12, theme.muted, "mono", "midright").x - 14
        other = other_theme(theme)
        label = other.label
        toggle = pygame.Rect(0, 0, self.fonts.width(label, 13) + 46, 32)
        toggle.midright = (right, BAR // 2)
        ui.button(toggle, label, self.toggle_theme, "control", icon="moon" if other.name == "dark" else "sun", size=13)

    def _draw(self) -> None:
        mouse = pygame.mouse.get_pos()
        self.screen.fill(self.theme.background)
        self.view.draw(self.screen, mouse)
        self.ui = self.kit.frame(self.screen, mouse)
        self._draw_bar(self.ui)
        pygame.display.flip()

    def _frame(self, dt: float) -> None:
        self._handle_events()
        self.view.update(dt)
        self._draw()

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(self.fps) / 1000.0
            self._frame(min(dt, 0.1))
        self.close()

    def run_frames(self, count: int) -> None:
        """Procesa ``count`` cuadros sin esperar al reloj (para pruebas y capturas)."""
        for _ in range(count):
            self._frame(1.0 / self.fps)

    def close(self) -> None:
        pygame.quit()
