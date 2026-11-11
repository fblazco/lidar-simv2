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
