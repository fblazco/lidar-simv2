"""La documentación y los datos de ejemplo no se rompen sin que alguien lo note."""
import re
from pathlib import Path

import pytest

from editor.map_manager import load_map
from simulation.world import World

ROOT = Path(__file__).resolve().parent.parent
DOCUMENTS = sorted([ROOT / "README.md", ROOT / "CLAUDE.md", *(ROOT / "docs").rglob("*.md")])
EXAMPLE_MAPS = sorted((ROOT / "maps").glob("ejemplo_*.json"))
LINK = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)\)")


def relative_links(document: Path):
    text = re.sub(r"```.*?```", "", document.read_text(encoding="utf-8"), flags=re.S)
    return [link for link in LINK.findall(text) if not link.startswith(("http://", "https://", "#", "mailto:"))]


@pytest.mark.parametrize("document", DOCUMENTS, ids=lambda p: p.relative_to(ROOT).as_posix())
def test_relative_links_point_to_existing_files(document):
    broken = [link for link in relative_links(document)
              if not (document.parent / link.split("#")[0]).exists()]
    assert broken == []


def test_readme_shows_the_application_and_how_to_run_it():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    images = [link for link in relative_links(ROOT / "README.md") if link.endswith(".png")]
    assert len(images) >= 2
    for command in ("main.py", "main.py train", "pytest"):
        assert command in readme


def test_the_repository_ships_example_maps():
    assert len(EXAMPLE_MAPS) >= 2
    assert {load_map(path).navigation_mode for path in EXAMPLE_MAPS} == {"route", "free"}


@pytest.mark.parametrize("path", EXAMPLE_MAPS, ids=lambda p: p.stem)
def test_example_maps_are_valid_and_simulable(path):
    example = load_map(path)
    assert example.validate() == []
    assert example.name == path.stem
    kinds = {spec.kind for spec in example.dynamic_obstacles}
    assert example.static_obstacles and kinds
    World(example)
