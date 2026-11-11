"""Modo 2: simulación. Conducción manual y entrenamiento con varios agentes visibles."""
from __future__ import annotations

import math
import time
from pathlib import Path
from typing import Optional

import pygame

from bootstrap import (available_strategies, build_map_generator, build_simulation_factory,
                       build_training_session, load_training_session, save_training_session)
from control.manual_controller import ManualController
from optimization.training import IterationStats, TrainingLog, TrainingSession
from rendering.renderer import Viewport, WorldRenderer
from ui.training_panel import draw_training_stats
from ui.widgets import ACCENT, BACKGROUND, GOOD, MUTED, TEXT, WARN, Fonts, Panel, draw_text

PANEL_WIDTH = 330
SPEEDS = [1, 2, 4, 8, 16, 32]      # multiplicador del tiempo real para los agentes visibles
MAX_STEPS_PER_FRAME = 96
BACKGROUND_BUDGET = 0.010          # segundos por cuadro para evaluar candidatos no visibles
HEADER = 18


def keyboard_input():
    """(dirección, aceleración) según flechas o WASD."""
    keys = pygame.key.get_pressed()
    steering = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
    acceleration = (keys[pygame.K_UP] or keys[pygame.K_w]) - (keys[pygame.K_DOWN] or keys[pygame.K_s])
    return float(steering), float(acceleration)


