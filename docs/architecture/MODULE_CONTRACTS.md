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
                     x, y                                       # posición absoluta
class Controller:    reset(); observe(observation); act(observation) -> Action
```

- `reset()` se llama al empezar cada episodio; `observe()` antes de cada `act()`.
- Un controlador no importa Pygame ni el simulador.
- Implementaciones: `ManualController` (`set_command(steering, acceleration)`;
  la interfaz traduce el teclado), `PolicyController(policy, observation_builder)`,
  `RuleTableController`, `RouteController`, `GoalSeekingController` (referencia:
  apunta al waypoint) y `AvoidanceController` (cualquiera de los anteriores más
  un evasor).

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

### Tabla de reglas — `control/rule_controller.py`

- `ObservationDiscretizer(num_rays, fov_deg, near_distance, mid_distance)`:
  `encode(observation) -> situación` y `decode(situación) -> (dirección del
  objetivo, izquierda, frente, derecha)`. 5 direcciones del waypoint por 3
  niveles de cercanía (cerca, medio, libre) en 3 sectores del LiDAR: 135
  situaciones (`size`).
- `default_maneuvers()`: 15 maniobras (5 direcciones por acelerar, avanzar
  despacio o frenar).
- `RuleTable(actions, visits)`: una maniobra por situación; el controlador anota
  en `visits` las situaciones que se presentaron al conducir.
- `RuleTableController(table, discretizer, maneuvers)` y
  `RuleControllerFactory` (`n_states`, `n_actions`, `__call__(table)`).

### Seguidor de rutas — `control/route_controller.py`

`RouteController(waypoints, num_rays, fov_deg, cruise_speed, lookahead,
safety_margin, reaction_time)`. Persigue el punto situado `lookahead` por delante
sobre la ruta, usando la posición de la observación, y frena cuando el LiDAR ve
algo dentro del corredor que va a ocupar. `planned_path` expone la ruta para
dibujarla. Es el "controlador de rutas" que la especificación anticipaba para
ACO; no depende de quién planificó la ruta.

### Evasión de obstáculos — `control/avoidance/`

```python
class ObstacleAvoider:   reset(); adjust(observation, proposal: Action) -> Action
class AvoidanceController(inner: Controller, avoider: ObstacleAvoider)   # es un Controller
with_avoidance(controller_factory, make_avoider) -> controller_factory
AvoidancePlugin(name, label, short_label, description, build(config) -> ObstacleAvoider | None)
discover_avoidance() -> {nombre: AvoidancePlugin}       # "learned" primero
```

- La propuesta de la navegación se lee como intención: `intended_direction(action)`
  convierte la dirección (-1..1) en un ángulo relativo de hasta ±90°. El evasor
  devuelve la orden final de dirección y nunca acelera más que la propuesta.
- `goal_in_sight(observation, angles, reach)`: si el destino está más cerca que
  cualquier obstáculo en el corredor hacia él, el evasor no interviene.
- `FollowTheGap` (`ftg.py`): obstáculos = rayos más cortos que `free_distance`;
  se agrandan con el radio del vehículo más `safety_margin`; hueco = tramo de
  rayos libres dentro de `view_deg`; se encara el centro del más ancho,
  ponderado con la dirección deseada por `alpha / d_min` y `beta`.
- `PotentialFields` (`apf.py`): atracción constante hacia la dirección deseada;
  repulsión `repulsion * (1/d - 1/d0) / d^2` por cada rayo dentro de
  `influence_distance`; más una componente `tangential` (campo de vórtice) para
  rodear lo que está al frente. `force(observation, wanted)` expone la resultante.
- `learned.py`: su `build` devuelve `None`; no se agrega ninguna capa.
- `control/rays.py`: `relative_ray_angles(num_rays, fov_deg)`, la geometría de
  los rayos que comparten todos los controladores.

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
| `MapData` (`map_data.py`) | Descripción serializable del escenario. `route` es la lista ordenada de celdas. `to_dict/from_dict`, `validate() -> problemas`, `path_cells()`, `fingerprint()` (huella del contenido). |
| `DynamicObstacleSpec` | `kind`, posición inicial, `speed`, `direction`, `pause`, `range_min/max`, `center_x/y`, `orbit_radius`, `radius`. |
| `DynamicObstacle` (`obstacle.py`) | `position_at(t)`: función cerrada del tiempo. |
| `World` (`world.py`) | Construido desde `MapData`. `boxes`, `circles`, `route`, `goal`, `start_pose`, `set_time(t)`. |
| `Route`, `Navigator` (`navigation.py`) | Proyección sobre la ruta, avance 0..1, waypoint adelantado, desvío. Un mismo `Navigator` cubre los dos modos. `shortest_path_length(map_data)`: largo del camino más corto (el dibujado en modo ruta; entre los obstáculos fijos en modo libre). |
| `Mobile` (`vehicle.py`) | `Mobile(params, sensor, controller)`. `state`, `status`, `scan`, `last_action`, `distance_traveled`, `navigation`. `apply(action, dt)` integra el movimiento. |
| `collision.py` | `collides(world, x, y, radius)` y sus partes. |
| `Simulation` (`environment.py`) | `step()`, `reset()`, `done`, `time`, `mobiles`, `world`, `observation_for(mobile)`. Varios móviles independientes en un mundo. |
| `SimulationFactory` (`factory.py`) | `create(map_data, controllers) -> Simulation`; recibe la fábrica de sensores por inyección. |

Garantías: paso fijo `dt`; determinista; no importa `optimization`, `sensors`
ni Pygame; `Status` ∈ {ACTIVE, COLLIDED, REACHED_GOAL, TIMED_OUT}.

## Estrategia de optimización — `optimization/strategy.py`

```python
class Candidate:        id: int; solution: Any          # opaca para el resto del sistema
class CandidateResult:  candidate; fitness; episodes; scores   # scores: fitness de cada episodio
class LearningStrategy:
    # núcleo obligatorio
    iteration -> int                     # iteraciones completadas
    ask() -> list[Candidate]             # idempotente hasta el próximo tell
    tell(results)                        # exige el resultado de todos los pedidos
    best() -> (solution, fitness) | None
    statistics() -> dict[str, float]     # propias del algoritmo
    get_state() -> StrategyState(meta, arrays); set_state(state)
    # puntos de extensión opcionales
    generalizes = True                   # False: lo aprendido solo sirve en sus mapas (no se valida)
    prepare(scenarios)                   # se llama antes de cada ask() con los escenarios de la iteración
    cell_heatmap(scenario) -> array | None   # intensidad 0..1 por celda, para dibujarla
