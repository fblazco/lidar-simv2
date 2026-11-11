"""Raycasting geométrico del LiDAR."""
import math

import numpy as np
import pytest

from sensors.lidar import Lidar

NO_CIRCLES = np.zeros((0, 3))
NO_BOXES = np.zeros((0, 4))
BIG = (100.0, 100.0)


def ray(index_deg):
    return index_deg // 5


def test_default_configuration_is_72_rays_every_5_degrees_over_360():
    lidar = Lidar()
    assert lidar.num_rays == 72
    assert np.allclose(np.diff(lidar.angles), math.radians(5.0))
    assert lidar.angles[0] == 0.0
    assert lidar.angles[-1] == pytest.approx(math.radians(355.0))


def test_free_space_reads_maximum_normalized_distance():
    scan = Lidar(max_range=8.0).scan(50.0, 50.0, 0.0, NO_CIRCLES, NO_BOXES, BIG)
    assert scan.shape == (72,)
    assert np.all(scan == 1.0)


def test_circle_ahead_is_measured_to_its_surface():
    circles = np.array([[55.0, 50.0, 1.0]])
    scan = Lidar(max_range=8.0).scan(50.0, 50.0, 0.0, circles, NO_BOXES, BIG)
    assert scan[ray(0)] == pytest.approx(4.0 / 8.0)
    assert scan[ray(180)] == 1.0


def test_box_ahead_is_measured_to_its_face():
    boxes = np.array([[53.0, 49.0, 54.0, 51.0]])
    scan = Lidar(max_range=8.0).scan(50.0, 50.0, 0.0, NO_CIRCLES, boxes, BIG)
    assert scan[ray(0)] == pytest.approx(3.0 / 8.0)
    assert scan[ray(90)] == 1.0


def test_world_bounds_are_detected_as_walls():
    scan = Lidar(max_range=8.0).scan(2.0, 5.0, 0.0, NO_CIRCLES, NO_BOXES, (20.0, 10.0))
    assert scan[ray(180)] == pytest.approx(2.0 / 8.0)   # pared izquierda
    assert scan[ray(90)] == pytest.approx(5.0 / 8.0)    # pared inferior (y crece hacia abajo)
    assert scan[ray(0)] == 1.0


def test_rays_rotate_with_vehicle_heading():
    circles = np.array([[50.0, 55.0, 1.0]])  # en +y
    scan = Lidar(max_range=8.0).scan(50.0, 50.0, math.pi / 2, circles, NO_BOXES, BIG)
    assert scan[ray(0)] == pytest.approx(4.0 / 8.0)


def test_nearest_obstacle_wins_on_the_same_ray():
    circles = np.array([[56.0, 50.0, 1.0], [53.0, 50.0, 0.5]])
    boxes = np.array([[54.0, 49.5, 54.5, 50.5]])
    scan = Lidar(max_range=8.0).scan(50.0, 50.0, 0.0, circles, boxes, BIG)
    assert scan[ray(0)] == pytest.approx(2.5 / 8.0)


def test_obstacles_beyond_max_range_are_ignored():
    circles = np.array([[60.0, 50.0, 1.0]])
    scan = Lidar(max_range=8.0).scan(50.0, 50.0, 0.0, circles, NO_BOXES, BIG)
    assert scan[ray(0)] == 1.0


def test_readings_are_always_normalized_between_0_and_1():
    rng = np.random.default_rng(3)
    circles = np.column_stack([rng.uniform(0, 20, 12), rng.uniform(0, 10, 12), rng.uniform(0.2, 1.0, 12)])
    boxes = np.array([[3.0, 3.0, 4.0, 4.0], [10.0, 6.0, 11.0, 7.0]])
    scan = Lidar(max_range=6.0).scan(7.3, 4.1, 1.1, circles, boxes, (20.0, 10.0))
    assert np.all((scan >= 0.0) & (scan <= 1.0))


def test_axis_aligned_ray_does_not_hit_a_box_beside_it():
    boxes = np.array([[53.0, 50.5, 54.0, 51.5]])  # el rayo 0° pasa por y=50, por fuera
    scan = Lidar(max_range=8.0).scan(50.0, 50.0, 0.0, NO_CIRCLES, boxes, BIG)
    assert scan[ray(0)] == 1.0


def test_hit_points_match_measured_distances():
    lidar = Lidar(max_range=8.0)
    circles = np.array([[55.0, 50.0, 1.0]])
    scan = lidar.scan(50.0, 50.0, 0.0, circles, NO_BOXES, BIG)
    points = lidar.hit_points(50.0, 50.0, 0.0, scan)
    assert points.shape == (72, 2)
    assert points[ray(0)] == pytest.approx((54.0, 50.0))
