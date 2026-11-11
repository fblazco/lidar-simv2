"""Representación ASCII del mapa (derivada de los datos, nunca al revés)."""
from rendering.ascii_renderer import ascii_grid, route_glyphs
from simulation.map_data import DynamicObstacleSpec, MapData


def test_route_glyphs_follow_the_direction_of_travel():
    assert set(route_glyphs([(1, 1), (2, 1), (3, 1)]).values()) == {"-"}
    assert set(route_glyphs([(1, 1), (1, 2), (1, 3)]).values()) == {"|"}
    assert set(route_glyphs([(1, 1), (2, 2), (3, 3)]).values()) == {"\\"}   # baja hacia la derecha
    assert set(route_glyphs([(1, 3), (2, 2), (3, 1)]).values()) == {"/"}    # sube hacia la derecha


def test_ascii_grid_draws_every_element_with_its_symbol():
    m = MapData(
        cols=8, rows=4,
        route=[(1, 1), (2, 1), (3, 1), (4, 2), (4, 3)],
        start=(1, 1), goal=(4, 3),
        static_obstacles=[(6, 0)],
        dynamic_obstacles=[DynamicObstacleSpec(kind="vertical", x=6.5, y=2.5, range_min=1.5, range_max=3.5)],
    )
    assert ascii_grid(m) == [
        "......X.",
        ".S-\\....",
        "....\\.*.",
        "....G...",
    ]


def test_static_obstacle_hides_the_path_under_it():
    m = MapData(cols=5, rows=1, route=[(0, 0), (1, 0), (2, 0), (3, 0), (4, 0)], start=(0, 0), goal=(4, 0),
                static_obstacles=[(2, 0)])
    assert ascii_grid(m) == ["S-X-G"]
