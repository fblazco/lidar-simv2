"""Restricciones arquitectónicas: quién puede depender de quién."""
import ast
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PACKAGES = ("simulation", "sensors", "control", "optimization", "editor", "rendering", "ui")


def imports_of(path: Path) -> set:
    """Nombres completos de los módulos que importa un archivo."""
    found = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    return found


def package_imports(package: str, exclude: str = "") -> dict:
    files = [p for p in (ROOT / package).rglob("*.py") if not exclude or exclude not in p.parts]
    assert files, f"no hay módulos en {package}"
    return {p.relative_to(ROOT).as_posix(): imports_of(p) for p in files}


def offenders(package: str, forbidden: tuple, exclude: str = "") -> list:
    return [
        f"{path} importa {name}"
        for path, names in package_imports(package, exclude).items()
        for name in names
        if any(name == f or name.startswith(f + ".") for f in forbidden)
    ]


@pytest.mark.parametrize("package", ["simulation", "sensors", "control", "editor", "rendering"])
def test_simulator_side_never_depends_on_optimization(package):
    assert offenders(package, ("optimization",)) == []


@pytest.mark.parametrize("package", ["simulation", "sensors", "control", "optimization", "editor"])
def test_logic_packages_never_depend_on_pygame_or_the_interface(package):
    assert offenders(package, ("pygame", "ui", "rendering")) == []


PLUGINS = sorted(p.name for p in (ROOT / "optimization").iterdir() if (p / "__init__.py").exists())
PLUGIN_MODULES = tuple(f"optimization.{name}" for name in PLUGINS)


def test_the_three_algorithms_are_plugins():
    assert PLUGINS == ["aco_routes", "aco_rules", "genetic"]


def test_generic_optimization_code_never_depends_on_a_concrete_algorithm():
    generic = [p for p in (ROOT / "optimization").glob("*.py")]
    bad = [f"{p.name} importa {name}" for p in generic for name in imports_of(p)
           if name.startswith(PLUGIN_MODULES)]
    assert bad == []


def test_ui_and_bootstrap_never_import_a_concrete_algorithm():
    assert offenders("ui", PLUGIN_MODULES) == []
    for entry in ("bootstrap.py", "main.py"):
        assert not any(n.startswith(PLUGIN_MODULES) for n in imports_of(ROOT / entry))


@pytest.mark.parametrize("plugin", PLUGINS)
def test_plugins_do_not_depend_on_each_other_or_on_the_simulator(plugin):
    others = tuple(m for m in PLUGIN_MODULES if m != f"optimization.{plugin}")
    forbidden = others + ("simulation", "sensors", "editor", "rendering", "ui", "pygame")
    assert offenders(f"optimization/{plugin}", forbidden) == []


def test_control_and_sensors_do_not_depend_on_the_simulator():
    assert offenders("control", ("simulation", "sensors", "editor")) == []
    assert offenders("sensors", PACKAGES) == []


def test_simulation_only_knows_the_controller_contract():
    allowed = {"control.controller"}
    bad = [
        f"{path} importa {name}"
        for path, names in package_imports("simulation").items()
        for name in names
        if name.split(".")[0] in PACKAGES and name.split(".")[0] != "simulation" and name not in allowed
    ]
    assert bad == []


@pytest.mark.parametrize("removed", [["genetic"], ["aco_rules"], ["aco_routes"], PLUGINS])
def test_project_works_after_deleting_algorithm_packages(tmp_path, removed):
    """Borrar uno o todos los algoritmos no rompe simulador, editor, sensores ni la aplicación."""
    copy = tmp_path / "proyecto"
    shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns(
        ".venv", ".git", "__pycache__", ".pytest_cache", "tests", "docs", "logs", "models"))
    for name in removed:
        shutil.rmtree(copy / "optimization" / name)
    remaining = sorted(set(PLUGINS) - set(removed))
    script = (
        "import os; os.environ['SDL_VIDEODRIVER'] = 'dummy'\n"
        "from config import load_config\n"
        "from bootstrap import build_simulation_factory, build_map_generator\n"
        "from control.manual_controller import ManualController\n"
        "from editor.map_editor import MapEditor\n"
        "from optimization.registry import discover_plugins\n"
        "cfg = load_config()\n"
        "world_map = build_map_generator(cfg).generate(4)\n"
        "pilot = ManualController()\n"
        "sim = build_simulation_factory(cfg).create(world_map, [pilot])\n"
        "pilot.set_command(0.0, 1.0)   # el episodio empieza con el control en neutro\n"
        "for _ in range(40): sim.step()\n"
        "assert sim.mobiles[0].distance_traveled > 1.0\n"
        "assert sim.mobiles[0].scan.shape == (72,)\n"
        "editor = MapEditor(); editor.add_route_cell((1, 1)); editor.add_route_cell((5, 1))\n"
        "assert len(editor.map.route) == 5\n"
        f"assert sorted(discover_plugins()) == {remaining!r}\n"
        "from ui.application import Application\n"
        "app = Application(cfg, base_dir='.')\n"
        "app.run_frames(5); app.set_mode('simulation'); app.run_frames(5)\n"
        "app.simulation_view.set_sub_mode('training'); app.run_frames(3)\n"
        "app.simulation_view.set_sub_mode('results'); app.run_frames(3); app.close()\n"
        "print('OK')\n"
    )
    result = subprocess.run([sys.executable, "-c", script], cwd=copy, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().endswith("OK")
