"""Trayectorias de obstáculos dinámicos: horizontal, vertical y circular."""
import math

import pytest

from simulation.map_data import DynamicObstacleSpec
from simulation.obstacle import DynamicObstacle


def horizontal(**kw):
    spec = dict(kind="horizontal", x=2.0, y=5.0, speed=2.0, range_min=2.0, range_max=6.0)
    spec.update(kw)
    return DynamicObstacle(DynamicObstacleSpec(**spec))


def test_horizontal_obstacle_goes_back_and_forth_between_extremes():
    obstacle = horizontal()
    expected = {0.0: 2.0, 1.0: 4.0, 2.0: 6.0, 3.0: 4.0, 4.0: 2.0, 5.0: 4.0}
    for t, x in expected.items():
        assert obstacle.position_at(t) == pytest.approx((x, 5.0))


def test_pause_holds_the_obstacle_at_each_extreme():
    obstacle = horizontal(pause=1.0)
    assert obstacle.position_at(2.0) == pytest.approx((6.0, 5.0))
    assert obstacle.position_at(2.9) == pytest.approx((6.0, 5.0))
    assert obstacle.position_at(3.5) == pytest.approx((5.0, 5.0))
    assert obstacle.position_at(5.0) == pytest.approx((2.0, 5.0))
    assert obstacle.position_at(5.9) == pytest.approx((2.0, 5.0))


def test_direction_sets_the_initial_sense_of_movement():
    obstacle = horizontal(x=4.0, direction=-1)
    assert obstacle.position_at(0.5) == pytest.approx((3.0, 5.0))
    assert obstacle.position_at(1.0) == pytest.approx((2.0, 5.0))
    assert obstacle.position_at(2.0) == pytest.approx((4.0, 5.0))


def test_vertical_obstacle_moves_only_along_y():
    obstacle = DynamicObstacle(
        DynamicObstacleSpec(kind="vertical", x=3.0, y=1.0, speed=1.0, range_min=1.0, range_max=4.0)
    )
    assert obstacle.position_at(2.0) == pytest.approx((3.0, 3.0))
    assert obstacle.position_at(4.0) == pytest.approx((3.0, 3.0))


def test_linear_obstacle_never_leaves_its_extremes():
    obstacle = horizontal(x=3.3, speed=1.7, pause=0.4)
    for i in range(400):
        x, y = obstacle.position_at(i * 0.05)
        assert 2.0 - 1e-9 <= x <= 6.0 + 1e-9
        assert y == 5.0


def circular(direction=1):
    return DynamicObstacle(
        DynamicObstacleSpec(
            kind="circular", x=7.0, y=5.0, speed=2.0, direction=direction,
            center_x=5.0, center_y=5.0, orbit_radius=2.0,
        )
    )


def test_circular_obstacle_follows_a_continuous_circle():
    obstacle = circular()
    assert obstacle.position_at(0.0) == pytest.approx((7.0, 5.0))
    # velocidad tangencial 2 con radio 2 => 1 rad/s
    assert obstacle.position_at(math.pi / 2) == pytest.approx((5.0, 7.0))
    assert obstacle.position_at(2 * math.pi) == pytest.approx((7.0, 5.0))
    for i in range(100):
        x, y = obstacle.position_at(i * 0.1)
        assert math.hypot(x - 5.0, y - 5.0) == pytest.approx(2.0)


def test_circular_direction_reverses_the_rotation():
    assert circular(direction=-1).position_at(math.pi / 2) == pytest.approx((5.0, 3.0))


def test_zero_speed_or_zero_extent_obstacle_stays_put():
    still = horizontal(speed=0.0)
    flat = horizontal(range_min=2.0, range_max=2.0)
    for obstacle in (still, flat):
        assert obstacle.position_at(7.3) == pytest.approx((2.0, 5.0))
