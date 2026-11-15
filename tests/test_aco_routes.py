"""Colonia de hormigas que traza una ruta, celda a celda, sobre cada mapa."""
import numpy as np
import pytest

from bootstrap import build_training_session
from config import load_config
from control.route_controller import RouteController
from optimization.aco_routes.colony import ACORoutesConfig, MapColony, RouteColonies
from optimization.evaluation import Scenario
from optimization.strategy import CandidateResult, LearningStrategy, UnknownScenarioError

from helpers import corridor_map

WALL = [(10, r) for r in range(3, 8)]


def wall_map(**overrides):
    """Navegación libre de (1,5) a (18,5) con una pared de 5 celdas en medio."""
    data = dict(name="pared", navigation_mode="free", route=[], static_obstacles=WALL)
    data.update(overrides)
    return corridor_map(**data)


def routes(colony, count, seed=0):
    rng = np.random.default_rng(seed)
    return [colony.construct(rng) for _ in range(count)]


def test_ants_build_valid_routes_from_start_to_goal():
    world = wall_map()
    blocked = set(WALL)
    for route in routes(MapColony(world, ACORoutesConfig()), 60):
        assert route[0] == world.start and route[-1] == world.goal
        assert len(set(route)) == len(route)                                  # sin pasar dos veces por una celda
        assert not blocked & set(route)
        for (c0, r0), (c1, r1) in zip(route, route[1:]):
            assert max(abs(c1 - c0), abs(r1 - r0)) == 1                       # celdas contiguas
            if c0 != c1 and r0 != r1:                                         # en diagonal no se roza una esquina
                assert (c1, r0) not in blocked and (c0, r1) not in blocked


def test_routes_never_turn_more_than_45_degrees_between_steps():
    """El vehículo no gira sobre sí mismo: la ruta debe ser conducible."""
    for world in (wall_map(), corridor_map(static_obstacles=[(9, 5)])):
        for route in routes(MapColony(world, ACORoutesConfig()), 40):
            steps = [(c1 - c0, r1 - r0) for (c0, r0), (c1, r1) in zip(route, route[1:])]
            turns = list(zip(steps, steps[1:]))
            if route[-1] == world.goal:
                turns = turns[:-1]            # la entrada al destino admite un giro mayor
            for (ax, ay), (bx, by) in turns:
                assert ax * bx + ay * by > 0 and abs(ax * by - ay * bx) <= 1      # mismo rumbo o 45° de giro


def test_heuristic_sends_the_ants_towards_the_goal():
    lengths = [len(route) for route in routes(MapColony(corridor_map(navigation_mode="free", route=[]),
                                                        ACORoutesConfig()), 40)]
    assert np.mean(lengths) < 1.6 * 18          # 18 celdas en línea recta


def test_in_route_mode_the_ants_stay_close_to_the_drawn_path():
    world = corridor_map(static_obstacles=[(9, 5)])       # un obstáculo sobre el camino dibujado
    drawn = set(world.route)
    closeness = []
    for route in routes(MapColony(world, ACORoutesConfig()), 30):
        near = [min(max(abs(c - dc), abs(r - dr)) for dc, dr in drawn) <= 1 for c, r in route]
        assert route[-1] == world.goal and (9, 5) not in route
        closeness.append(np.mean(near))
    assert np.mean(closeness) > 0.9          # la colonia sigue el camino; alguna hormiga da un rodeo mayor
    assert min(closeness) > 0.6


def test_pheromone_evaporates_and_the_best_routes_deposit():
    colony = MapColony(wall_map(), ACORoutesConfig(evaporation=0.25, elite_ants=1, tau_min=0.02))
    good, bad = routes(colony, 2)
    assert np.all(colony.pheromone == 1.0)
    colony.update([(good, 500.0), (bad, -20.0)])
    on_trail = [colony.pheromone[r, c] for c, r in good]
    off_trail = [colony.pheromone[r, c] for c, r in bad if (c, r) not in set(good)]
    assert np.allclose(on_trail, 1.0) and np.allclose(off_trail, 0.75)
    assert colony.best_route == good and colony.best_score == 500.0
    for _ in range(40):
        colony.update([(good, 500.0)])
    assert colony.pheromone.min() == pytest.approx(0.02) and colony.pheromone.max() <= 1.0


def test_ants_follow_a_strong_pheromone_trail():
    colony = MapColony(wall_map(), ACORoutesConfig())
    # Un rastro sensato: recto, sube para rodear la pared por arriba y vuelve a la fila del destino.
    trail = ([(c, 5) for c in range(1, 7)] + [(7, 4), (8, 3), (9, 2), (10, 2), (11, 2), (12, 3), (13, 4)]
             + [(c, 5) for c in range(14, 19)])
    colony.pheromone[:] = colony.config.tau_min
    for c, r in trail:
        colony.pheromone[r, c] = 1.0
    followers = routes(colony, 30, seed=9)
    overlap = [len(set(route) & set(trail)) / len(trail) for route in followers]
    assert np.mean(overlap) > 0.85 and all(route[-1] == colony.goal for route in followers)


def test_heatmap_matches_the_grid_and_highlights_the_trail():
    world = wall_map()
    colony = MapColony(world, ACORoutesConfig())
    route = routes(colony, 1)[0]
    for _ in range(30):
        colony.update([(route, 100.0)])
    heat = colony.heatmap()
    assert heat.shape == (world.rows, world.cols)
    assert heat.min() == 0.0 and heat.max() == 1.0
    assert all(heat[r, c] == 1.0 for c, r in route)


