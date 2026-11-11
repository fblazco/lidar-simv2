"""Punto de entrada.

    python main.py                         abre la aplicación (editor + simulación)
    python main.py train --generations 20  entrena sin ventana gráfica
"""
from __future__ import annotations

import argparse
from pathlib import Path

from bootstrap import build_training_session, load_training_session, save_training_session
from config import load_config
from optimization.training import TrainingLog

PROJECT_DIR = Path(__file__).resolve().parent


def run_gui(args) -> None:
    from ui.application import Application   # Pygame solo se importa si hay ventana

    Application(load_config(args.config), base_dir=args.base_dir).run()


def run_training(args) -> None:
    base = Path(args.base_dir)
    if args.resume:
        session, config = load_training_session(args.resume)
        print(f"Reanudando desde {args.resume} (generación {session.strategy.iteration})")
    else:
        config = load_config(args.config)
        session = build_training_session(config)
    session.visible_agents = 0                # sin ventana no hay agentes visibles
    checkpoint = base / "models" / f"{args.name}.npz"
    log = TrainingLog(base / "logs" / f"{args.name}.jsonl")
    every = config["training"].get("checkpoint_every", 0)
    print(f"Estrategia: {session.strategy.name} | semilla: {session.scenarios.seed} | "
          f"semillas de validación: {session.scenarios.validation_seeds()}")
    try:
        for _ in range(args.generations):
            stats = session.run_iteration()
            log.append(stats)
            validation = f"{stats.validation_fitness:7.1f}" if stats.validation_fitness is not None else "   -   "
            print(f"gen {stats.iteration:4d} | mejor {stats.best_fitness:7.1f} | media {stats.mean_fitness:7.1f} | "
                  f"éxito {stats.success_rate * 100:5.1f}% | colisiones {stats.collisions:3d} | "
                  f"validación {validation} | evaluaciones {stats.evaluations}", flush=True)
            if every and stats.iteration % every == 0:
                save_training_session(session, checkpoint, config)
    except KeyboardInterrupt:
        print("\nInterrumpido: se guarda la última generación completa.")
    save_training_session(session, checkpoint, config)
    print(f"Checkpoint: {checkpoint}\nRegistro:   {log.path}")


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Simulador 2D de navegación autónoma con LiDAR y algoritmos evolutivos")
    parser.add_argument("--config", help="archivo JSON con los parámetros que se quieren cambiar")
    parser.add_argument("--base-dir", default=str(PROJECT_DIR), help="carpeta que contiene maps/, models/ y logs/")
    commands = parser.add_subparsers(dest="command")
    train = commands.add_parser("train", help="entrenar sin ventana gráfica")
    train.add_argument("--generations", type=int, default=10)
    train.add_argument("--config", help="archivo JSON con los parámetros que se quieren cambiar")
    train.add_argument("--resume", help="checkpoint .npz desde el que continuar")
    train.add_argument("--name", default="entrenamiento", help="nombre del checkpoint y del registro")
    train.add_argument("--base-dir", default=str(PROJECT_DIR))
    args = parser.parse_args(argv)
    if args.command == "train":
        run_training(args)
    else:
        run_gui(args)


if __name__ == "__main__":
    main()
