"""La aplicación Pygame completa, sin ventana real (driver de video 'dummy')."""
import time

import pygame
import pytest

from config import load_config
from ui.application import Application

from helpers import corridor_map


@pytest.fixture
def app(tmp_path):
    config = load_config(overrides={
        "window": {"width": 1000, "height": 640},
        "map": {"cols": 16, "rows": 10},
        "simulation": {"max_time": 6.0},
        "policy": {"hidden_layers": [4]},
        "observation": {"use_previous_lidar": False},
        "generator": {"static_obstacles": [1, 2], "dynamic_obstacles": [1, 1]},
        "training": {"population_size": 6, "visible_agents": 4, "scenarios_per_candidate": 1,
                     "validation_scenarios": 1, "stall_time": 1.0, "checkpoint_every": 0},
    })
    application = Application(config, base_dir=tmp_path)
    yield application
    application.close()


def press(view, pos):
    view.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1))


def release(view, pos):
    view.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=pos, button=1))


def drag(view, cells):
    points = [view.cell_to_screen(c) for c in cells]
    press(view, points[0])
    for point in points[1:]:
        view.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=point, rel=(1, 0), buttons=(1, 0, 0)))
    release(view, points[-1])


def distinct_colors(surface, step=7):
    width, height = surface.get_size()
    return {tuple(surface.get_at((x, y)))[:3] for x in range(0, width, step) for y in range(0, height, step)}


def train_one_generation(app, max_frames=20000):
    view = app.simulation_view
    view.set_sub_mode("training")
    view.start_training()
    slowest = 0.0
    for _ in range(max_frames):
        started = time.perf_counter()
        app.run_frames(1)
        slowest = max(slowest, time.perf_counter() - started)
        if view.session.history:
            return slowest
    raise AssertionError("la generación no terminó")


def test_app_starts_in_the_editor_and_draws(app):
    assert app.mode == "editor"
    app.run_frames(3)
    assert len(distinct_colors(app.screen)) > 3


def test_function_keys_switch_between_the_two_modes(app):
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F2, mod=0, unicode=""))
    app.run_frames(1)
    assert app.mode == "simulation"
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F1, mod=0, unicode=""))
    app.run_frames(1)
    assert app.mode == "editor"


def test_dragging_with_the_path_tool_draws_an_ordered_route(app):
    view = app.editor_view
    app.run_frames(1)
    view.select_tool("route")
    drag(view, [(2, 2), (4, 2), (7, 2)])
    assert view.editor.map.route == [(c, 2) for c in range(2, 8)]


def test_editor_tools_place_obstacles_start_and_goal(app):
    view = app.editor_view
    app.run_frames(1)
    view.select_tool("static")
    drag(view, [(5, 5), (6, 5)])
    view.select_tool("start")
    drag(view, [(1, 1), (1, 3)])            # arrastrar define la orientación
    view.select_tool("goal")
    drag(view, [(12, 8)])
    view.select_tool("dynamic")
    view.select_dynamic_kind("circular")
    drag(view, [(9, 4), (11, 4)])
    view.select_tool("erase")
    drag(view, [(6, 5)])
    m = view.editor.map
    assert m.static_obstacles == [(5, 5)]
    assert m.start == (1, 1) and m.start_heading == pytest.approx(1.5708, abs=1e-3)
    assert m.goal == (12, 8)
    assert [d.kind for d in m.dynamic_obstacles] == ["circular"]
    assert m.dynamic_obstacles[0].orbit_radius == pytest.approx(2.0)
    assert view.selected_dynamic == 0
    app.run_frames(2)                       # dibuja el panel de propiedades sin errores


def test_maps_are_saved_and_loaded_from_the_editor(app, tmp_path):
    view = app.editor_view
    view.editor.set_map(corridor_map())
    path = view.save_map("demo")
    assert path == tmp_path / "maps" / "demo.json" and path.exists()
    view.editor.new()
    assert view.editor.map.route == []
    view.load_map("demo")
    assert view.editor.map.to_dict() == {**corridor_map().to_dict(), "name": "demo"}


def test_simulation_mode_drives_the_editor_map_with_the_manual_controller(app):
    app.editor_view.editor.set_map(corridor_map())
    app.set_mode("simulation")
    view = app.simulation_view
    assert view.sub_mode == "manual"
    view.input_source = lambda: (0.0, 1.0)     # acelerar a fondo, sin teclado real
    app.run_frames(60)
    mobile = view.simulation.mobiles[0]
    assert view.simulation.world.map.name == "corridor"
    assert mobile.state.x > 2.5 and mobile.scan.shape == (72,)
    assert len(distinct_colors(app.screen)) > 5


def test_simulation_mode_uses_a_random_map_when_the_editor_map_is_incomplete(app):
    app.set_mode("simulation")
    app.run_frames(3)
    view = app.simulation_view
    assert view.simulation is not None
    assert view.simulation.world.map.seed is not None
    assert "aleatorio" in view.message.lower()


