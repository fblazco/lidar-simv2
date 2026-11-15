"""Punto de entrada.

    python main.py                                    abre la aplicación (editor + simulación)
    python main.py train --strategy genetic --avoidance ftg   entrena sin ventana con la combinación elegida
    python main.py runs                               lista las corridas terminadas
    python main.py compare genetic aco_rules          compara dos corridas
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from bootstrap import (available_avoidance, available_strategies, build_training_session, finish_run,
                       load_training_session, save_training_session, with_choices)
from config import load_config
from control.avoidance import DEFAULT as LEARNED
from optimization.results import MAP_MODES, format_comparison, format_summary, list_runs, load_run
from optimization.training import TrainingLog

PROJECT_DIR = Path(__file__).resolve().parent


def runs_dir(base_dir) -> Path:
    return Path(base_dir) / "logs" / "runs"


def run_gui(args) -> None:
    from ui.application import Application   # Pygame solo se importa si hay ventana

    Application(load_config(args.config), base_dir=args.base_dir).run()


def run_training(args) -> None:
    base = Path(args.base_dir)
    if args.resume:
        session, config = load_training_session(args.resume)
        print(f"Reanudando desde {args.resume} (generación {session.strategy.iteration})")
    else:
        config = with_choices(load_config(args.config), args.strategy, args.avoidance, args.maps)
        session = build_training_session(config)
    default_name = session.strategy.name + ("" if session.avoidance == LEARNED else f"_{session.avoidance}")
    name = args.name or default_name
    session.visible_agents = 0                # sin ventana no hay agentes visibles
    checkpoint = base / "models" / f"{name}.npz"
    log = TrainingLog(base / "logs" / f"{name}.jsonl")
    every = config["training"].get("checkpoint_every", 0)
    validation_seeds = session.scenarios.validation_seeds() if session.strategy.generalizes else "no aplica"
    resampling = "nuevos en cada generación" if session.scenarios.resample_every else "fijos"
    print(f"Navegación: {session.strategy.name} | evasión: {session.avoidance} | "
          f"mapas: {config['generator']['navigation_mode']}, {resampling} | semilla: {session.scenarios.seed}")
    print(f"Semillas de validación: {validation_seeds}")
    try:
        for _ in range(args.generations):
            stats = session.run_iteration()
            log.append(stats)
            validation = f"{stats.validation_fitness:7.1f}" if stats.validation_fitness is not None else "   -   "
            print(f"gen {stats.iteration:4d} | mejor {stats.best_fitness:7.1f} | media {stats.mean_fitness:7.1f} | "
                  f"éxito {stats.success_rate * 100:5.1f}% | colisiones {stats.collisions:3d} | "
                  f"validación {validation} | {stats.seconds:5.1f} s", flush=True)
            if every and stats.iteration % every == 0:
                save_training_session(session, checkpoint, config)
    except KeyboardInterrupt:
        print("\nInterrumpido: se guarda la última generación completa.")
    save_training_session(session, checkpoint, config)
    record = finish_run(session, config, runs_dir(base), name)
    if record is not None:
        print(f"\nResumen de la corrida '{record.run_id}'\n{format_summary(record)}")
    print(f"\nCheckpoint: {checkpoint}\nRegistro:   {log.path}\nCorrida:    {runs_dir(base) / (name + '.json')}")


def find_run(base_dir, reference: str):
    """Una corrida por nombre (en logs/runs/) o por ruta a su archivo."""
    for path in (Path(reference), runs_dir(base_dir) / f"{reference}.json"):
        if path.is_file():
            return load_run(path)
    raise ValueError(f"No existe la corrida '{reference}'. Usa `python main.py runs` para ver las disponibles.")


def show_runs(args) -> None:
    records = list_runs(runs_dir(args.base_dir))
    if not records:
        print("No hay corridas terminadas todavía.")
        return
    avoiders, strategies = available_avoidance(), available_strategies()
    rows = [("corrida", "navegación", "evasión", "gen.", "éxito val.", "IC 95 %", "colis. val.", "efic. val.", "éxito entr.")]
    for record in records:
        metrics = record.metrics()

        def percent(key):
            return "-" if metrics[key] is None else f"{metrics[key] * 100:.0f} %"

        interval = metrics["validation_interval"]
        rows.append((
            record.run_id,
            strategies[record.strategy].short_label if record.strategy in strategies else record.strategy,
            avoiders[record.avoidance].short_label if record.avoidance in avoiders else record.avoidance,
            str(metrics["iterations"]),
            percent("validation_success_rate"),
            "-" if interval is None else f"{interval[0] * 100:.0f}-{interval[1] * 100:.0f} %",
            percent("validation_collision_rate"),
            percent("validation_efficiency"),
            percent("recent_success_rate"),
        ))
    widths = [max(len(row[i]) for row in rows) for i in range(len(rows[0]))]
    for row in rows:
        print("  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)).rstrip())


def show_comparison(args) -> None:
    print(format_comparison(find_run(args.base_dir, args.first), find_run(args.base_dir, args.second)))
    print("\n* mejor valor de la fila")


def main(argv=None) -> None:
    strategies = ", ".join(sorted(available_strategies())) or "ninguno instalado"
    avoiders = ", ".join(available_avoidance())
    parser = argparse.ArgumentParser(
        description="Simulador 2D de navegación autónoma con LiDAR y algoritmos evolutivos")
    parser.add_argument("--config", help="archivo JSON con los parámetros que se quieren cambiar")
    parser.add_argument("--base-dir", default=str(PROJECT_DIR), help="carpeta que contiene maps/, models/ y logs/")
    commands = parser.add_subparsers(dest="command")

    train = commands.add_parser("train", help="entrenar sin ventana gráfica")
    train.add_argument("--strategy", help=f"algoritmo de navegación ({strategies}); por defecto, el de la configuración")
    train.add_argument("--avoidance", help=f"algoritmo de evasión de obstáculos ({avoiders})")
    train.add_argument("--maps", choices=sorted(MAP_MODES), help="tipo de mapas aleatorios: libres, con ruta o mixtos")
    train.add_argument("--generations", type=int, default=10)
    train.add_argument("--config", help="archivo JSON con los parámetros que se quieren cambiar")
    train.add_argument("--resume", help="checkpoint .npz desde el que continuar")
    train.add_argument("--name", help="nombre del checkpoint, del registro y de la corrida (por defecto, el del algoritmo)")
    train.add_argument("--base-dir", default=str(PROJECT_DIR))

    runs = commands.add_parser("runs", help="listar las corridas terminadas")
    runs.add_argument("--base-dir", default=str(PROJECT_DIR))

    compare = commands.add_parser("compare", help="comparar dos corridas terminadas")
    compare.add_argument("first", help="nombre de la corrida A (o ruta a su archivo .json)")
    compare.add_argument("second", help="nombre de la corrida B")
    compare.add_argument("--base-dir", default=str(PROJECT_DIR))

    args = parser.parse_args(argv)
    actions = {"train": run_training, "runs": show_runs, "compare": show_comparison}
    try:
        actions.get(args.command, run_gui)(args)
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
