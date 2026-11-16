"""Modo 2: simulación. Conducción manual, entrenamiento con agentes visibles y resultados."""
from __future__ import annotations

import math
import time
from pathlib import Path
from typing import List, Optional, Tuple

import pygame

from bootstrap import (available_avoidance, available_strategies, build_map_generator, build_simulation_factory,
                       build_training_session, finish_run, load_training_session, save_training_session)
from config import deep_merge
from control.manual_controller import ManualController
from optimization.evaluation import EpisodeRunner, EvaluationSettings, Scenario
from optimization.fitness import FitnessFunction, FitnessWeights
from optimization.results import RunRecord
from optimization.strategy import UnknownScenarioError
from optimization.training import IterationStats, TrainingLog, TrainingSession
from rendering.renderer import Viewport, WorldRenderer
from rendering.scene import SceneRenderer
from simulation.vehicle import Status
from ui.results_view import ResultsView
from ui.training_panel import draw_generation_stats, draw_legend, draw_line_chart, draw_validation
from ui.widgets import Toolkit, Ui

SPEEDS = [1, 2, 4, 8, 16, 32]      # multiplicador del tiempo real para los agentes visibles
MAX_STEPS_PER_FRAME = 96
BACKGROUND_BUDGET = 0.010          # segundos por cuadro para evaluar candidatos no visibles
LIMIT_STEP = 5                     # generaciones que suma o resta cada pulsación del límite
TRAIL_STEP = 0.15                  # distancia entre dos puntos guardados del camino recorrido
HEADER, FOOTER = 50, 42            # franjas de la tarjeta del mapa al conducir
AGENT_HEADER = 34
SECTION = 30                       # alto del título de cada fila de opciones
OPTION_TEXT = 86                   # alto del texto de una tarjeta de algoritmo
SUB_MODES = [("manual", "Conducir"), ("training", "Entrenar"), ("results", "Resultados")]
MAP_MODE_LABELS = {"free": "libres", "route": "con ruta", "mixed": "mixtos"}
MAP_MODES = [("free", "Libres"), ("route", "Con ruta"), ("mixed", "Mixtos")]
PILOTS = [("manual", "Manual"), ("policy", "Lo aprendido")]
STATUS_TEXT = {Status.ACTIVE: "En camino", Status.REACHED_GOAL: "Llegó al destino", Status.COLLIDED: "Chocó",
               Status.TIMED_OUT: "Se acabó el tiempo"}


def keyboard_input():
    """(dirección, aceleración) según flechas o WASD."""
    keys = pygame.key.get_pressed()
    steering = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
    acceleration = (keys[pygame.K_UP] or keys[pygame.K_w]) - (keys[pygame.K_DOWN] or keys[pygame.K_s])
    return float(steering), float(acceleration)


