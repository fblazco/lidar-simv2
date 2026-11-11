"""Controladores intercambiables, ObservationBuilder y política MLP."""
import numpy as np
import pytest

from control.controller import Action, Controller, Observation, ROUTE_FOLLOWING
from control.manual_controller import ManualController
from control.observation_builder import ObservationBuilder
from control.policy import MLPPolicy
from control.policy_controller import MLPControllerFactory, PolicyController


def observation(num_rays=72, **overrides):
    data = dict(
        lidar=np.linspace(0.0, 1.0, num_rays),
        lidar_previous=np.ones(num_rays),
        heading=0.7,
        speed=2.0,
        max_speed=4.0,
        goal_distance=30.0,
        goal_bearing=-1.2,
        waypoint_distance=2.0,
        waypoint_bearing=0.3,
        path_deviation=-5.0,
        path_heading_error=0.1,
        navigation_mode=ROUTE_FOLLOWING,
        lidar_range=8.0,
        time=1.0,
    )
    data.update(overrides)
    return Observation(**data)


def test_action_clipped_limits_both_outputs():
    assert Action(3.0, -7.0).clipped() == Action(1.0, -1.0)


def test_manual_controller_returns_the_last_command_and_resets_to_neutral():
    controller = ManualController()
    assert isinstance(controller, Controller)
    assert controller.act(observation()) == Action(0.0, 0.0)
    controller.set_command(steering=-0.5, acceleration=1.0)
    assert controller.act(observation()) == Action(-0.5, 1.0)
    controller.reset()
    assert controller.act(observation()) == Action(0.0, 0.0)


def test_builder_size_matches_the_vector_it_builds():
    for use_previous in (True, False):
        builder = ObservationBuilder(num_rays=72, use_previous_lidar=use_previous)
        vector = builder.build(observation())
        assert vector.shape == (builder.size,)
        assert len(builder.feature_names) == builder.size


def test_previous_lidar_adds_exactly_one_scan_of_inputs():
    with_previous = ObservationBuilder(num_rays=72, use_previous_lidar=True)
    without = ObservationBuilder(num_rays=72, use_previous_lidar=False)
    assert with_previous.size - without.size == 72


def test_builder_output_is_bounded_and_finite_even_for_extreme_values():
    builder = ObservationBuilder(num_rays=72)
    vector = builder.build(observation(goal_distance=1e6, path_deviation=-1e6, speed=99.0))
    assert np.all(np.isfinite(vector))
    assert np.all(np.abs(vector) <= 1.0)


def test_builder_encodes_navigation_mode():
    builder = ObservationBuilder(num_rays=8)
    index = builder.feature_names.index("mode")
    assert builder.build(observation(8))[index] == 1.0
    assert builder.build(observation(8, navigation_mode="free"))[index] == 0.0


def test_mlp_parameter_count_and_roundtrip():
    assert MLPPolicy.parameter_count([5, 4, 2]) == 5 * 4 + 4 + 4 * 2 + 2
    policy = MLPPolicy([5, 4, 2])
    params = np.arange(34, dtype=float) / 34.0
    policy.set_parameters(params)
    assert np.array_equal(policy.get_parameters(), params)


def test_mlp_outputs_are_bounded_and_depend_on_parameters():
    policy = MLPPolicy([5, 4, 2])
    x = np.array([0.1, -0.4, 0.9, 0.0, 0.3])
    rng = np.random.default_rng(0)
    policy.set_parameters(rng.normal(0, 1, 34))
    first = policy(x)
    policy.set_parameters(rng.normal(0, 1, 34))
    second = policy(x)
    assert first.shape == (2,)
    assert np.all(np.abs(first) <= 1.0)
    assert not np.allclose(first, second)


def test_mlp_rejects_parameter_vectors_of_the_wrong_length():
    with pytest.raises(ValueError):
        MLPPolicy([5, 4, 2]).set_parameters(np.zeros(10))


def test_policy_controller_turns_policy_outputs_into_an_action():
    builder = ObservationBuilder(num_rays=72)
    policy = MLPPolicy([builder.size, 6, 2])
    policy.set_parameters(np.random.default_rng(1).normal(0, 1, MLPPolicy.parameter_count([builder.size, 6, 2])))
    action = PolicyController(policy, builder).act(observation())
    expected = policy(builder.build(observation()))
    assert action == Action(float(expected[0]), float(expected[1]))


def test_factory_derives_network_size_from_the_builder():
    builder = ObservationBuilder(num_rays=72, use_previous_lidar=False)
    factory = MLPControllerFactory(builder, hidden_layers=[8])
    assert factory.layer_sizes == [builder.size, 8, 2]
    assert factory.parameter_count == MLPPolicy.parameter_count([builder.size, 8, 2])
    controller = factory(np.zeros(factory.parameter_count))
    assert controller.act(observation()) == Action(0.0, 0.0)
