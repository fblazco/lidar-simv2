# Informe: primera versión del simulador

Fecha: 2026-11-11

## 1. Objetivo de la tarea

Construir desde cero (el repositorio estaba vacío) la primera versión funcional
del simulador 2D de navegación autónoma con LiDAR y algoritmos evolutivos
descrita en `docs/specification/`, con GA como primer plugin de optimización, y
dejar instalada la documentación viva del proyecto.

## 2. Qué se implementó

- **Simulación** (`simulation/`): modelo de mapa serializable, mundo, vehículo
  cinemático, obstáculos dinámicos con trayectorias cerradas en el tiempo,
  colisiones, navegación libre y por ruta, simulación con N móviles.
- **Sensor** (`sensors/lidar.py`): raycasting vectorizado contra círculos, cajas
  y bordes.
- **Control** (`control/`): contrato `Controller`, control manual,
  `ObservationBuilder`, política MLP y fábrica de controladores.
- **Mapas** (`editor/`): guardado y carga en JSON, modelo del editor, generador
  aleatorio con semillas.
- **Optimización** (`optimization/`): contrato `LearningStrategy`, registro de
  plugins, fitness, evaluación por pasos, sesión de entrenamiento, checkpoints
  y registro por generación.
- **GA** (`optimization/genetic/`): genoma, torneo, tres crossovers, mutación
  gaussiana, elitismo.
- **Interfaz** (`rendering/`, `ui/`): ventana única con modo Editor y modo
  Simulación (manual y entrenamiento con agentes visibles, estadísticas, gráfico).
- **Entrada** (`main.py`, `bootstrap.py`, `config/`): aplicación con ventana y
  entrenamiento sin ventana; configuración externa en JSON.
- **Documentación**: `CLAUDE.md`, `README.md` y `docs/`.

## 3. Archivos creados

- Raíz: `main.py`, `bootstrap.py`, `conftest.py`, `pytest.ini`,
  `requirements.txt`, `requirements-dev.txt`, `.gitignore`, `README.md`, `CLAUDE.md`.
- `config/`: `__init__.py`, `default.json`.
- `simulation/`: `geometry.py`, `map_data.py`, `obstacle.py`, `navigation.py`,
  `vehicle.py`, `world.py`, `collision.py`, `environment.py`, `factory.py`.
- `sensors/`: `lidar.py`.
- `control/`: `controller.py`, `manual_controller.py`, `observation_builder.py`,
  `policy.py`, `policy_controller.py`.
- `optimization/`: `strategy.py`, `fitness.py`, `evaluation.py`, `training.py`,
  `checkpoint.py`, `registry.py`.
- `optimization/genetic/`: `__init__.py`, `genome.py`, `selection.py`,
  `crossover.py`, `mutation.py`, `genetic_algorithm.py`.
- `editor/`: `map_manager.py`, `map_editor.py`, `map_generator.py`.
- `rendering/`: `ascii_renderer.py`, `renderer.py`.
- `ui/`: `widgets.py`, `editor_view.py`, `simulation_view.py`,
  `training_panel.py`, `application.py`.
- `tests/`: `helpers.py` y 20 archivos `test_*.py`.
- `docs/`: toda la estructura (especificación, arquitectura con 4 ADR, estado,
  solicitudes, este informe, changelog y guía de uso).
- Carpetas de datos vacías: `maps/`, `models/`, `logs/`.

## 4. Archivos modificados

Ninguno: el repositorio no tenía archivos ni commits previos.

## 5. Decisiones técnicas adoptadas

Las arquitectónicas están en `docs/architecture/decisions/` (ADR-0001 a 0004).
Además:

- Cuerpos de colisión: vehículo y obstáculos dinámicos como círculos; cada
  obstáculo estático como el cuadrado de su celda; bordes del mapa como paredes.
- Vehículo: modelo de bicicleta simplificado, sin marcha atrás por defecto.
- Paso de simulación fijo de 0.05 s; el renderizado no interviene en la física.
- Fitness por defecto: 100 por recorrido completo, +500 por llegar, hasta +100
  por rapidez, -20 por colisión, -30 por quedarse sin avanzar, hasta -30 por
  desvío y hasta -10 por control brusco. Un episodio sin avance durante 4 s se
  corta (regla de la evaluación, no del simulador).
- Escenarios: 3 mapas aleatorios fijos por candidato y 5 de validación con otro
  flujo de semillas; se pueden remuestrear cada N generaciones y sumar mapas propios.
- Red por defecto: 157 entradas (72 + 72 del LiDAR anterior + 13), 16 ocultas,
  2 salidas: 2562 parámetros.
- Checkpoints en `.npz` con metadatos JSON, sin pickle.
- Entorno: se creó `.venv` con `--without-pip` porque el sistema no tiene
  `ensurepip`; `pytest.ini` desactiva plugins de pytest de ROS que el entorno
  inyecta por `PYTHONPATH`.
- Las diferencias respecto de la especificación están en `status/PROJECT_STATUS.md`.

## 6. Pruebas ejecutadas y resultados

Se trabajó por etapas, escribiendo cada grupo de pruebas antes del código y
comprobando que fallaban (por módulos inexistentes) antes de implementarlo.

| Comprobación | Resultado |
|---|---|
| `.venv/bin/python -m pytest` (suite completa, 20 archivos) | **174 pasaron, 0 fallaron** (≈ 9 s) |
| Entrenamiento sin ventana, configuración por defecto, 12 generaciones | Mejor fitness -2.8 → 440.9; validación -11.5 → 143.7; ≈ 4.5 s por generación |
| `python main.py train --generations 3` | Terminó bien; escribió `models/demo.npz` y `logs/demo.jsonl`; mismos valores que la corrida anterior (reproducible) |
| Reanudar desde checkpoint | Idéntico a entrenar de corrido (`test_training`, `test_cli`) |
| Copia del proyecto sin `optimization/genetic/` | Simulación, editor y aplicación funcionan; cero plugins (`test_architecture`) |
| Capturas del editor, la conducción manual y el entrenamiento con 4 agentes | Revisadas visualmente; se corrigieron tres detalles de diseño del panel |

Fallos encontrados y corregidos durante el desarrollo: rayos del LiDAR paralelos
a un eje devolvían distancia 0 (corregido, cubierto por `test_lidar`); dos
pruebas tenían expectativas mal planteadas (glifos de esquina y orden de
`set_command` respecto del reinicio del episodio) y se corrigieron las pruebas.

**No ejecutado:** la aplicación no se abrió en una ventana real. La interfaz se
verificó con el driver de video `dummy` de SDL (pruebas automáticas y capturas),
no con mouse y teclado de verdad.

## 7. Limitaciones conocidas

Ver `status/KNOWN_ISSUES.md`. Las principales: interfaz sin prueba manual; los
móviles de un mismo mundo no interactúan; el entrenamiento en la ventana solo
avanza con la vista de entrenamiento abierta; hiperparámetros sin ajustar.

## 8. Tareas pendientes y recomendaciones

1. Abrir `python main.py` y probar a mano el editor y el entrenamiento.
2. Entrenar más generaciones (`main.py train --generations 100`) para ver hasta
   dónde llega la tasa de éxito con los valores por defecto.
3. Decidir el siguiente algoritmo (PSO es el más directo: reutiliza la fábrica
   de controladores MLP).
4. Resto de ideas en `status/BACKLOG.md`.