```

Una estrategia no toca la física ni el renderizado, y no impone representación.
`UnknownScenarioError` indica que una solución no sabe conducir un mapa.

### Plugins — `optimization/registry.py`

`StrategyPlugin(name, label, build, short_label, description, stat_labels)` y
`StrategyBundle(strategy, controller_factory)`, donde `controller_factory` es
`(solución, escenario) -> Controller`. `for_any_scenario(fábrica)` adapta las que
no dependen del escenario. `discover_plugins()` importa cada subpaquete de
`optimization/` que exponga `PLUGIN`. Nadie importa un algoritmo por nombre.

### Los tres plugins

- `optimization/genetic/`: `GeneticAlgorithm` (torneo, crossover, mutación
  gaussiana, elitismo) sobre vectores reales.
- `optimization/aco_rules/`: `RuleColony(heuristic, ants, config, seed)`.
  Feromona por (situación, maniobra); `build_heuristic` aporta el conocimiento
  previo; depositan las mejores hormigas, solo en las situaciones que visitaron.
- `optimization/aco_routes/`: `RouteColonies` mantiene un `MapColony` por mapa
  (feromona por celda, `construct`, `update`, `heatmap`). Cada hormiga lleva una
  ruta por escenario; `RouteControllerFactory` elige la del escenario evaluado.
- `optimization/reactive/`: `GoalSeeking`, estrategia de referencia que no
  aprende: un único candidato por iteración, conducido por `GoalSeekingController`.

## Evaluador — `optimization/evaluation.py`, `optimization/fitness.py`

- `Scenario(map_data, seed, label)` con `key` (la huella del mapa) y
  `reference_length` (largo del camino más corto, calculado una vez).
- `Evaluator(simulation_factory, controller_factory, fitness, settings)`:
  `evaluate(candidates, scenarios)` bloqueante; `start(candidate, scenarios) ->
  CandidateEvaluation` por pasos. Crea un controlador por episodio con
  `controller_factory(solución, escenario)`.
- `CandidateEvaluation`: `step()`, `done`, `partial_fitness`, `simulation`
  (mundo propio, legible para dibujarlo), `episode_index`, `result()`.
- `EpisodeMetrics` y `FitnessFunction(weights)`: puntaje de un episodio y
  `aggregate` (media entre escenarios). Las métricas incluyen
  `reference_length`, `path_efficiency` (camino más corto / recorrido, solo si
  llegó) y `min_clearance` (lo más cerca que el LiDAR vio un obstáculo). Un episodio sin avance durante
  `stall_time` se corta como `stalled`; esa regla es de la evaluación, no del
  simulador.

El evaluador no sabe qué algoritmo produjo los candidatos.

## Sesión de entrenamiento — `optimization/training.py`

- `ScenarioProvider`: semillas de entrenamiento (iguales para todos los
  candidatos de una iteración) y de validación (flujo separado), más mapas fijos.
- `TrainingSession`: `advance(visible_steps, time_budget) -> IterationStats |
  None`, `run_iteration()`, `visible`, `history`, `finished` (llegó a
  `max_iterations`), `best_controller(map_data)`, `training_maps()`,
  `get_state()/set_state()`.
- `IterationStats`: estadísticas generales, semillas usadas, eficiencia del
  camino, holgura mínima, detalle de la validación (episodios, colisiones,
  eficiencia, tiempo al destino) y las propias de la estrategia. `TrainingLog` las escribe como JSON por línea.
- `optimization/checkpoint.py`: `save_checkpoint` / `load_checkpoint`.

## Corridas y comparación — `optimization/results.py`

- `RunRecord`: navegación, evasión, tipo de mapas, semillas, población e
  historial completo de una corrida terminada; `metrics()` deriva las cifras de
  resumen.
- `wilson_interval(llegadas, total)`: intervalo de confianza del éxito en
  validación. `validation_significance(a, b)`: prueba z de dos proporciones
  sobre la última validación de dos corridas, redactada como frase.
- `summary_rows(record)` y `compare_runs(a, b)`: filas listas para mostrar; la
  comparación indica qué corrida es mejor en cada métrica.
- `save_run`, `load_run`, `list_runs`, `format_summary`, `format_comparison`.
- `bootstrap.finish_run(session, config, directory, run_id)` crea y guarda el
  registro de una sesión. `bootstrap.with_choices(config, strategy, avoidance,
  map_mode)` aplica las elecciones del usuario; `available_avoidance()` lista
  los evasores.

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
- `ui/editor_view.py`, `ui/simulation_view.py`, `ui/training_panel.py`,
  `ui/results_view.py`, `ui/widgets.py`.
- El renderizador dibuja, si existen, el `cell_heatmap` de la estrategia y la
  `planned_path` del controlador de cada móvil, sin saber de qué algoritmo vienen.
