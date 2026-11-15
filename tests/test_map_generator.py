"""Generador de mapas aleatorios: validez y reproducibilidad por semilla."""
import math

from editor.map_generator import GeneratorConfig, MapGenerator
from simulation.obstacle import DynamicObstacle
from simulation.world import World

SEEDS = range(40)


def generate(seed, **config):
    return MapGenerator(GeneratorConfig(**config)).generate(seed)


def test_same_seed_reproduces_the_same_map():
    assert generate(123).to_dict() == generate(123).to_dict()


def test_different_seeds_give_different_maps():
    assert generate(1).to_dict() != generate(2).to_dict()


def test_generated_maps_are_valid_and_simulable():
    for seed in SEEDS:
        m = generate(seed)
        assert m.validate() == [], f"semilla {seed}: {m.validate()}"
        assert m.seed == seed
        World(m)


def test_route_is_an_ordered_contiguous_path_from_start_to_goal():
    for seed in SEEDS:
        m = generate(seed, navigation_mode="route")
        assert m.route[0] == m.start and m.route[-1] == m.goal
        for a, b in zip(m.route, m.route[1:]):
            assert max(abs(a[0] - b[0]), abs(a[1] - b[1])) == 1


def test_maps_vary_in_routes_goals_and_obstacles():
    maps = [generate(seed, navigation_mode="route") for seed in SEEDS]
    assert len({tuple(m.route) for m in maps}) > 30
    assert len({m.goal for m in maps}) > 10
    assert all(m.static_obstacles for m in maps)
    kinds = {d.kind for m in maps for d in m.dynamic_obstacles}
    assert kinds == {"horizontal", "vertical", "circular"}
    speeds = {round(d.speed, 3) for m in maps for d in m.dynamic_obstacles}
    assert len(speeds) > 20


def test_obstacle_counts_respect_the_configured_ranges():
    for seed in SEEDS:
        m = generate(seed, static_obstacles=(2, 4), dynamic_obstacles=(1, 2))
        assert 2 <= len(m.static_obstacles) <= 4
        assert 1 <= len(m.dynamic_obstacles) <= 2


def test_dynamic_obstacles_never_sweep_over_the_start():
    for seed in SEEDS:
        m = generate(seed)
        sx, sy = m.cell_center(m.start)
        for spec in m.dynamic_obstacles:
            obstacle = DynamicObstacle(spec)
            for i in range(600):
                x, y = obstacle.position_at(i * 0.1)
                assert math.hypot(x - sx, y - sy) > 2.0
                assert 0.0 <= x <= m.width and 0.0 <= y <= m.height


def test_navigation_mode_follows_the_configuration():
    assert generate(5, navigation_mode="free").navigation_mode == "free"
    assert generate(5, navigation_mode="route").navigation_mode == "route"
    modes = {generate(seed, navigation_mode="mixed").navigation_mode for seed in SEEDS}
    assert modes == {"free", "route"}


def test_grid_size_follows_the_configuration():
    m = generate(9, cols=24, rows=14)
    assert (m.cols, m.rows) == (24, 14)
    assert m.validate() == []


# --- navegación libre: el modo por defecto de los mapas aleatorios ---------------------------

def distance_to_segment(cell, a, b):
    (px, py), (ax, ay), (bx, by) = cell, a, b
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def test_random_maps_are_free_navigation_by_default_with_no_drawn_route():
    for seed in SEEDS:
        m = generate(seed)
        assert m.navigation_mode == "free" and m.route == []
        assert m.validate() == []
        gx, gy = m.goal[0] - m.start[0], m.goal[1] - m.start[1]
        assert abs(math.atan2(gy, gx) - m.start_heading) < 1e-9        # arranca mirando al destino


def test_free_maps_put_obstacles_between_start_and_goal():
    """Para que encontrar el camino más corto exija esquivar algo."""
    blocked = 0
    for seed in SEEDS:
        m = generate(seed)
        on_the_way = [c for c in m.static_obstacles if distance_to_segment(c, m.start, m.goal) < 0.75]
        blocked += bool(on_the_way)
        assert all(distance_to_segment(c, m.start, m.goal) < 6.0 for c in m.static_obstacles)
    assert blocked > 30


def test_free_maps_vary_and_keep_all_three_kinds_of_moving_obstacle():
    maps = [generate(seed) for seed in SEEDS]
    assert len({(m.start, m.goal) for m in maps}) > 30
    assert {d.kind for m in maps for d in m.dynamic_obstacles} == {"horizontal", "vertical", "circular"}
    assert any(max(abs(a[0] - b[0]), abs(a[1] - b[1])) == 1                 # algunos obstáculos forman paredes
               for m in maps for a in m.static_obstacles for b in m.static_obstacles if a != b)
