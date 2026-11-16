# Arquitectura: visión general

## Capas y dependencias

Qué importa cada paquete (grafo real, verificado por `tests/test_architecture.py`):

```
simulation               -> control.controller        (solo el contrato)
sensors                  -> (nada del proyecto)
control                  -> (nada del proyecto)
editor                   -> simulation, control.controller
optimization             -> simulation, control
optimization/genetic     -> optimization (contratos), control
optimization/aco_rules   -> optimization (contratos), control
optimization/aco_routes  -> optimization (contratos), control
optimization/reactive    -> optimization (contratos), control
rendering                -> simulation, control.controller, pygame
bootstrap.py             -> config, simulation, sensors, editor, optimization
ui                       -> bootstrap, config, rendering, editor, control, optimization, simulation, pygame
main.py                  -> bootstrap, config, optimization, ui
```

Nadie importa un algoritmo por nombre: los de navegación (`optimization/<nombre>/`)
y los de evasión (`control/avoidance/<nombre>.py`) se descubren como plugins, y
ningún plugin importa a otro.

| Paquete | Responsabilidad | No puede importar |
|---|---|---|
| `control/` | Contrato `Controller`/`Action`/`Observation`, control manual, `ObservationBuilder`, política MLP, tabla de reglas, seguidor de rutas, navegación de referencia | simulation, sensors, editor, optimization, pygame |
| `control/avoidance/` | Capa de evasión de obstáculos: contrato `ObstacleAvoider`, FTG, APF y el registro que los descubre | simulation, sensors, editor, optimization, pygame |
| `sensors/` | LiDAR por raycasting sobre arreglos NumPy | cualquier otro paquete del proyecto |
| `simulation/` | Mundo, móvil, obstáculos, colisiones, navegación, paso de tiempo | optimization, sensors, editor, pygame; de `control` solo `control.controller` |
| `editor/` | Modelo del editor, guardado/carga JSON, generador aleatorio | optimization, rendering, ui, pygame |
| `optimization/` | Contrato `LearningStrategy`, fitness, evaluación, sesión, checkpoints, corridas y comparación, registro de plugins | pygame, ui, rendering, y cualquier plugin |
| `optimization/genetic/` | Plugin: algoritmo genético sobre los pesos de una red | simulation, sensors, editor, pygame, otros plugins |
| `optimization/aco_rules/` | Plugin: colonia de hormigas que asigna maniobras a situaciones | ídem |
| `optimization/aco_routes/` | Plugin: colonia de hormigas que traza una ruta por mapa | ídem |
| `optimization/reactive/` | Plugin de referencia: navegación sin aprendizaje | ídem |
| `rendering/` | Dibujo ASCII en Pygame con una paleta clara y otra oscura; escenas explicativas; solo lee el estado | optimization, ui |
| `ui/` | Ventana, temas, componentes, vistas e íconos propios | cualquier plugin |
| `bootstrap.py` | Único punto de ensamblado: construye objetos desde la configuración | cualquier plugin, pygame |

## Los tres conceptos

- **Simulador** (`simulation/`): `Simulation` avanza un `World` y sus `Mobile`
  con paso fijo. No sabe quién decide ni si alguien aprende.
- **Móvil** (`simulation/vehicle.py`): estado físico + modelo cinemático +
  sensor y controlador recibidos por el constructor.
- **Estrategia de aprendizaje** (`optimization/strategy.py`): contrato
  pedir/informar. Hay tres algoritmos concretos, cada uno en su carpeta.

El puente entre una estrategia y el simulador es una `controller_factory`
(solución, escenario → `Controller`) que entrega cada plugin. Ver ADR-0002 y ADR-0005.

## Flujo de un paso de simulación

1. Para cada móvil activo: `Simulation` arma una `Observation` y le pide la
   acción a su controlador.
2. Avanza el tiempo y se mueven los obstáculos dinámicos.
3. Se integra el movimiento de cada móvil.
4. Se evalúan colisión, llegada al destino y límite de tiempo.
5. Cada móvil vuelve a medir con su LiDAR.

## Flujo de una generación

```
strategy.prepare(escenarios)          (opcional: para algoritmos que dependen del mapa)
strategy.ask() ─► candidatos ─► Evaluator: un episodio por escenario, los mismos para todos
                                   │  controller_factory(solución, escenario) + SimulationFactory
        strategy.tell(resultados) ◄┘  (antes se valida el mejor en mapas aparte, si el algoritmo generaliza)
```

`TrainingSession.advance()` reparte ese trabajo en llamadas cortas: los
candidatos visibles avanzan unos pasos por cuadro y el resto se evalúa sin
dibujarse dentro de un presupuesto de tiempo. Sin ventana, `run_iteration()`
usa el mismo camino. Ver ADR-0003.

Un entrenamiento termina al llegar a `training.max_iterations` o cuando el
usuario lo finaliza. `bootstrap.finish_run` guarda entonces su registro
(`optimization/results.py`), que es lo que se resume y se compara.

## Dos elecciones independientes: navegación y evasión

Un controlador de entrenamiento se arma con dos piezas que el usuario elige por
separado:

```
Observación ─► navegación (decide a dónde ir) ─► propuesta ─► evasión (corrige para no chocar) ─► Acción
```

**Navegación** (`training.strategy`): plugins de `optimization/`.