class SimulationView:
    def __init__(self, config: dict, kit: Toolkit, renderer: WorldRenderer, scenes: SceneRenderer, editor_view,
                 base_dir: Path) -> None:
        self.config = config
        self.kit = kit
        self.fonts = kit.fonts
        self.scenes = scenes
        self.renderer = renderer
        self.editor_view = editor_view
        self.models_dir = Path(base_dir) / "models"
        self.logs_dir = Path(base_dir) / "logs"
        self.runs_dir = self.logs_dir / "runs"
        self.factory = build_simulation_factory(config)
        self.fitness = FitnessFunction(FitnessWeights.from_dict(config["fitness"]))
        self.plugins = available_strategies()
        self.strategy_names = sorted(self.plugins)
        configured = config["training"]["strategy"]
        self.selected_strategy: Optional[str] = (
            configured if configured in self.plugins else (self.strategy_names[0] if self.strategy_names else None)
        )
        self.avoiders = available_avoidance()
        self.avoidance_names = list(self.avoiders)
        self.selected_avoidance = config["training"].get("avoidance", self.avoidance_names[0])
        self.map_modes = list(MAP_MODE_LABELS)
        self.selected_map_mode = config["generator"]["navigation_mode"]
        self.iteration_limit = int(config["training"].get("max_iterations", 0))   # 0 = sin límite
        self.results = ResultsView(kit, self.runs_dir, self.plugins, self.avoiders)
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
        self.ui: Optional[Ui] = None
        self.focus = 0                     # agente visible que ocupa la pantalla grande
        self._trail: List[Tuple[float, float]] = []      # camino recorrido al conducir
        self._trails = {}                  # camino de cada agente visible del entrenamiento
        self._accumulator = 0.0
        self.layout(pygame.Rect(0, 0, 800, 600))

    def layout(self, area: pygame.Rect) -> None:
        self.area = pygame.Rect(area)
        self.compact = area.width < 1150
        pad = 20 if self.compact else 32
        self.inner = pygame.Rect(area.x + pad, area.y + 18, max(200, area.width - 2 * pad), max(200, area.height - 36))

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
            generator = build_map_generator(deep_merge(
                self.config, {"generator": {"navigation_mode": self.selected_map_mode}}))
            map_data = generator.generate(seed)
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
        self.episode = EpisodeRunner(self.simulation, EvaluationSettings(stall_time=math.inf),
                                     Scenario(map_data).reference_length)
        self.episode_summary = None
        self._accumulator = 0.0
        self._trail = []

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

    def select_avoidance(self, name: str) -> None:
        if name in self.avoiders:
            self.selected_avoidance = name
            self.message = self.avoiders[name].description

    def cycle_avoidance(self, delta: int) -> None:
        index = self.avoidance_names.index(self.selected_avoidance) + delta
        self.select_avoidance(self.avoidance_names[index % len(self.avoidance_names)])

    def select_map_mode(self, mode: str) -> None:
        if mode in MAP_MODE_LABELS:
            self.selected_map_mode = mode
            self.message = f"Mapas aleatorios {MAP_MODE_LABELS[mode]}."

    def cycle_map_mode(self, delta: int) -> None:
        index = self.map_modes.index(self.selected_map_mode) + delta
        self.select_map_mode(self.map_modes[index % len(self.map_modes)])

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
        config = deep_merge(self.config, {
            "training": {"strategy": self.selected_strategy, "avoidance": self.selected_avoidance,
                         "max_iterations": self.iteration_limit},
            "generator": {"navigation_mode": self.selected_map_mode},
        })
        try:
            session = build_training_session(config, fixed)
        except ValueError as error:
            self.message = str(error)
            return
        self._adopt_session(session, config)
        self.message = (f"Entrenamiento nuevo: {self.plugins[self.selected_strategy].short_label}, "
                        f"evasión {self.avoiders[self.selected_avoidance].short_label}.")

    def reset_training(self) -> None:
        """Descarta la corrida en curso y vuelve a la pantalla de preparación."""
        self.running = False
        self.session = None
        self.focus = 0
        self.message = "Elige una combinación y pulsa Empezar entrenamiento."

    def set_focus(self, index: int) -> None:
        """Elige qué agente visible ocupa la pantalla grande."""
        self.focus = max(0, int(index))

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
        self.message = "Se aplica a la próxima corrida."

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
        self.selected_avoidance = session.avoidance
        self.selected_map_mode = config["generator"]["navigation_mode"]
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
            if self.ui is not None:
                self.ui.click(event.pos)
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
            state = self.simulation.mobiles[0].state
            if not self._trail or math.hypot(state.x - self._trail[-1][0], state.y - self._trail[-1][1]) >= TRAIL_STEP:
                self._trail.append((state.x, state.y))
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
        ui = self.kit.frame(surface, mouse)
        if self.sub_mode == "manual":
            self._draw_manual(ui)
        elif self.sub_mode == "training":
            if self.session is None:
                self._draw_setup(ui)
            else:
                self._draw_training(ui)
        else:
            self.results.draw(ui, self.inner)
        if self.message:
            ui.text(ui.fit(self.message, self.inner.width, 12), (self.inner.x, self.area.bottom - 9), 12,
                    ui.theme.muted, anchor="midleft")
        self.ui = ui

    @staticmethod
    def _map_key(prefix: str, map_data):
        return (prefix, id(map_data), map_data.name, map_data.seed)

    def _world(self, ui: Ui, rect: pygame.Rect, simulation, key, **layers) -> None:
        """El simulador dentro de ``rect``, centrado y sin deformar."""
        surface, world_map = ui.surface, simulation.world.map
        surface.fill(ui.theme.world.background, rect)
        clip = surface.get_clip()
        surface.set_clip(rect.clip(clip))
        self.renderer.draw_simulation(surface, Viewport(rect, world_map.width, world_map.height, padding=0),
                                      simulation, key, **layers)
        surface.set_clip(clip)

    def _trail_of(self, simulation) -> List[Tuple[float, float]]:
        """Camino recorrido por el vehículo de un agente visible; se reinicia con cada episodio."""
        state = simulation.mobiles[0].state
        entry = self._trails.get(id(simulation))
        if entry is None or entry[0] is not simulation or simulation.steps < entry[1]:
            entry = [simulation, simulation.steps, [(state.x, state.y)]]
            self._trails[id(simulation)] = entry
        elif math.hypot(state.x - entry[2][-1][0], state.y - entry[2][-1][1]) >= TRAIL_STEP:
            entry[2].append((state.x, state.y))
        entry[1] = simulation.steps
        return entry[2]

    # --- conducir ---------------------------------------------------------------------
    def _draw_manual(self, ui: Ui) -> None:
        theme, inner, surface = ui.theme, self.inner, ui.surface
        panel_width = 270 if self.compact else 300
        panel = pygame.Rect(inner.right - panel_width, inner.y, panel_width, inner.height)
        slot = pygame.Rect(inner.x, inner.y, inner.width - panel_width - 16, inner.height)
        simulation = self.simulation
        if simulation is None:
            ui.card(slot)
            ui.card(panel)
            ui.text("Sin simulación", slot.center, 15, theme.muted, anchor="center")
            return
        world_map = simulation.world.map
        ideal = int((slot.width - 2) * world_map.height / world_map.width) + HEADER + FOOTER + 2
        card = pygame.Rect(slot.x, slot.y, slot.width, max(HEADER + FOOTER + 60, min(slot.height, ideal)))
        canvas = pygame.Rect(card.x + 1, card.y + HEADER, card.width - 2, card.height - HEADER - FOOTER)
        ui.card(card)
        self._world(ui, canvas, simulation, self._map_key("manual", world_map), trail=self._trail)
        ui.divider(card.x + 1, canvas.y - 1, card.width - 2)
        ui.divider(card.x + 1, canvas.bottom, card.width - 2)
        mobile = simulation.mobiles[0]
        # cabecera: quién conduce
        middle = card.y + HEADER // 2
        label = ui.text("Piloto", (card.x + 14, middle), 12, theme.muted, anchor="midleft")
        segment = 112 if card.width >= 620 else 92
        pilots = pygame.Rect(label.right + 10, middle - 17, 2 * segment + 6, 34)
        ui.segmented(pilots, PILOTS, self.pilot, self.set_pilot)
        mode = "sigue la ruta" if world_map.navigation_mode == "route" else "navegación libre"
        room = card.right - 14 - pilots.right - 16
        if room > 90:
            ui.text(ui.fit(f"{world_map.name} · {mode}", room, 12), (card.right - 14, middle), 12, theme.muted,
                    anchor="midright")
        # pie: estado del episodio
        middle = canvas.bottom + FOOTER // 2
        pygame.draw.circle(surface, theme.text, (card.x + 20, middle), 4, 0 if mobile.status is Status.ACTIVE else 1)
        status = ui.text(STATUS_TEXT[mobile.status], (card.x + 32, middle), 14, face="bold", anchor="midleft")
        if self.pilot == "policy" and self.session is not None:
            plugin = self.plugins.get(self.session.strategy.name)
            name = plugin.short_label if plugin is not None else self.session.strategy.name
            who = f"Conduce lo aprendido: {name}, generación {self.session.strategy.iteration}"
        else:
            who = "Conduces tú, con las flechas o WASD"
        room = card.right - 14 - status.right - 16
        if room > 90:
            ui.text(ui.fit(who, room, 12), (card.right - 14, middle), 12, theme.muted, anchor="midright")
        self._draw_episode(ui, panel, simulation, mobile)

    def _draw_episode(self, ui: Ui, panel: pygame.Rect, simulation, mobile) -> None:
        theme = ui.theme
        ui.card(panel)
        x, width = panel.x + 16, panel.width - 32
        y = panel.y + 16
        done = self.episode_summary is not None
        ui.text("Episodio terminado" if done else "Episodio en curso", (x, y), 12, theme.muted)
        ui.text(STATUS_TEXT[mobile.status], (x, y + 17), 18, face="bold")
        y += 50
        nav = mobile.navigation
        cells = [("Tiempo", f"{simulation.time:.1f} s"), ("Distancia", f"{mobile.distance_traveled:.1f}"),
                 ("Velocidad", f"{mobile.state.speed:.2f}"), ("Avance", f"{nav.progress * 100:.1f} %")]
        half = (width - 10) // 2
        for index, (label, value) in enumerate(cells):
            box = pygame.Rect(x + (index % 2) * (half + 10), y + (index // 2) * 72, half, 62)
            ui.box(box)
            ui.stat(box.x + 12, box.y + 8, label, value, 20 if half >= 122 else 17)
        y += 146
        ui.progress((x, y, width, 6), nav.progress)
        y += 16
        closest = float(mobile.scan.min()) * mobile.sensor.max_range if mobile.sensor is not None else 0.0
        for label, value in (("Orientación", f"{math.degrees(mobile.state.heading):.1f}°"),
                             ("Desvío del camino", f"{nav.deviation:.2f}"), ("LiDAR mínimo", f"{closest:.2f}")):
            ui.text(label, (x, y + 13), 13, anchor="midleft")
            ui.text(value, (x + width, y + 13), 13, face="mono", anchor="midright")
            y += 26
        y += 8
        half = (width - 8) // 2
        ui.button((x, y, half, 38), "Reiniciar", self.restart_manual)
        ui.button((x + half + 8, y, half, 38), "Mapa aleatorio", lambda: self.reset_manual(True), size=13)
        y += 52
        ui.divider(x, y, width)
        y += 12
        if done:
            ui.text("Resumen del episodio", (x, y), 14, face="bold")
            y += 26
            for label, value in self.episode_summary:
                if y + 16 > panel.bottom - 8:
                    break
                ui.text(label, (x, y), 13, theme.muted)
                ui.text(value, (x + width, y), 13, face="mono", anchor="topright")
                y += 21
        else:
            ui.text("Teclado", (x, y), 12, theme.muted)
            y += 22
            for keys, text in ((["↑", "↓", "←", "→"], "o WASD: conducir"), (["P"], "cambiar de piloto"),
                               (["R"], "reiniciar"), (["N"], "mapa aleatorio")):
                if y + 24 > panel.bottom - 8:
                    break
                self._keys(ui, x, y, keys, text)
                y += 30

    def _keys(self, ui: Ui, x: int, y: int, keys, text: str) -> None:
        theme = ui.theme
        for key in keys:
            chip = pygame.Rect(x, y, max(24, self.fonts.width(key, 12, "mono") + 12), 24)
            self.kit.shapes.rounded(ui.surface, chip, 6, theme.control, theme.control_line)
            ui.text(key, chip.center, 12, face="mono", anchor="center")
            x = chip.right + 5
        ui.text(text, (x + 3, y + 12), 13, theme.muted, anchor="midleft")

    # --- entrenar: preparar la corrida ----------------------------------------------------
    def _draw_setup(self, ui: Ui) -> None:
        theme, inner = ui.theme, self.inner
        tall = inner.height >= 620
        y = inner.y
        ui.text("Nueva corrida", (inner.x, y), 28 if tall else 22, face="bold")
        ui.link("Cargar un entrenamiento guardado", (inner.right, y + 8), self.load_checkpoint, 13, "topright")
        y += 38 if tall else 30
        if tall:
            training = self.config["training"]
            ui.text(ui.fit("Elige cómo navega y cómo esquiva; cada tarjeta muestra al algoritmo funcionando en el "
                           f"simulador. Población de {training['population_size']}, "
                           f"{training['scenarios_per_candidate']} mapas por individuo.", inner.width, 14),
                    (inner.x, y), 14, theme.muted)
            y += 22
        y += 12
        strategies = [self.plugins[name] for name in self.strategy_names]
        avoiders = [self.avoiders[name] for name in self.avoidance_names]
        columns = max(4, len(strategies), len(avoiders) + 1)
        gap = 16 if columns <= 4 else 10
        width = (inner.width - gap * (columns - 1)) // columns
        card_height = (inner.bottom - y - 2 * SECTION - gap) // 2
        image_height = max(40, min(int((width - 2) / 1.6667), card_height - OPTION_TEXT))
        card_height = image_height + OPTION_TEXT

        self._section(ui, inner.x, y, "1", "Navegación", "quién aprende el camino")
        y += SECTION
        if not strategies:
            ui.paragraph("No hay algoritmos de aprendizaje instalados (carpetas en optimization/).",
                         inner.x, y + 8, inner.width, 14)
        for index, plugin in enumerate(strategies):
            rect = pygame.Rect(inner.x + index * (width + gap), y, width, card_height)
            self._option(ui, rect, plugin, plugin.name == self.selected_strategy,
                         lambda name=plugin.name: self.select_strategy(name), image_height)
        y += card_height + gap

        last = inner.x + (columns - 1) * (width + gap)
        self._section(ui, inner.x, y, "2", "Evasión", "quién esquiva")
        self._section(ui, last, y, "3", "Mapas y duración", "")
        y += SECTION
        for index, plugin in enumerate(avoiders[:columns - 1]):
            rect = pygame.Rect(inner.x + index * (width + gap), y, width, card_height)
            self._option(ui, rect, plugin, plugin.name == self.selected_avoidance,
                         lambda name=plugin.name: self.select_avoidance(name), image_height)
        self._draw_run_settings(ui, pygame.Rect(last, y, width, card_height), bool(strategies))

    def _section(self, ui: Ui, x: int, y: int, number: str, title: str, rest: str) -> None:
        theme = ui.theme
        chip = pygame.Rect(x, y, 22, 22)
        self.kit.shapes.rounded(ui.surface, chip, 11, theme.primary)
        ui.text(number, chip.center, 12, theme.on_primary, "mono", "center")
        end = ui.text(title, (chip.right + 10, chip.centery), 15, face="bold", anchor="midleft").right
        if rest:
            ui.text(f"— {rest}", (end + 6, chip.centery), 15, theme.muted, anchor="midleft")

    def _option(self, ui: Ui, rect: pygame.Rect, plugin, chosen: bool, action, image_height: int) -> None:
        """Tarjeta de un algoritmo: una imagen suya funcionando en el simulador, su ícono y qué hace."""
        theme, surface = ui.theme, ui.surface
        ui.card(rect)
        picture = pygame.Rect(rect.x + 1, rect.y + 1, rect.width - 2, image_height)
        scene = self.kit.assets.scene(plugin.demo)
        if scene is not None:
            surface.blit(self.scenes.render(scene, picture.size), picture)
        else:                                   # un plugin sin escena: su ícono en grande
            surface.fill(theme.soft, picture)
            ui.icon(plugin.icon, picture.center, max(24, min(56, image_height - 16)), theme.muted, plugin.short_label)
        ui.divider(rect.x + 1, picture.bottom, rect.width - 2)
        ui.frame(rect)                          # recorta las esquinas de la imagen
        if chosen:
            self.kit.shapes.rounded(surface, rect, 18, None, theme.text, 2)
            pill = pygame.Rect(0, 0, self.fonts.width("Elegido", 11, "bold") + 20, 22)
            pill.topright = (rect.right - 10, rect.y + 10)
            self.kit.shapes.rounded(surface, pill, 11, theme.primary)
            ui.text("Elegido", pill.center, 11, theme.on_primary, "bold", "center")
        y = picture.bottom + 10
        ui.icon(plugin.icon, (rect.x + 27, y + 15), 30, theme.text, plugin.short_label)
        left = rect.x + 52
        room = rect.right - 12 - left
        ui.text(ui.fit(plugin.short_label, room, 15, "bold"), (left, y), 15, face="bold")
        lines = max(1, min(3, (rect.bottom - 6 - (y + 21)) // 16))
        ui.paragraph(plugin.description, left, y + 21, room, 12, max_lines=lines)
        ui.hit(rect, action)

    def _draw_run_settings(self, ui: Ui, rect: pygame.Rect, enabled: bool) -> None:
        theme = ui.theme
        ui.card(rect, fill=theme.soft)
        roomy = rect.height >= 236
        margin = 14 if roomy else 10
        x, width = rect.x + margin, rect.width - 2 * margin
        y = rect.y + margin
        ui.text("Mapas de entrenamiento", (x, y), 12, theme.muted)
        y += 20 if roomy else 17
        height = 36 if roomy else 30
        ui.segmented((x, y, width, height), MAP_MODES, self.selected_map_mode, self.select_map_mode, size=12)
        y += height + (12 if roomy else 7)
        row = 40 if roomy else 32
        ui.text("Generaciones", (x, y + row // 2 - (8 if roomy else 0)), 14, face="bold", anchor="midleft")
        if roomy:
            ui.text("Mapas nuevos en cada una", (x, y + row // 2 + 10), 12, theme.muted, anchor="midleft")
        ui.stepper(rect.right - margin, y + row // 2, str(self.iteration_limit) if self.iteration_limit else "∞",
                   lambda: self.set_iteration_limit(self.iteration_limit - LIMIT_STEP),
                   lambda: self.set_iteration_limit(self.iteration_limit + LIMIT_STEP),
                   value_width=30 if width < 230 else 38, button=min(36, row - 2))
        y += row + (8 if roomy else 4)
        ui.text("Sumar el mapa del editor" if width >= 236 else "Mapa del editor", (x, y + 13), 13, anchor="midleft")
        ui.toggle(rect.right - margin, y + 13, self.use_editor_map, self.toggle_editor_map)
        height = 46 if roomy else 36
        ui.button((x, rect.bottom - margin - height, width, height), "Empezar entrenamiento", self.start_training,
                  "primary", enabled=enabled, size=15 if width >= 236 else 13)

    # --- entrenar: corrida en curso -----------------------------------------------------------
    def _draw_training(self, ui: Ui) -> None:
        theme, inner, session = ui.theme, self.inner, self.session
        gap = 16
        lower = max(170, min(219, int(inner.height * 0.31)))
        upper = pygame.Rect(inner.x, inner.y, inner.width, inner.height - gap - lower)
        runs = [run for run in session.visible if run is not None]
        self.focus = min(self.focus, max(len(runs) - 1, 0))
        others = [index for index in range(len(runs)) if index != self.focus][:3]
        thumb_height = (upper.height - 18) // 3
        thumb_width = int((thumb_height - 20) * 1.6) if others else 0
        side_width = 264 if self.compact else 296
        room = upper.width - side_width - gap - (thumb_width + gap if others else 0)
        big_width = max(160, min(room, int((upper.height - AGENT_HEADER - 2) * 1.6) + 2)) if others else room
        big = pygame.Rect(upper.x, upper.y, big_width, upper.height)
        if runs:
            self._draw_agent(ui, big, runs[self.focus], self.focus, len(runs))
        else:
            ui.card(big)
            waiting = "Pulsa Iniciar" if not session.history and not self.running else "Evaluación sin renderizado"
            ui.text(waiting, big.center, 15, theme.muted, anchor="center")
        x = big.right + gap
        for slot, index in enumerate(others):
            self._draw_thumb(ui, pygame.Rect(x, upper.y + slot * (thumb_height + 9), thumb_width, thumb_height),
                             runs[index], index)
        if others:
            x += thumb_width + gap
        self._draw_run(ui, pygame.Rect(x, upper.y, inner.right - x, upper.height), session)

        last = session.history[-1] if session.history else None
        y = upper.bottom + gap
        first, second = int(inner.width * 0.33), int(inner.width * 0.27)
        draw_generation_stats(ui, (inner.x, y, first, lower), last)
        draw_validation(ui, (inner.x + first + gap, y, second, lower), last, session.strategy.generalizes)
        chart = pygame.Rect(inner.x + first + second + 2 * gap, y, inner.width - first - second - 2 * gap, lower)
        ui.card(chart)
        ui.text("Evolución del fitness", (chart.x + 16, chart.y + 14), 14, face="bold")
        draw_legend(ui, chart.right - 16, chart.y + 22, ["mejor", "promedio"])
        draw_line_chart(ui, (chart.x + 16, chart.y + 44, chart.width - 32, chart.height - 56),
                        [("mejor", [h.best_fitness for h in session.history]),
                         ("promedio", [h.mean_fitness for h in session.history])])
        alive = {id(run.simulation) for run in runs}
        self._trails = {key: entry for key, entry in self._trails.items() if key in alive}

    def _agent_status(self, run) -> str:
        return "sin avance" if run.runner.stalled else STATUS_TEXT[run.simulation.mobiles[0].status].lower()

    def _agent_world(self, ui: Ui, canvas: pygame.Rect, run) -> None:
        simulation = run.simulation
        self._world(ui, canvas, simulation, self._map_key("agente", simulation.world.map),
                    heatmap=self.session.strategy.cell_heatmap(run.scenario),
                    heat_key=(run.scenario.key, self.session.strategy.iteration), trail=self._trail_of(simulation))

    def _draw_agent(self, ui: Ui, rect: pygame.Rect, run, index: int, count: int) -> None:
        """El agente elegido, en grande, con lo que está haciendo."""
        theme = ui.theme
        ui.card(rect)
        self._agent_world(ui, pygame.Rect(rect.x + 1, rect.y + AGENT_HEADER, rect.width - 2,
                                          rect.height - AGENT_HEADER - 1), run)
        ui.frame(rect)
        ui.divider(rect.x + 1, rect.y + AGENT_HEADER - 1, rect.width - 2)
        middle = rect.y + AGENT_HEADER // 2
        color = theme.muted if self.session.is_collected(run) else theme.text
        title = ui.text(f"Agente {index + 1}", (rect.x + 14, middle), 14, color, "bold", "midleft")
        pager = count * 32 if count > 1 else 0
        detail = (f"· individuo {run.candidate.id} · mapa {run.episode_index + 1} de {run.episode_count} · "
                  f"fitness {run.partial_fitness:.1f} · {self._agent_status(run)}")
        room = rect.right - 14 - pager - title.right - 12
        if room > 60:
            ui.text(ui.fit(detail, room, 13), (title.right + 6, middle), 13, theme.muted, anchor="midleft")
        for number in range(count if count > 1 else 0):
            dot = pygame.Rect(rect.right - 8 - (count - number) * 32, middle - 13, 26, 26)
            ui.button(dot, str(number + 1), lambda n=number: self.set_focus(n),
                      "primary" if number == index else "control", size=12)

    def _draw_thumb(self, ui: Ui, rect: pygame.Rect, run, index: int) -> None:
        theme = ui.theme
        ui.card(rect, 14)
        canvas = pygame.Rect(rect.x + 1, rect.y + 1, rect.width - 2, rect.height - 21)
        self._agent_world(ui, canvas, run)
        ui.frame(rect, 14)
        ui.divider(rect.x + 1, canvas.bottom, rect.width - 2)
        ui.text(ui.fit(f"Agente {index + 1} · {self._agent_status(run)}", rect.width - 20, 12),
                (rect.x + 10, rect.bottom - 10), 12, theme.muted, anchor="midleft")
        ui.hit(rect, lambda: self.set_focus(index))

    def _draw_run(self, ui: Ui, rect: pygame.Rect, session: TrainingSession) -> None:
        """Qué corrida es, por dónde va y sus controles."""
        theme = ui.theme
        ui.card(rect)
        x, width = rect.x + 16, rect.width - 32
        y = rect.y + 16
        plugin, avoider = self.plugins.get(session.strategy.name), self.avoiders.get(session.avoidance)
        for offset, item in enumerate((plugin, avoider)):
            ring = pygame.Rect(x + offset * 46, y, 40, 40)
            self.kit.shapes.rounded(ui.surface, ring, 20, None, theme.text, 2)
            ui.icon(item.icon if item is not None else "", ring.center, 22, theme.text,
                    item.short_label if item is not None else "?")
        y += 49
        state = "Corrida terminada" if session.finished else "Corrida en curso" if self.running else "Corrida en pausa"
        ui.text(state, (x, y), 12, theme.muted)
        name = (f"{plugin.short_label if plugin is not None else session.strategy.name} + "
                f"{avoider.short_label if avoider is not None else session.avoidance}")
        ui.text(ui.fit(name, width, 17, "bold"), (x, y + 17), 17, face="bold")
        y += 48
        size = 56 if rect.height >= 420 else 40
        number = ui.text(str(session.current_iteration), (x, y), size, face="bold")
        limit = f"de {session.max_iterations} generaciones" if session.max_iterations else "generaciones"
        ui.text(ui.fit(limit, rect.right - 16 - number.right - 8, 14), (number.right + 8, number.bottom - size // 5), 14,
                theme.muted, anchor="bottomleft")
        y = number.bottom + 4
        done, total = session.evaluated
        partial = done / total if total else 0.0
        fraction = ((session.strategy.iteration + partial) / session.max_iterations if session.max_iterations
                    else partial)
        ui.progress((x, y, width, 6), fraction)
        y += 14
        mode = self.session_config["generator"]["navigation_mode"]
        ui.text(ui.fit(f"Evaluados {done} de {total} · mapas {MAP_MODE_LABELS.get(mode, mode)}", width, 12), (x, y), 12,
                theme.muted)
        y += 26
        # controles, anclados al pie de la tarjeta
        links = rect.bottom - 16 - 14
        ui.link("Guardar checkpoint", (x, links), self.save_checkpoint, 12)
        ui.link("Nueva corrida", (rect.right - 16, links), self.reset_training, 12, "topright")
        row = links - 12 - 40
        ui.button((x, row, 104, 40), "Finalizar", self.finish_training, enabled=bool(session.history))
        ui.stepper(rect.right - 16, row + 20, f"×{SPEEDS[self.speed_index]}", lambda: self.change_speed(-1),
                   lambda: self.change_speed(1), value_width=34)
        main = row - 10 - 46
        started = bool(session.history) or done > 0
        label, icon = ("Pausar", "pause") if self.running else ("Continuar" if started else "Iniciar", "play")
        ui.button((x, main, width, 46), label, self.toggle_training, "primary", icon=icon, size=15)
        # cifras propias del algoritmo, en el espacio que quede
        last = session.history[-1] if session.history else None
        if last is not None and last.strategy:
            labels = plugin.stat_labels if plugin is not None else {}
            for key, value in last.strategy.items():
                if y + 16 > main - 6:
                    break
                ui.text(ui.fit(labels.get(key, key), width - 62, 12), (x, y), 12, theme.muted)
                ui.text(f"{value:.3g}", (rect.right - 16, y), 12, theme.muted, "mono", "topright")
                y += 17