def test_training_runs_in_the_window_without_blocking_it(app):
    app.set_mode("simulation")
    slowest_frame = train_one_generation(app)
    view = app.simulation_view
    assert slowest_frame < 0.5
    assert len(view.session.visible) == 4
    assert view.session.history[0].evaluations == 6
    app.run_frames(5)                           # sigue con la generación siguiente
    assert view.session.current_iteration == 2
    assert len(distinct_colors(app.screen)) > 5


def test_training_can_be_paused_and_resumed(app):
    app.set_mode("simulation")
    view = app.simulation_view
    view.set_sub_mode("training")
    view.start_training()
    app.run_frames(3)
    view.toggle_training()
    steps = [run.simulation.steps for run in view.session.visible if run]
    app.run_frames(5)
    assert [run.simulation.steps for run in view.session.visible if run] == steps
    view.toggle_training()
    app.run_frames(5)
    assert [run.simulation.steps for run in view.session.visible if run] != steps


def test_checkpoints_are_saved_and_restored_from_the_window(app, tmp_path):
    app.set_mode("simulation")
    train_one_generation(app)
    view = app.simulation_view
    path = view.save_checkpoint()
    assert path.parent == tmp_path / "models" and path.exists()
    view.new_training()
    assert view.session.history == []
    view.load_checkpoint(path)
    assert len(view.session.history) == 1 and view.session.strategy.iteration == 1


def test_best_policy_can_replace_the_manual_pilot(app):
    app.editor_view.editor.set_map(corridor_map())
    app.set_mode("simulation")
    train_one_generation(app)
    view = app.simulation_view
    view.set_sub_mode("manual")
    view.set_pilot("policy")
    app.run_frames(10)
    assert type(view.simulation.mobiles[0].controller).__name__ == "PolicyController"
    view.set_pilot("manual")
    assert type(view.simulation.mobiles[0].controller).__name__ == "ManualController"


# --- selección de algoritmo, resultados y comparación ----------------------------------------

def test_training_algorithm_is_chosen_in_the_window(app):
    app.set_mode("simulation")
    view = app.simulation_view
    view.set_sub_mode("training")
    assert view.strategy_names == ["aco_routes", "aco_rules", "genetic", "reactive"]
    assert view.selected_strategy == "genetic"
    view.cycle_strategy(1)
    assert view.selected_strategy == "reactive"
    view.cycle_strategy(1)
    assert view.selected_strategy == "aco_routes"          # la lista es circular
    view.cycle_strategy(1)
    assert view.selected_strategy == "aco_rules"
    view.new_training()
    assert view.session.strategy.name == "aco_rules"
    view.select_strategy("genetic")
    assert view.session.strategy.name == "aco_rules"      # cambiar la selección no toca el entrenamiento en curso
    app.run_frames(3)


@pytest.mark.parametrize("strategy", ["genetic", "aco_rules", "aco_routes"])
def test_every_algorithm_trains_in_the_window(app, strategy):
    app.set_mode("simulation")
    view = app.simulation_view
    view.select_strategy(strategy)
    slowest = train_one_generation(app)
    assert view.session.strategy.name == strategy
    assert slowest < 0.5
    assert len(view.session.history) == 1
    app.run_frames(5)
    assert len(distinct_colors(app.screen)) > 5


def test_route_colony_shows_its_pheromone_and_the_route_of_each_ant(app):
    app.set_mode("simulation")
    view = app.simulation_view
    view.select_strategy("aco_routes")
    view.set_sub_mode("training")
    view.start_training()
    app.run_frames(3)
    run = next(r for r in view.session.visible if r is not None)
    heat = view.session.strategy.cell_heatmap(run.scenario)
    assert heat.shape == (run.scenario.map_data.rows, run.scenario.map_data.cols)
    assert run.simulation.mobiles[0].controller.planned_path.shape[1] == 2


def test_finishing_a_run_shows_its_statistics_and_saves_it(app, tmp_path):
    app.set_mode("simulation")
    train_one_generation(app)
    view = app.simulation_view
    record = view.finish_training()
    assert view.running is False and view.sub_mode == "results"
    assert record.strategy == "genetic" and record.metrics()["iterations"] == 1
    assert (tmp_path / "logs" / "runs" / f"{record.run_id}.json").exists()
    assert view.results.selected == [record.run_id]
    assert [r.run_id for r in view.results.records] == [record.run_id]
    app.run_frames(3)
    assert len(distinct_colors(app.screen)) > 5


def test_finishing_before_any_generation_ends_does_nothing(app):
    app.set_mode("simulation")
    view = app.simulation_view
    view.set_sub_mode("training")
    view.start_training()
    app.run_frames(2)
    assert view.finish_training() is None
    assert view.sub_mode == "training" and view.results.records == []


def test_training_stops_by_itself_at_the_generation_limit(app):
    app.set_mode("simulation")
    view = app.simulation_view
    view.set_iteration_limit(1)
    train_one_generation(app)
    app.run_frames(2)
    assert view.running is False and view.sub_mode == "results"
    assert len(view.results.records) == 1
    view.set_sub_mode("training")
    view.start_training()                    # continuar extiende el límite otro tramo
    assert view.running and not view.session.finished


