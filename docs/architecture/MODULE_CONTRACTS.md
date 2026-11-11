# Contratos de los módulos

Interfaces públicas y responsabilidades. Los nombres son los del código.

## Controlador — `control/controller.py`

Lo único que el simulador conoce de quien decide.

```python
class Action:        steering: float; acceleration: float      # ambos en [-1, 1]
class Observation:   lidar, lidar_previous                      # arreglos 0..1, uno por rayo
                     heading, speed, max_speed
                     goal_distance, goal_bearing                # ángulos relativos al vehículo
                     waypoint_distance, waypoint_bearing
                     path_deviation, path_heading_error
                     navigation_mode                            # "free" | "route"
                     lidar_range, time
class Controller:    reset(); observe(observation); act(observation) -> Action
```

- `reset()` se llama al empezar cada episodio; `observe()` antes de cada `act()`.
- Un controlador no importa Pygame ni el simulador.
- Implementaciones: `ManualController` (`set_command(steering, acceleration)`;
  la interfaz traduce el teclado) y `PolicyController(policy, observation_builder)`.

### `ObservationBuilder` — `control/observation_builder.py`

`build(observation) -> vector` acotado en [-1, 1] y `size` (única fuente de las
dimensiones de entrada). `feature_names` describe cada posición. El LiDAR se
codifica como proximidad (`1 - distancia`); `use_previous_lidar` agrega la
medición anterior.

### Política — `control/policy.py`, `control/policy_controller.py`

- `MLPPolicy(layer_sizes)`: `set_parameters(vector)`, `get_parameters()`,
  `__call__(entradas) -> salidas` (tanh), `parameter_count(layer_sizes)`.
- `MLPControllerFactory(builder, hidden_layers)`: `parameter_count` y
  `__call__(vector) -> PolicyController`. Es la `controller_factory` de
  cualquier optimizador de vectores reales.

## Sensor — `sensors/lidar.py`

```python
Lidar(num_rays=72, fov_deg=360, max_range=8.0)
scan(x, y, heading, circles, boxes, bounds) -> distancias normalizadas 0..1
hit_points(x, y, heading, scan) -> puntos finales de cada rayo
```

Recibe geometría como arreglos (`circles`: x, y, radio; `boxes`: xmin, ymin,
xmax, ymax; `bounds`: ancho, alto). No conoce `World`. El móvil acepta como
sensor cualquier objeto con `scan`, `num_rays` y `max_range`.

## Simulador — `simulation/`

| Elemento | Contrato |
|---|---|
| `MapData` (`map_data.py`) | Descripción serializable del escenario. `route` es la lista ordenada de celdas. `to_dict/from_dict`, `validate() -> problemas`, `path_cells()`. |
| `DynamicObstacleSpec` | `kind`, posición inicial, `speed`, `direction`, `pause`, `range_min/max`, `center_x/y`, `orbit_radius`, `radius`. |
| `DynamicObstacle` (`obstacle.py`) | `position_at(t)`: función cerrada del tiempo. |
| `World` (`world.py`) | Construido desde `MapData`. `boxes`, `circles`, `route`, `goal`, `start_pose`, `set_time(t)`. |
| `Route`, `Navigator` (`navigation.py`) | Proyección sobre la ruta, avance 0..1, waypoint adelantado, desvío. Un mismo `Navigator` cubre los dos modos. |
| `Mobile` (`vehicle.py`) | `Mobile(params, sensor, controller)`. `state`, `status`, `scan`, `last_action`, `distance_traveled`, `navigation`. `apply(action, dt)` integra el movimiento. |
| `collision.py` | `collides(world, x, y, radius)` y sus partes. |
| `Simulation` (`environment.py`) | `step()`, `reset()`, `done`, `time`, `mobiles`, `world`, `observation_for(mobile)`. Varios móviles independientes en un mundo. |
| `SimulationFactory` (`factory.py`) | `create(map_data, controllers) -> Simulation`; recibe la fábrica de sensores por inyección. |

Garantías: paso fijo `dt`; determinista; no importa `optimization`, `sensors`
ni Pygame; `Status` ∈ {ACTIVE, COLLIDED, REACHED_GOAL, TIMED_OUT}.

## Estrategia de optimización — `optimization/strategy.py`

```python
class Candidate:        id: int; solution: Any          # opaca para el resto del sistema
class CandidateResult:  candidate; fitness; episodes
class LearningStrategy:
    iteration -> int                     # iteraciones completadas
    ask() -> list[Candidate]             # idempotente hasta el próximo tell
    tell(results)                        # exige el resultado de todos los pedidos
    best() -> (solution, fitness) | None
    statistics() -> dict[str, float]     # propias del algoritmo
    get_state() -> StrategyState(meta, arrays); set_state(state)
```

Una estrategia no toca la física ni el renderizado, y no impone representación.

### Plugins — `optimization/registry.py`

`StrategyPlugin(name, label, build)` y `StrategyBundle(strategy,
controller_factory)`. `discover_plugins()` importa cada subpaquete de
`optimization/` que exponga `PLUGIN`. Nadie importa un algoritmo por nombre.

## Evaluador — `optimization/evaluation.py`, `optimization/fitness.py`

- `Scenario(map_data, seed, label)`.
- `Evaluator(simulation_factory, controller_factory, fitness, settings)`:
  `evaluate(candidates, scenarios)` bloqueante; `start(candidate, scenarios) ->
  CandidateEvaluation` por pasos.
- `CandidateEvaluation`: `step()`, `done`, `partial_fitness`, `simulation`
  (mundo propio, legible para dibujarlo), `episode_index`, `result()`.
- `EpisodeMetrics` y `FitnessFunction(weights)`: puntaje de un episodio y
  `aggregate` (media entre escenarios). Un episodio sin avance durante
  `stall_time` se corta como `stalled`; esa regla es de la evaluación, no del
  simulador.

El evaluador no sabe qué algoritmo produjo los candidatos.

## Sesión de entrenamiento — `optimization/training.py`

- `ScenarioProvider`: semillas de entrenamiento (iguales para todos los
  candidatos de una iteración) y de validación (flujo separado), más mapas fijos.
- `TrainingSession`: `advance(visible_steps, time_budget) -> IterationStats |
  None`, `run_iteration()`, `visible`, `history`, `best_controller()`,
  `get_state()/set_state()`.
- `IterationStats`: estadísticas generales, semillas usadas y las propias de la
  estrategia. `TrainingLog` las escribe como JSON por línea.
- `optimization/checkpoint.py`: `save_checkpoint` / `load_checkpoint`.

## Editor — `editor/`

- `MapEditor` (`map_editor.py`): operaciones de edición sin interfaz
  (`add_route_cell`, `erase`, `add_static`, `add_dynamic`, `update_dynamic`,
  `set_start`, `point_start_towards`, `set_goal`, `resize`…). `revision` cambia
  con cada edición.
- `MapManager` (`map_manager.py`): `save`, `load`, `list_maps`; `MapFormatError`.
- `MapGenerator` (`map_generator.py`): `generate(seed) -> MapData` válido y reproducible.

## Renderizado e interfaz — `rendering/`, `ui/`

- `rendering/ascii_renderer.py`: `route_glyphs`, `ascii_grid` (puras, sin Pygame).
- `rendering/renderer.py`: `Viewport` y `WorldRenderer`; solo leen el estado.
- `ui/application.py`: `Application(config, base_dir)`, `run()`, `set_mode()`.
- `ui/editor_view.py`, `ui/simulation_view.py`, `ui/training_panel.py`, `ui/widgets.py`.