| Plugin | Qué es una solución | Controlador | ¿Generaliza? |
|---|---|---|---|
| `genetic` | Vector de pesos de una red MLP | `PolicyController` | Sí: se valida en mapas no vistos |
| `aco_rules` | Tabla "situación → maniobra" (`RuleTable`) | `RuleTableController` | Sí |
| `aco_routes` | Una ruta de celdas por mapa | `RouteController` | No: una ruta solo sirve en su mapa |
| `reactive` | Nada: no aprende | `GoalSeekingController` | Sí (referencia) |

**Evasión** (`training.avoidance`): plugins de `control/avoidance/`.

| Plugin | Qué hace |
|---|---|
| `learned` | Ninguna capa: la navegación se ocupa de los obstáculos con lo que percibe |
| `ftg` | Follow the Gap: encara el hueco más ancho que ve el LiDAR |
| `apf` | Campos potenciales: el destino atrae, los obstáculos repelen |

`bootstrap` compone ambas: si la evasión elegida aporta un `ObstacleAvoider`,
envuelve la fábrica de controladores de la navegación con `with_avoidance`. El
evasor interpreta la dirección propuesta como "hacia dónde quiere ir" la
navegación y devuelve la orden final. Así cualquier navegación se combina con
cualquier evasión, y la referencia sin aprendizaje permite medir FTG y APF por
sí solos. Ver ADR-0007.

## Mapas de entrenamiento y camino más corto

- Los mapas aleatorios son de navegación libre por defecto (sin camino
  dibujado), con obstáculos repartidos en torno a la recta inicio-destino.
- Con `resample_scenarios_every = 1` cada generación se evalúa en mapas nuevos:
  lo aprendido no puede memorizar un mapa. Las estrategias que no generalizan
  (`aco_routes`) conservan mapas fijos.
- El conjunto de validación es fijo y nunca interviene en la selección: es la
  vara común para comparar corridas.
- `Scenario.reference_length` es el largo del camino más corto del mapa; la
  eficiencia de un episodio es ese largo dividido por lo recorrido, y forma
  parte del fitness. Ver ADR-0008.

## Datos y persistencia

| Qué | Dónde | Formato |
|---|---|---|
| Parámetros | `config/default.json` (+ archivo del usuario) | JSON |
| Mapas | `maps/*.json` | JSON (`MapData.to_dict`) |
| Checkpoints | `models/*.npz` | NumPy + metadatos JSON, sin pickle |
| Registro de entrenamiento | `logs/*.jsonl` | una línea JSON por generación |
| Corridas terminadas | `logs/runs/*.json` | resumen e historial completo (`RunRecord`) |

## Convenciones del mundo

- Unidades del mundo: una celda mide `cell_size` (1.0 por defecto). Eje Y hacia abajo.
- Ángulos en radianes; 0 apunta a +X; positivo gira hacia +Y (horario en pantalla).
- Cuerpos de colisión: vehículo y obstáculos dinámicos son círculos; cada
  obstáculo estático es el cuadrado de su celda; los bordes del mapa son paredes.
- Las posiciones de los obstáculos dinámicos son funciones cerradas del tiempo,
  así que la simulación es determinista y repetible.

## Cómo agregar un algoritmo de navegación (PSO, ABC…)

1. Crear `optimization/<nombre>/` con una clase que implemente `LearningStrategy`
   (`iteration`, `ask`, `tell`, `best`, `statistics`, `get_state`, `set_state`).
2. En su `__init__.py`, exponer `PLUGIN = StrategyPlugin(name, label, build,
   short_label, description, stat_labels)`, donde `build(config)` devuelve
   `StrategyBundle(strategy, controller_factory)`.
   - Si sus soluciones no dependen del mapa (PSO o ABC sobre los pesos de la
     red): `for_any_scenario(build_mlp_controller_factory(config))`.
   - Si dependen del mapa: una fábrica `(solución, escenario) -> Controller`,
     `generalizes = False` y, si hace falta, `prepare(escenarios)`.
3. Agregar su sección de parámetros en `config/default.json`.

## Cómo agregar un algoritmo de evasión (DWA, VFH…)

1. Crear `control/avoidance/<nombre>.py` con una clase que implemente
   `ObstacleAvoider.adjust(observación, propuesta) -> Action`.
2. En el mismo archivo, exponer `PLUGIN = AvoidancePlugin(name, label,
   short_label, description, build)`, donde `build(config)` crea el evasor.
3. Agregar sus parámetros en la sección `avoidance` de `config/default.json`.

En los dos casos se puede sumar, en la misma carpeta, un ícono y una escena:
`icon` es la ruta de un SVG de un solo color (la interfaz lo tiñe con el color
del tema) y `demo` la de un JSON con una escena del algoritmo funcionando (ver
`MODULE_CONTRACTS.md`). Son opcionales: sin ellos la tarjeta muestra la inicial
del nombre y la descripción.

En ambos casos no hay que tocar `simulation/`, `sensors/`, `editor/`, `ui/` ni
`main.py`: el registro los descubre y aparecen solos en los selectores de la
ventana (una tarjeta por algoritmo) y en `--strategy` / `--avoidance`. `tests/test_architecture.py`
comprueba que el proyecto siga funcionando al borrar cualquier plugin de
navegación.