# --- la estrategia: una colonia por mapa -------------------------------------------------

SCENARIOS = [Scenario(wall_map(), label="pared"), Scenario(corridor_map(), label="pasillo")]


def make_strategy(seed=2, ants=8, **config):
    strategy = RouteColonies(ants=ants, config=ACORoutesConfig(**config), seed=seed)
    strategy.prepare(SCENARIOS)
    return strategy


def score(result_scores, strategy):
    """Resultados de prueba: a la hormiga i se le asignan los puntajes result_scores[i]."""
    return [CandidateResult(c, float(np.mean(result_scores[c.id])), [], list(result_scores[c.id]))
            for c in strategy.ask()]


def test_is_a_learning_strategy_that_does_not_generalize():
    strategy = make_strategy()
    assert isinstance(strategy, LearningStrategy) and strategy.name == "aco_routes"
    assert strategy.generalizes is False


def test_it_must_know_the_scenarios_before_building_routes():
    with pytest.raises(RuntimeError):
        RouteColonies(ants=4, config=ACORoutesConfig(), seed=1).ask()


def test_every_ant_carries_one_route_per_scenario():
    strategy = make_strategy()
    ants = strategy.ask()
    assert len(ants) == 8 and strategy.ask() is ants
    for ant in ants:
        assert set(ant.solution) == {s.key for s in SCENARIOS}
        for scenario in SCENARIOS:
            route = ant.solution[scenario.key]
            assert route[0] == scenario.map_data.start and route[-1] == scenario.map_data.goal


def test_each_map_keeps_the_route_that_scored_best_on_that_map():
    strategy = make_strategy()
    ants = strategy.ask()
    scores = {a.id: [0.0, 0.0] for a in ants}
    scores[3] = [600.0, 10.0]      # la hormiga 3 es la mejor en el primer mapa
    scores[5] = [20.0, 640.0]      # la 5, en el segundo
    strategy.tell(score(scores, strategy))
    solution, fitness = strategy.best()
    assert solution[SCENARIOS[0].key] == ants[3].solution[SCENARIOS[0].key]
    assert solution[SCENARIOS[1].key] == ants[5].solution[SCENARIOS[1].key]
    assert fitness == pytest.approx(620.0)
    assert strategy.ask()[0].solution == solution          # vuelve a salir como primera hormiga
    assert strategy.iteration == 1


def test_incomplete_results_are_rejected():
    strategy = make_strategy()
    with pytest.raises(ValueError):
        strategy.tell(score({a.id: [1.0, 1.0] for a in strategy.ask()}, strategy)[:-1])


def test_heatmap_is_available_only_for_known_maps():
    strategy = make_strategy()
    heat = strategy.cell_heatmap(SCENARIOS[0])
    assert heat.shape == (10, 20) and 0.0 <= heat.min() <= heat.max() <= 1.0
    assert strategy.cell_heatmap(Scenario(corridor_map(goal=(15, 2)))) is None


def test_same_seed_reproduces_the_routes_and_state_resumes_exactly():
    def run(strategy, steps):
        for _ in range(steps):
            ants = strategy.ask()
            strategy.tell(score({a.id: [float(-len(a.solution[s.key])) for s in SCENARIOS] for a in ants}, strategy))
        return [a.solution for a in strategy.ask()]

    assert run(make_strategy(seed=5), 3) == run(make_strategy(seed=5), 3)
    assert run(make_strategy(seed=5), 3) != run(make_strategy(seed=6), 3)

    original = make_strategy(seed=5)
    run(original, 2)
    ants = original.ask()
    original.tell(score({a.id: [float(-len(a.solution[s.key])) for s in SCENARIOS] for a in ants}, original))
    resumed = RouteColonies(ants=8, config=ACORoutesConfig(), seed=99)
    resumed.set_state(original.get_state())
    assert resumed.iteration == original.iteration and resumed.best()[1] == original.best()[1]
    resumed.prepare(SCENARIOS)
    assert run(original, 2) == run(resumed, 2)


def test_statistics_report_colony_parameters():
    stats = make_strategy(alpha=1.2, beta=2.5, evaporation=0.3).statistics()
    assert (stats["alpha"], stats["beta"], stats["evaporation"]) == (1.2, 2.5, 0.3)
    assert {"route_length", "trail_focus"} <= set(stats)


# --- integrada con el simulador --------------------------------------------------------------

def tiny(**training):
    return load_config(overrides={
        "simulation": {"max_time": 15.0},
        "training": {"strategy": "aco_routes", "population_size": 10, "visible_agents": 0,
                     "scenarios_per_candidate": 0, "validation_scenarios": 2, "stall_time": 2.0, **training},
    })


def test_the_colony_learns_a_way_around_a_wall():
    session = build_training_session(tiny(), fixed_maps=[wall_map()])
    best = [session.run_iteration() for _ in range(8)]
    assert max(stats.best_fitness for stats in best) > 500.0         # llegó al destino rodeando la pared
    assert all(stats.validation_fitness is None for stats in best)   # una ruta por mapa no se valida en otros
    assert all(b.best_fitness >= a.best_fitness for a, b in zip(best, best[1:]))


def test_best_route_drives_the_map_it_was_trained_on_and_no_other():
    world = wall_map()
    session = build_training_session(tiny(), fixed_maps=[world])
    session.run_iteration()
    controller = session.best_controller(world)
    assert isinstance(controller, RouteController)
    assert tuple(controller.planned_path[0]) == world.cell_center(world.start)
    with pytest.raises(UnknownScenarioError):
        session.best_controller(corridor_map())