def test_two_runs_with_different_algorithms_can_be_compared(app):
    app.set_mode("simulation")
    view = app.simulation_view
    train_one_generation(app)
    first = view.finish_training()
    view.select_strategy("aco_rules")
    view.new_training()
    train_one_generation(app)
    second = view.finish_training()
    assert first.run_id != second.run_id
    assert view.results.selected == [second.run_id, first.run_id]      # A: la recién terminada; B: la anterior
    rows = view.results.comparison()
    assert rows[0][0] == "Algoritmo" and rows[0][1] != rows[0][2]
    assert any(label == "Mejor fitness" for label, *_ in rows)
    app.run_frames(3)
    assert len(distinct_colors(app.screen)) > 6
    view.results.toggle(first.run_id)                                    # quitar B deja el resumen de una sola
    assert view.results.selected == [second.run_id] and view.results.comparison() == []
    app.run_frames(2)


def test_manual_episode_ends_with_a_summary(app):
    app.editor_view.editor.set_map(corridor_map())
    app.set_mode("simulation")
    view = app.simulation_view
    view.input_source = lambda: (0.0, 1.0)
    assert view.episode_summary is None
    for _ in range(3000):
        app.run_frames(1)
        if view.episode_summary is not None:
            break
    summary = dict(view.episode_summary)
    assert summary["Resultado"] == "llegó"
    assert float(summary["Fitness"]) > 500.0
    assert {"Tiempo", "Distancia", "Velocidad media", "Desvío medio"} <= set(summary)
    app.run_frames(2)


def test_best_route_pilot_drives_one_of_the_maps_the_colony_trained_on(app):
    app.editor_view.editor.set_map(corridor_map())
    app.set_mode("simulation")
    view = app.simulation_view
    view.select_strategy("aco_routes")
    train_one_generation(app)
    view.set_sub_mode("manual")
    view.set_pilot("policy")
    assert type(view.simulation.mobiles[0].controller).__name__ == "RouteController"
    trained = [m.fingerprint() for m in view.session.training_maps()]
    assert view.simulation.world.map.fingerprint() in trained
    assert "entren" in view.message.lower()
    app.run_frames(10)


# --- evasión de obstáculos y tipo de mapas ------------------------------------------------------

def test_avoidance_and_map_kind_are_chosen_in_the_window(app):
    app.set_mode("simulation")
    view = app.simulation_view
    view.set_sub_mode("training")
    assert view.avoidance_names == ["learned", "apf", "ftg"] and view.selected_avoidance == "learned"
    view.cycle_avoidance(1)
    assert view.selected_avoidance == "apf"
    view.cycle_avoidance(-2)
    assert view.selected_avoidance == "ftg"                  # la lista es circular
    assert view.map_modes == ["free", "route", "mixed"] and view.selected_map_mode == "free"
    view.cycle_map_mode(1)
    assert view.selected_map_mode == "route"
    view.select_strategy("reactive")
    view.start_training()
    app.run_frames(3)
    session = view.session
    assert (session.strategy.name, session.avoidance) == ("reactive", "ftg")
    run = next(r for r in session.visible if r is not None)
    assert type(run.controller).__name__ == "AvoidanceController"
    assert run.scenario.map_data.navigation_mode == "route"
    view.select_avoidance("apf")
    assert session.avoidance == "ftg"                         # la selección se aplica al próximo entrenamiento


def test_run_record_keeps_the_avoidance_and_maps_chosen_in_the_window(app):
    app.set_mode("simulation")
    view = app.simulation_view
    view.select_strategy("reactive")
    view.select_avoidance("apf")
    train_one_generation(app)
    record = view.finish_training()
    assert (record.strategy, record.avoidance, record.map_mode, record.resampled) == ("reactive", "apf", "free", True)
    assert "APF" in dict(view.results.summary())["Evasión de obstáculos"]
    app.run_frames(3)
    assert len(distinct_colors(app.screen)) > 5


def test_comparison_in_the_window_says_whether_the_difference_is_significant(app):
    app.set_mode("simulation")
    view = app.simulation_view
    view.select_strategy("reactive")
    view.select_avoidance("ftg")
    train_one_generation(app)
    view.finish_training()
    view.select_avoidance("apf")
    view.new_training()
    train_one_generation(app)
    view.finish_training()
    newest, older = (r.run_id for r in view.results.records[:2])
    assert view.results.selected == [newest, older]          # la combinación anterior queda como rival
    assert "significativa" in view.results.significance()
    app.run_frames(3)
    assert len(distinct_colors(app.screen)) > 6


def test_loading_a_checkpoint_restores_the_choices_it_was_trained_with(app):
    app.set_mode("simulation")
    view = app.simulation_view
    view.select_strategy("aco_rules")
    view.select_avoidance("ftg")
    train_one_generation(app)
    path = view.save_checkpoint()
    view.select_strategy("genetic")
    view.select_avoidance("learned")
    view.load_checkpoint(path)
    assert (view.selected_strategy, view.selected_avoidance) == ("aco_rules", "ftg")
    assert view.session.avoidance == "ftg"
