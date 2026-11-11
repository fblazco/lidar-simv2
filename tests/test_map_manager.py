"""Guardado y carga de mapas en JSON."""
import json

import pytest

from editor.map_manager import MapFormatError, MapManager
from simulation.map_data import DynamicObstacleSpec, MapData


def sample_map():
    return MapData(
        name="prueba",
        cols=12,
        rows=8,
        navigation_mode="route",
        route=[(1, 1), (2, 2), (3, 2), (3, 3), (2, 4)],   # el orden importa, no está ordenado por coordenada
        start=(1, 1),
        start_heading=0.5,
        goal=(2, 4),
        static_obstacles=[(6, 6), (7, 6)],
        dynamic_obstacles=[
            DynamicObstacleSpec(kind="horizontal", x=4.5, y=5.5, speed=2.0, pause=0.5, direction=-1,
                                range_min=2.5, range_max=8.5),
            DynamicObstacleSpec(kind="circular", x=9.5, y=3.5, speed=1.0, center_x=8.5, center_y=3.5,
                                orbit_radius=1.0),
        ],
        seed=77,
    )


def test_saved_map_loads_back_identical(tmp_path):
    manager = MapManager(tmp_path)
    original = sample_map()
    manager.save(original)
    loaded = manager.load("prueba")
    assert loaded.to_dict() == original.to_dict()
    assert loaded.route == original.route
    assert loaded.dynamic_obstacles[0].direction == -1


def test_map_file_is_plain_json(tmp_path):
    path = MapManager(tmp_path).save(sample_map())
    assert path.suffix == ".json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["route"][1] == [2, 2]
    assert data["dynamic_obstacles"][1]["kind"] == "circular"
    assert data["format_version"] == 1


def test_list_maps_returns_saved_names(tmp_path):
    manager = MapManager(tmp_path)
    manager.save(sample_map(), name="b_mapa")
    manager.save(sample_map(), name="a_mapa")
    assert manager.list_maps() == ["a_mapa", "b_mapa"]


def test_saving_with_a_new_name_renames_the_map(tmp_path):
    manager = MapManager(tmp_path)
    manager.save(sample_map(), name="otro")
    assert manager.load("otro").name == "otro"


def test_unsafe_names_stay_inside_the_maps_directory(tmp_path):
    path = MapManager(tmp_path).save(sample_map(), name="../fuera/mi mapa")
    assert path.parent == tmp_path
    assert "/" not in path.stem and " " not in path.stem


def test_loading_a_corrupt_or_missing_file_raises_a_map_error(tmp_path):
    manager = MapManager(tmp_path)
    (tmp_path / "roto.json").write_text("{esto no es json", encoding="utf-8")
    (tmp_path / "lista.json").write_text("[1, 2, 3]", encoding="utf-8")
    for name in ("roto", "lista", "no_existe"):
        with pytest.raises(MapFormatError):
            manager.load(name)
