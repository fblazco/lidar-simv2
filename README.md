# Simulador LiDAR con algoritmos evolutivos

Simulador 2D de un vehículo autónomo que detecta obstáculos con un LiDAR de 72
rayos y aprende a navegar mediante algoritmos evolutivos. Incluye un editor
visual de mapas en ASCII.

## Instalación

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
```

Si `venv` falla por falta de `ensurepip`, ver `docs/status/KNOWN_ISSUES.md`.

## Uso

```bash
.venv/bin/python main.py                          # ventana: editor (F1) y simulación (F2)
.venv/bin/python main.py train --generations 30   # entrenamiento sin ventana
.venv/bin/python -m pytest                        # pruebas
```

Documentación completa, estado del proyecto y cómo pedir cambios:
[docs/README.md](docs/README.md).