class SimulationView:
    def __init__(self, config: dict, fonts: Fonts, renderer: WorldRenderer, editor_view, base_dir: Path) -> None:
        self.config = config
        self.fonts = fonts
        self.renderer = renderer
        self.editor_view = editor_view
        self.models_dir = Path(base_dir) / "models"
        self.log = TrainingLog(Path(base_dir) / "logs" / "entrenamiento_gui.jsonl")
        self.factory = build_simulation_factory(config)
        self.generator = build_map_generator(config)
        self.plugins = available_strategies()
        self.sub_mode = "manual"
        self.pilot = "manual"
        self.manual = ManualController()
        self.input_source = keyboard_input     # sustituible: cualquier función -> (dirección, aceleración)
        self.simulation = None
        self.session: Optional[TrainingSession] = None
        self.session_config: Optional[dict] = None
        self.running = False
        self.speed_index = 0
        self.use_editor_map = False
        self.message = ""
        self.panel: Optional[Panel] = None
        self._accumulator = 0.0
        self.layout(pygame.Rect(0, 0, 800, 600))

    def layout(self, area: pygame.Rect) -> None:
        self.canvas = pygame.Rect(area.x, area.y, max(50, area.width - PANEL_WIDTH), area.height)
        self.panel_rect = pygame.Rect(self.canvas.right, area.y, area.right - self.canvas.right, area.height)

    # --- simulación manual ---------------------------------------------------
    def enter(self) -> None:
        """Al entrar al modo: prepara la simulación con el mapa del editor."""
        self.reset_manual()

    def reset_manual(self, random_map: bool = False) -> None:
        editor_map = self.editor_view.editor.map
        if random_map or editor_map.validate():
            seed = int(time.time() * 1000) % 1_000_000
            map_data = self.generator.generate(seed)
            self.message = f"Mapa aleatorio (semilla {seed})."
            if not random_map:
                self.message += " El mapa del editor está incompleto."
        else:
            map_data = editor_map.copy()
            self.message = f"Mapa del editor: {map_data.name}."
        self._build_manual(map_data)

    def _build_manual(self, map_data) -> None:
        controller = self.manual
        if self.pilot == "policy":
            controller = self._policy_controller()
            if controller is None:
                self.pilot, controller = "manual", self.manual
        self.simulation = self.factory.create(map_data, [controller])
        self._accumulator = 0.0

    def _policy_controller(self):
        if self.session is None:
            checkpoint = self._latest_checkpoint()
            if checkpoint is not None:
                self.load_checkpoint(checkpoint)
        controller = self.session.best_controller() if self.session is not None else None
        if controller is None:
            self.message = "Todavía no hay una política entrenada: entrena al menos una generación."
        return controller

    def set_pilot(self, pilot: str) -> None:
        self.pilot = pilot
        if self.simulation is not None:
            self._build_manual(self.simulation.world.map)

    def set_sub_mode(self, sub_mode: str) -> None:
        self.sub_mode = sub_mode
        self._accumulator = 0.0
        if sub_mode == "manual" and self.simulation is None:
            self.reset_manual()

    # --- entrenamiento ------------------------------------------------------------
    def new_training(self) -> None:
        self.running = False
        self.session = None
        if not self.plugins:
            self.message = "No hay algoritmos de aprendizaje instalados en optimization/."
            return
        fixed = []
        if self.use_editor_map:
            editor_map = self.editor_view.editor.map
            if editor_map.validate():
                self.message = "El mapa del editor está incompleto: se entrena solo con mapas aleatorios."
            else:
                fixed = [editor_map.copy()]
        try:
            self.session = build_training_session(self.config, fixed)
        except ValueError as error:
            self.message = str(error)
            return
        self.session_config = self.config
        self.message = "Entrenamiento nuevo listo."

    def start_training(self) -> None:
        if self.session is None:
            self.new_training()
        self.running = self.session is not None

    def toggle_training(self) -> None:
        if self.session is None or not self.running:
            self.start_training()
        else:
            self.running = False

    def change_speed(self, delta: int) -> None:
        self.speed_index = min(max(self.speed_index + delta, 0), len(SPEEDS) - 1)

    def toggle_editor_map(self) -> None:
        self.use_editor_map = not self.use_editor_map
        self.message = "El cambio se aplica al iniciar un entrenamiento nuevo."

    def save_checkpoint(self, path: Optional[Path] = None) -> Optional[Path]:
        if self.session is None:
            self.message = "No hay entrenamiento para guardar."
            return None
        path = path or self.models_dir / f"checkpoint_gen{self.session.strategy.iteration:04d}.npz"
        saved = save_training_session(self.session, path, self.session_config)
        self.message = f"Checkpoint guardado: {saved.name}"
        return saved

    def _latest_checkpoint(self) -> Optional[Path]:
        files = sorted(self.models_dir.glob("*.npz"), key=lambda p: p.stat().st_mtime)
        return files[-1] if files else None

    def load_checkpoint(self, path: Optional[Path] = None) -> None:
        path = path or self._latest_checkpoint()
        if path is None:
            self.message = "No hay checkpoints en models/."
            return
        try:
            self.session, self.session_config = load_training_session(path)
        except (OSError, ValueError, KeyError) as error:
            self.message = f"No se pudo cargar {Path(path).name}: {error}"
            return
        self.running = False
        self.message = f"Checkpoint cargado: {Path(path).name} (generación {self.session.strategy.iteration})."

    def _on_iteration(self, stats: IterationStats) -> None:
        self.log.append(stats)
        every = self.session_config["training"].get("checkpoint_every", 0)
        if every and stats.iteration % every == 0:
            self.save_checkpoint(self.models_dir / "auto.npz")

    # --- ciclo ------------------------------------------------------------------------
    def handle_event(self, event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.panel is not None:
                self.panel.click(event.pos)
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_m:
                self.set_sub_mode("manual")
            elif event.key == pygame.K_t:
                self.set_sub_mode("training")
            elif self.sub_mode == "manual":
                if event.key == pygame.K_r and self.simulation is not None:
                    self.simulation.reset()
                elif event.key == pygame.K_n:
                    self.reset_manual(random_map=True)
                elif event.key == pygame.K_p:
                    self.set_pilot("manual" if self.pilot == "policy" else "policy")
            elif event.key == pygame.K_SPACE:
                self.toggle_training()
            elif event.key in (pygame.K_PLUS, pygame.K_KP_PLUS, pygame.K_EQUALS):
                self.change_speed(1)
            elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                self.change_speed(-1)

    def update(self, dt: float) -> None:
        """Avanza la simulación con paso fijo. Nunca bloquea: el entrenamiento se reparte por cuadros."""
        if self.sub_mode == "manual":
            if self.simulation is None:
                return
            self.manual.set_command(*self.input_source())
            self._accumulator += dt
            step = self.simulation.config.dt
            for _ in range(5):
                if self._accumulator < step:
                    break
                self.simulation.step()
                self._accumulator -= step
            else:
                self._accumulator = 0.0
        elif self.running and self.session is not None:
            step = self.session.evaluator.simulation_factory.config.dt
            self._accumulator += dt * SPEEDS[self.speed_index]
            steps = min(int(self._accumulator / step), MAX_STEPS_PER_FRAME)
            self._accumulator = 0.0 if steps == MAX_STEPS_PER_FRAME else self._accumulator - steps * step
            stats = self.session.advance(visible_steps=steps, time_budget=BACKGROUND_BUDGET)
            if stats is not None:
                self._on_iteration(stats)

    # --- dibujo -------------------------------------------------------------------------
    def draw(self, surface, mouse) -> None:
        panel = Panel(self.fonts, self.panel_rect, mouse)
        panel.begin(surface)
        panel.title("SIMULACIÓN")
        panel.buttons([("M Manual", lambda: self.set_sub_mode("manual"), self.sub_mode == "manual"),
                       ("T Entrenamiento", lambda: self.set_sub_mode("training"), self.sub_mode == "training")])
        if self.sub_mode == "manual":
            self._draw_manual(surface, panel)
        else:
            self._draw_training(surface, panel)
        panel.gap(4)
        panel.text(self.message, MUTED, 12)
        self.panel = panel

    @staticmethod
    def _map_key(prefix: str, map_data):
        return (prefix, id(map_data), map_data.name, map_data.seed)

    def _draw_manual(self, surface, panel: Panel) -> None:
        panel.buttons([("Piloto manual", lambda: self.set_pilot("manual"), self.pilot == "manual"),
                       ("P Mejor política", lambda: self.set_pilot("policy"), self.pilot == "policy")])
        simulation = self.simulation
        if simulation is None:
            return
        world_map = simulation.world.map
        viewport = Viewport(self.canvas, world_map.width, world_map.height, padding=14)
        self.renderer.draw_simulation(surface, viewport, simulation, self._map_key("manual", world_map))
        mobile = simulation.mobiles[0]
        nav = mobile.navigation
        mode = "seguimiento de ruta" if world_map.navigation_mode == "route" else "navegación libre"
        panel.gap(4)
        panel.text(f"Estado: {mobile.status.value}", GOOD if mobile.active else WARN)
        panel.text(f"Modo: {mode}")
        panel.text(f"Velocidad:   {mobile.state.speed:6.2f}")
        panel.text(f"Orientación: {math.degrees(mobile.state.heading):6.1f}°")
        panel.text(f"Tiempo:      {simulation.time:6.1f} s")
        panel.text(f"Distancia:   {mobile.distance_traveled:6.1f}")
        panel.text(f"Avance:      {nav.progress * 100:6.1f} %")
        panel.text(f"Desvío:      {nav.deviation:6.2f}")
        panel.text(f"LiDAR mín.:  {float(mobile.scan.min()) * mobile.sensor.max_range:6.2f}")
        panel.gap(4)
        panel.buttons([("R Reiniciar", simulation.reset), ("N Mapa aleatorio", lambda: self.reset_manual(True))])
        panel.text("Conduce con las flechas o WASD.", MUTED, 12)

    def _draw_training(self, surface, panel: Panel) -> None:
        session = self.session
        if not self.plugins:
            panel.text("No hay algoritmos de aprendizaje instalados (carpetas en optimization/).", WARN)
            return
        label = "Espacio: Pausar" if self.running else "Espacio: Iniciar"
        panel.buttons([(label, self.toggle_training, self.running), ("Nuevo", self.new_training)])
        panel.stepper("Velocidad", f"x{SPEEDS[self.speed_index]}",
                      lambda: self.change_speed(-1), lambda: self.change_speed(1))
        panel.buttons([("Guardar checkpoint", self.save_checkpoint, False, session is not None),
                       ("Cargar último", self.load_checkpoint)])
        panel.buttons([(f"Usar el mapa del editor: {'sí' if self.use_editor_map else 'no'}",
                        self.toggle_editor_map, self.use_editor_map)])
        panel.gap(4)
        if session is None:
            training = self.config["training"]
            panel.text(f"Población: {training['population_size']} individuos, "
                       f"{training['visible_agents']} visibles, "
                       f"{training['scenarios_per_candidate']} escenarios cada uno.", TEXT, 12)
            panel.text("Pulsa Espacio para comenzar.", MUTED)
            draw_text(surface, self.fonts, "Entrenamiento detenido", self.canvas.center, 16, MUTED, "center")
            return
        draw_training_stats(panel, session)
        self._draw_agents(surface, session)

    def _draw_agents(self, surface, session: TrainingSession) -> None:
        """Reparte el área en una grilla y dibuja un agente visible en cada celda."""
        runs = session.visible
        if not runs:
            draw_text(surface, self.fonts, "VISIBLE_AGENTS = 0: evaluación sin renderizado",
                      self.canvas.center, 14, MUTED, "center")
            return
        columns = math.ceil(math.sqrt(len(runs)))
        rows = math.ceil(len(runs) / columns)
        width, height = self.canvas.width // columns, self.canvas.height // rows
        for slot, run in enumerate(runs):
            cell = pygame.Rect(self.canvas.x + (slot % columns) * width,
                               self.canvas.y + (slot // columns) * height, width, height)
            if run is None:
                draw_text(surface, self.fonts, "sin candidato", cell.center, 12, MUTED, "center")
                continue
            simulation = run.simulation
            world_map = simulation.world.map
            body = pygame.Rect(cell.x, cell.y + HEADER, cell.width, cell.height - HEADER)
            viewport = Viewport(body, world_map.width, world_map.height, padding=5)
            self.renderer.draw_simulation(surface, viewport, simulation, self._map_key("agente", world_map))
            mobile = simulation.mobiles[0]
            status = "sin avance" if run.runner.stalled else mobile.status.value
            header = (f"Ind {run.candidate.id:2d}  ep {run.episode_index + 1}/{run.episode_count}  "
                      f"fit {run.partial_fitness:7.1f}  {status}")
            pygame.draw.rect(surface, BACKGROUND, (cell.x, cell.y, cell.width, HEADER))
            draw_text(surface, self.fonts, header, (cell.x + 8, cell.y + 3), 12,
                      ACCENT if not session.is_collected(run) else MUTED)
