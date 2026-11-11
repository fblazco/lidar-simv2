"""Ventana única de la aplicación: modo Editor y modo Simulación."""
from __future__ import annotations

from pathlib import Path

import pygame

from bootstrap import build_map_generator
from editor.map_manager import MapManager
from rendering.renderer import WorldRenderer
from ui.editor_view import EditorView
from ui.simulation_view import SimulationView
from ui.widgets import ACCENT, BACKGROUND, BORDER, BUTTON, BUTTON_ACTIVE, MUTED, PANEL_BG, TEXT, Fonts, draw_text

TOP_BAR = 40
MODES = [("editor", "F1 Editor de mapas"), ("simulation", "F2 Simulación")]
MODE_KEYS = {pygame.K_F1: "editor", pygame.K_F2: "simulation"}


class Application:
    def __init__(self, config: dict, base_dir=".") -> None:
        pygame.init()
        window = config["window"]
        pygame.display.set_caption("Simulador LiDAR - navegación con algoritmos evolutivos")
        self.screen = pygame.display.set_mode((window["width"], window["height"]), pygame.RESIZABLE)
        self.fps = window["fps"]
        self.clock = pygame.time.Clock()
        self.fonts = Fonts()
        self.renderer = WorldRenderer(self.fonts)
        base = Path(base_dir)
        self.editor_view = EditorView(config, self.fonts, self.renderer, MapManager(base / "maps"),
                                      build_map_generator(config))
        self.simulation_view = SimulationView(config, self.fonts, self.renderer, self.editor_view, base)
        self.mode = "editor"
        self.running = True
        self._tabs = []
        self._layout()

    @property
    def view(self):
        return self.editor_view if self.mode == "editor" else self.simulation_view

    def set_mode(self, mode: str) -> None:
        if mode == self.mode:
            return
        self.mode = mode
        if mode == "simulation":
            self.simulation_view.enter()

    def _layout(self) -> None:
        self.screen = pygame.display.get_surface()
        width, height = self.screen.get_size()
        area = pygame.Rect(0, TOP_BAR, width, height - TOP_BAR)
        self.editor_view.layout(area)
        self.simulation_view.layout(area)
        self._tabs = [(pygame.Rect(10 + i * 210, 6, 200, TOP_BAR - 12), mode, label)
                      for i, (mode, label) in enumerate(MODES)]

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
                for rect, mode, _ in self._tabs:
                    if rect.collidepoint(event.pos):
                        self.set_mode(mode)
            else:
                self.view.handle_event(event)

    def _draw(self) -> None:
        self.screen.fill(BACKGROUND)
        self.view.draw(self.screen, pygame.mouse.get_pos())
        pygame.draw.rect(self.screen, PANEL_BG, (0, 0, self.screen.get_width(), TOP_BAR))
        pygame.draw.line(self.screen, BORDER, (0, TOP_BAR - 1), (self.screen.get_width(), TOP_BAR - 1))
        for rect, mode, label in self._tabs:
            active = mode == self.mode
            pygame.draw.rect(self.screen, BUTTON_ACTIVE if active else BUTTON, rect, border_radius=4)
            draw_text(self.screen, self.fonts, label, rect.center, 13, TEXT if active else MUTED, "center")
        draw_text(self.screen, self.fonts, f"{self.clock.get_fps():3.0f} fps",
                  (self.screen.get_width() - 12, TOP_BAR // 2), 12, ACCENT, "midright")
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
