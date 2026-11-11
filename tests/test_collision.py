"""Detección de colisiones del cuerpo circular del vehículo."""
import numpy as np

from simulation import collision
from simulation.map_data import DynamicObstacleSpec
from simulation.world import World

from helpers import corridor_map

BOXES = np.array([[4.0, 4.0, 5.0, 5.0]])
CIRCLES = np.array([[10.0, 10.0, 0.5]])


def test_circle_overlapping_a_box_collides():
    assert collision.circle_hits_boxes(3.8, 4.5, 0.3, BOXES)
    assert collision.circle_hits_boxes(4.5, 4.5, 0.3, BOXES)


def test_circle_near_a_box_corner_does_not_collide_until_it_touches():
    assert not collision.circle_hits_boxes(3.7, 3.7, 0.3, BOXES)
    assert collision.circle_hits_boxes(3.8, 3.8, 0.3, BOXES)


def test_circle_vs_circle_uses_sum_of_radii():
    assert collision.circle_hits_circles(10.7, 10.0, 0.3, CIRCLES)
    assert not collision.circle_hits_circles(10.9, 10.0, 0.3, CIRCLES)


def test_empty_obstacle_sets_never_collide():
    assert not collision.circle_hits_boxes(1, 1, 0.3, np.zeros((0, 4)))
    assert not collision.circle_hits_circles(1, 1, 0.3, np.zeros((0, 3)))


def test_leaving_the_world_counts_as_collision():
    assert collision.circle_out_of_bounds(0.2, 5.0, 0.3, 20.0, 10.0)
    assert collision.circle_out_of_bounds(19.9, 5.0, 0.3, 20.0, 10.0)
    assert collision.circle_out_of_bounds(5.0, 9.8, 0.3, 20.0, 10.0)
    assert not collision.circle_out_of_bounds(5.0, 5.0, 0.3, 20.0, 10.0)


def test_world_collision_covers_static_dynamic_and_bounds():
    spec = DynamicObstacleSpec(kind="horizontal", x=12.5, y=2.5, speed=1.0, range_min=12.5, range_max=15.5)
    world = World(corridor_map(static_obstacles=[(8, 5)], dynamic_obstacles=[spec]))
    assert collision.collides(world, 8.5, 5.5, 0.3)      # celda X
    assert collision.collides(world, 12.5, 2.5, 0.3)     # obstáculo dinámico en t=0
    assert collision.collides(world, 0.1, 5.0, 0.3)      # borde del mundo
    assert not collision.collides(world, 3.5, 5.5, 0.3)


def test_dynamic_obstacle_collision_follows_its_position_in_time():
    spec = DynamicObstacleSpec(kind="horizontal", x=12.5, y=2.5, speed=1.0, range_min=12.5, range_max=15.5)
    world = World(corridor_map(dynamic_obstacles=[spec]))
    world.set_time(3.0)  # ahora está en x=15.5
    assert not collision.collides(world, 12.5, 2.5, 0.3)
    assert collision.collides(world, 15.5, 2.5, 0.3)
