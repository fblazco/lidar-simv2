"""Configuración externa en JSON."""
import json

from config import load_config


def test_default_config_has_every_section_the_app_needs():
    cfg = load_config()
    for section in ("window", "simulation", "vehicle", "lidar", "map", "observation", "policy",
                    "training", "fitness", "generator", "genetic"):
        assert section in cfg, section
    assert cfg["lidar"]["num_rays"] == 72 and cfg["lidar"]["fov_deg"] == 360


def test_population_size_and_visible_agents_are_separate_settings():
    training = load_config()["training"]
    assert training["population_size"] > training["visible_agents"] > 0


def test_user_file_overrides_only_the_keys_it_names(tmp_path):
    path = tmp_path / "mio.json"
    path.write_text(json.dumps({"training": {"population_size": 12}, "lidar": {"max_range": 5.0}}))
    cfg = load_config(path)
    default = load_config()
    assert cfg["training"]["population_size"] == 12
    assert cfg["training"]["visible_agents"] == default["training"]["visible_agents"]
    assert cfg["lidar"] == {**default["lidar"], "max_range": 5.0}


def test_loading_never_mutates_the_defaults():
    a = load_config()
    a["training"]["population_size"] = -1
    assert load_config()["training"]["population_size"] != -1
