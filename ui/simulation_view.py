"""Modo 2: simulación. Conducción manual, entrenamiento con agentes visibles y resultados."""
from __future__ import annotations

import math
import time
from pathlib import Path
from typing import List, Optional, Tuple

import pygame

from bootstrap import (available_strategies, build_map_generator, build_simulation_factory,
                       build_training_session, finish_run, load_training_session, save_training_session)
from config import deep_merge
from control.manual_controller import ManualController
from optimization.evaluation import EpisodeRunner, EvaluationSettings
from optimization.fitness import FitnessFunction, FitnessWeights
from optimization.results import RunRecord
from optimization.strategy import UnknownScenarioError
from optimization.training import IterationStats, TrainingLog, TrainingSession
from rendering.renderer import Viewport, WorldRenderer
from simulation.vehicle import Status
from ui.results_view import ResultsView
from ui.training_panel import draw_training_stats
from ui.widgets import ACCENT, BACKGROUND, GOOD, MUTED, TEXT, WARN, Fonts, Panel, draw_text

PANEL_WIDTH = 330
SPEEDS = [1, 2, 4, 8, 16, 32]      # multiplicador del tiempo real para los agentes visibles
MAX_STEPS_PER_FRAME = 96
BACKGROUND_BUDGET = 0.010          # segundos por cuadro para evaluar candidatos no visibles
LIMIT_STEP = 5                     # generaciones que suma o resta cada pulsación del límite
HEADER = 18
SUB_MODES = [("manual", "M Manual"), ("training", "T Entrenar"), ("results", "C Resultados")]


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
        self.logs_dir = Path(base_dir) / "logs"
        self.runs_dir = self.logs_dir / "runs"
        self.factory = build_simulation_factory(config)
        self.generator = build_map_generator(config)
        self.fitness = FitnessFunction(FitnessWeights.from_dict(config["fitness"]))
        self.plugins = available_strategies()
        self.strategy_names = sorted(self.plugins)
        configured = config["training"]["strategy"]
        self.selected_strategy: Optional[str] = (
            configured if configured in self.plugins else (self.strategy_names[0] if self.strategy_names else None)
        )
        self.iteration_limit = int(config["training"].get("max_iterations", 0))   # 0 = sin límite
        self.results = ResultsView(fonts, self.runs_dir, self.plugins)
        self.sub_mode = "manual"
        self.pilot = "manual"
        self.manual = ManualController()
        self.input_source = keyboard_input     # sustituible: cualquier función -> (dirección, aceleración)
        self.simulation = None
        self.episode: Optional[EpisodeRunner] = None
        self.episode_summary: Optional[List[Tuple[str, str]]] = None
        self.session: Optional[TrainingSession] = None
        self.session_config: Optional[dict] = None
        self.run_id: Optional[str] = None
        self.log: Optional[TrainingLog] = None
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

    def set_sub_mode(self, sub_mode: str) -> None:
        self.sub_mode = sub_mode
        self._accumulator = 0.0
        if sub_mode == "manual" and self.simulation is None:
            self.reset_manual()
        elif sub_mode == "results":
            self.results.refresh()

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

    def restart_manual(self) -> None:
        """Repite el episodio en el mismo mapa."""
        if self.simulation is not None:
            self._build_manual(self.simulation.world.map)

    def _build_manual(self, map_data) -> None:
        controller = self.manual
        if self.pilot == "policy":
            controller, map_data = self._policy_controller(map_data)
            if controller is None:
                self.pilot, controller = "manual", self.manual
        self.simulation = self.factory.create(map_data, [controller])
        # El episodio manual nunca se corta por falta de avance: el conductor decide.
        self.episode = EpisodeRunner(self.simulation, EvaluationSettings(stall_time=math.inf))
        self.episode_summary = None
        self._accumulator = 0.0

    def _policy_controller(self, map_data):
        """(controlador, mapa) para conducir con lo aprendido; ``(None, mapa)`` si todavía no hay nada.

        Si el algoritmo solo sabe conducir sus mapas de entrenamiento, se pasa al primero de ellos.
        """
        if self.session is None:
            checkpoint = self._latest_checkpoint()
            if checkpoint is not None:
                self.load_checkpoint(checkpoint)
        if self.session is None or self.session.best_solution is None:
            self.message = "Todavía no hay nada aprendido: entrena al menos una generación."
            return None, map_data
        try:
            return self.session.best_controller(map_data), map_data
        except UnknownScenarioError:
            for trained in self.session.training_maps():
                try:
                    controller = self.session.best_controller(trained)
                except UnknownScenarioError:
                    continue
                self.message = ("Este algoritmo solo conoce sus mapas de entrenamiento: "
                                f"se muestra '{trained.name}'.")
                return controller, trained
            self.message = "La mejor solución no tiene una ruta para ningún mapa de entrenamiento."
            return None, map_data

    def set_pilot(self, pilot: str) -> None:
        self.pilot = pilot
        if self.simulation is not None:
            self._build_manual(self.simulation.world.map)

    def _summarize_episode(self) -> List[Tuple[str, str]]:
        metrics = self.episode.metrics()
        mobile = self.simulation.mobiles[0]
        speed = metrics.distance / metrics.time if metrics.time > 0 else 0.0
        return [
            ("Resultado", mobile.status.value),
            ("Tiempo", f"{metrics.time:.1f} s"),
            ("Distancia", f"{metrics.distance:.1f}"),
            ("Velocidad media", f"{speed:.2f}"),
            ("Avance", f"{metrics.progress * 100:.0f} %"),
            ("Desvío medio", f"{metrics.mean_deviation:.2f}"),
            ("Cambio de dirección", f"{metrics.steering_change:.3f}"),
            ("Fitness", f"{self.fitness(metrics):.1f}"),
        ]

    # --- entrenamiento ------------------------------------------------------------
    def select_strategy(self, name: str) -> None:
        if name in self.plugins:
            self.selected_strategy = name
            self.message = self.plugins[name].description

    def cycle_strategy(self, delta: int) -> None:
        if self.strategy_names:
            index = self.strategy_names.index(self.selected_strategy) + delta
            self.select_strategy(self.strategy_names[index % len(self.strategy_names)])

    def set_iteration_limit(self, limit: int) -> None:
        self.iteration_limit = max(0, int(limit))
        if self.session is not None:
            self.session.max_iterations = self.iteration_limit

    def _new_run_id(self, strategy: str) -> str:
        base = f"{time.strftime('%Y%m%d-%H%M%S')}-{strategy}"
        run_id, attempt = base, 1
        while run_id == self.run_id or (self.runs_dir / f"{run_id}.json").exists():
            attempt += 1
            run_id = f"{base}-{attempt}"
        return run_id

    def _adopt_session(self, session: TrainingSession, config: dict) -> None:
        self.session, self.session_config = session, config
        self.run_id = self._new_run_id(session.strategy.name)
        self.log = TrainingLog(self.logs_dir / f"{self.run_id}.jsonl")
        self.running = False

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
        config = deep_merge(self.config, {"training": {"strategy": self.selected_strategy,
                                                       "max_iterations": self.iteration_limit}})
        try:
            session = build_training_session(config, fixed)
        except ValueError as error:
            self.message = str(error)
            return
        self._adopt_session(session, config)
        self.message = f"Entrenamiento nuevo con {self.plugins[self.selected_strategy].short_label}."

    def start_training(self) -> None:
        if self.session is None:
            self.new_training()
        if self.session is None:
            return
        if self.session.finished:      # ya se había llegado al límite: continuar suma otro tramo
            self.session.max_iterations = (
                self.session.strategy.iteration + self.iteration_limit if self.iteration_limit else 0
            )
        self.running = True

    def toggle_training(self) -> None:
        if self.session is None or not self.running:
            self.start_training()
        else:
            self.running = False

    def finish_training(self) -> Optional[RunRecord]:
        """Da por terminada la corrida: guarda su registro y muestra sus estadísticas."""
        if self.session is None:
            self.message = "No hay entrenamiento que finalizar."
            return None
        record = finish_run(self.session, self.session_config, self.runs_dir, self.run_id)
        if record is None:
            self.message = "Todavía no terminó ninguna generación."
            return None
        self.running = False
        self.results.show(record.run_id)
        self.sub_mode = "results"
        self.message = f"Corrida finalizada tras {record.metrics()['iterations']} generaciones."
        return record

    def change_speed(self, delta: int) -> None:
        self.speed_index = min(max(self.speed_index + delta, 0), len(SPEEDS) - 1)

    def toggle_editor_map(self) -> None:
        self.use_editor_map = not self.use_editor_map
        self.message = "El cambio se aplica al pulsar Nuevo."

    def save_checkpoint(self, path: Optional[Path] = None) -> Optional[Path]:
        if self.session is None:
            self.message = "No hay entrenamiento para guardar."
            return None
        name = f"checkpoint_{self.session.strategy.name}_gen{self.session.strategy.iteration:04d}.npz"
        saved = save_training_session(self.session, path or self.models_dir / name, self.session_config)
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
            session, config = load_training_session(path)
        except (OSError, ValueError, KeyError) as error:
            self.message = f"No se pudo cargar {Path(path).name}: {error}"
            return
        self._adopt_session(session, config)
        self.selected_strategy = session.strategy.name
        self.iteration_limit = session.max_iterations
        self.message = f"Checkpoint cargado: {Path(path).name} (generación {session.strategy.iteration})."

    def _on_iteration(self, stats: IterationStats) -> None:
        self.log.append(stats)
        every = self.session_config["training"].get("checkpoint_every", 0)
        if every and stats.iteration % every == 0:
            self.save_checkpoint(self.models_dir / f"auto_{self.session.strategy.name}.npz")
        if self.session.finished:
            self.finish_training()

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
            elif event.key == pygame.K_c:
                self.set_sub_mode("results")
            elif self.sub_mode == "manual":
                if event.key == pygame.K_r:
                    self.restart_manual()
                elif event.key == pygame.K_n:
                    self.reset_manual(random_map=True)
                elif event.key == pygame.K_p:
                    self.set_pilot("manual" if self.pilot == "policy" else "policy")
            elif self.sub_mode == "training":
                if event.key == pygame.K_SPACE:
                    self.toggle_training()
                elif event.key == pygame.K_f:
                    self.finish_training()
                elif event.key in (pygame.K_PLUS, pygame.K_KP_PLUS, pygame.K_EQUALS):
                    self.change_speed(1)
                elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    self.change_speed(-1)

    def update(self, dt: float) -> None:
        """Avanza la simulación con paso fijo. Nunca bloquea: el entrenamiento se reparte por cuadros."""
        if self.sub_mode == "manual":
            if self.episode is None:
                return
            self.manual.set_command(*self.input_source())
            self._accumulator += dt
            step = self.simulation.config.dt
            for _ in range(5):
                if self._accumulator < step:
                    break
                self.episode.step()
                self._accumulator -= step
            else:
                self._accumulator = 0.0
            if self.episode.done and self.episode_summary is None:
                self.episode_summary = self._summarize_episode()
        elif self.sub_mode == "training" and self.running and self.session is not None:
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
        panel.buttons([(label, lambda m=mode: self.set_sub_mode(m), self.sub_mode == mode)
                       for mode, label in SUB_MODES])
        if self.sub_mode == "manual":
            self._draw_manual(surface, panel)
        elif self.sub_mode == "training":
            self._draw_training(surface, panel)
        else:
            self.results.build_panel(panel)
            self.results.draw(surface, self.canvas)
        panel.gap(4)
        panel.text(self.message, MUTED, 12)
        self.panel = panel

    @staticmethod
    def _map_key(prefix: str, map_data):
        return (prefix, id(map_data), map_data.name, map_data.seed)

    def _draw_manual(self, surface, panel: Panel) -> None:
        panel.buttons([("Piloto manual", lambda: self.set_pilot("manual"), self.pilot == "manual"),
                       ("P Lo aprendido", lambda: self.set_pilot("policy"), self.pilot == "policy")])
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
        fine = mobile.status in (Status.ACTIVE, Status.REACHED_GOAL)
        panel.text(f"Estado: {mobile.status.value}", GOOD if fine else WARN)
        panel.text(f"Modo: {mode}")
        panel.text(f"Velocidad:   {mobile.state.speed:6.2f}")
        panel.text(f"Orientación: {math.degrees(mobile.state.heading):6.1f}°")
        panel.text(f"Tiempo:      {simulation.time:6.1f} s")
        panel.text(f"Distancia:   {mobile.distance_traveled:6.1f}")
        panel.text(f"Avance:      {nav.progress * 100:6.1f} %")
        panel.text(f"Desvío:      {nav.deviation:6.2f}")
        panel.text(f"LiDAR mín.:  {float(mobile.scan.min()) * mobile.sensor.max_range:6.2f}")
        panel.gap(4)
        panel.buttons([("R Reiniciar", self.restart_manual), ("N Mapa aleatorio", lambda: self.reset_manual(True))])
        if self.episode_summary is not None:
            panel.gap(4)
            panel.text("Resumen del episodio", ACCENT)
            for label, value in self.episode_summary:
                panel.text(f"{label + ':':<21}{value}", TEXT, 12)
        else:
            panel.text("Conduce con las flechas o WASD.", MUTED, 12)

    def _draw_training(self, surface, panel: Panel) -> None:
        session = self.session
        if not self.plugins:
            panel.text("No hay algoritmos de aprendizaje instalados (carpetas en optimization/).", WARN)
            return
        chosen = self.plugins[self.selected_strategy]
        panel.stepper("Algoritmo", chosen.short_label, lambda: self.cycle_strategy(-1),
                      lambda: self.cycle_strategy(1), "<", ">")
        panel.buttons([("Pausar" if self.running else "Iniciar", self.toggle_training, self.running),
                       ("Nuevo", self.new_training),
                       ("F Finalizar", self.finish_training, False, session is not None and bool(session.history))])
        panel.stepper("Velocidad", f"x{SPEEDS[self.speed_index]}",
                      lambda: self.change_speed(-1), lambda: self.change_speed(1))
        limit = f"{self.iteration_limit} gen." if self.iteration_limit else "sin límite"
        panel.stepper("Límite", limit, lambda: self.set_iteration_limit(self.iteration_limit - LIMIT_STEP),
                      lambda: self.set_iteration_limit(self.iteration_limit + LIMIT_STEP))
        panel.buttons([("Guardar checkpoint", self.save_checkpoint, False, session is not None),
                       ("Cargar último", self.load_checkpoint)])
        panel.buttons([(f"Usar el mapa del editor: {'sí' if self.use_editor_map else 'no'}",
                        self.toggle_editor_map, self.use_editor_map)])
        panel.gap(4)
        if session is None:
            training = self.config["training"]
            panel.text(chosen.label, ACCENT, 12)
            panel.text(chosen.description, TEXT, 12)
            panel.gap(4)
            panel.text(f"Población: {training['population_size']} individuos, "
                       f"{training['visible_agents']} visibles, "
                       f"{training['scenarios_per_candidate']} mapas cada uno.", TEXT, 12)
            panel.text("Espacio o Iniciar para comenzar.", MUTED)
            draw_text(surface, self.fonts, "Entrenamiento detenido", self.canvas.center, 16, MUTED, "center")
            return
        if session.strategy.name != self.selected_strategy:
            panel.text(f"Pulsa Nuevo para entrenar con {chosen.short_label}.", WARN, 12)
        draw_training_stats(panel, session, self.plugins.get(session.strategy.name))
        self._draw_agents(surface, session)

    def _draw_agents(self, surface, session: TrainingSession) -> None:
        """Reparte el área en una grilla y dibuja un agente visible en cada celda."""
        runs = session.visible
        if not runs:
            text = "Pulsa Iniciar" if not session.history and not self.running else "Evaluación sin renderizado"
            draw_text(surface, self.fonts, text, self.canvas.center, 14, MUTED, "center")
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
            self.renderer.draw_simulation(
                surface, viewport, simulation, self._map_key("agente", world_map),
                heatmap=session.strategy.cell_heatmap(run.scenario),
                heat_key=(run.scenario.key, session.strategy.iteration),
            )
            mobile = simulation.mobiles[0]
            status = "sin avance" if run.runner.stalled else mobile.status.value
            header = (f"Ind {run.candidate.id:2d}  ep {run.episode_index + 1}/{run.episode_count}  "
                      f"fit {run.partial_fitness:7.1f}  {status}")
            pygame.draw.rect(surface, BACKGROUND, (cell.x, cell.y, cell.width, HEADER))
            draw_text(surface, self.fonts, header, (cell.x + 8, cell.y + 3), 12,
                      ACCENT if not session.is_collected(run) else MUTED)
