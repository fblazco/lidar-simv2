"""Largo del camino más corto de un mapa: la vara con que se mide la eficiencia."""
import math

import pytest

from optimization.evaluation import Scenario
from simulation.navigation import shortest_path_length

from helpers import corridor_map


def free_map(**overrides):
    return corridor_map(navigation_mode="free", route=[], **overrides)


def test_without_obstacles_it_is_the_straight_line():
    assert shortest_path_length(free_map()) == pytest.approx(17.0)
    assert shortest_path_length(free_map(goal=(13, 0))) == pytest.approx(math.hypot(12, 5))


def test_a_wall_makes_the_shortest_path_longer_than_the_straight_line():
    wall = [(10, r) for r in range(3, 8)]
    length = shortest_path_length(free_map(static_obstacles=wall))
    over_the_tip = math.hypot(9.0, 3.0) + math.hypot(8.0, 3.0)      # por la fila libre junto a la punta
    assert length == pytest.approx(over_the_tip, abs=0.5) and length > 17.5


def test_an_obstacle_beside_the_line_does_not_lengthen_it():
    assert shortest_path_length(free_map(static_obstacles=[(10, 2), (6, 8)])) == pytest.approx(17.0)


def test_in_route_mode_it_is_the_length_of_the_drawn_route():
    bent = corridor_map(route=[(1, 5), (2, 5), (3, 4), (4, 3), (5, 3)], goal=(5, 3))
    assert shortest_path_length(bent) == pytest.approx(1.0 + 2 * math.sqrt(2) + 1.0)


def test_scenario_exposes_it_as_its_reference_length():
    scenario = Scenario(free_map(static_obstacles=[(10, r) for r in range(3, 8)]))
    assert scenario.reference_length == shortest_path_length(scenario.map_data)
