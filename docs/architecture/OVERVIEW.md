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
rendering                -> simulation, control.controller, pygame
bootstrap.py             -> config, simulation, sensors, editor, optimization
ui                       -> bootstrap, config, rendering, editor, control, optimization, simulation, pygame
main.py                  -> bootstrap, config, optimization, ui
```

Nadie importa un algoritmo por nombre: los tres se descubren como plugins, y
ningún plugin importa a otro.

| Paquete | Responsabilidad | No puede importar |
|---|---|---|
| `control/` | Contrato `Controller`/`Action`/`Observation`, control manual, `ObservationBuilder`, política MLP, tabla de reglas, seguidor de rutas | simulation, sensors, editor, optimization, pygame |
| `sensors/` | LiDAR por raycasting sobre arreglos NumPy | cualquier otro paquete del proyecto |
| `simulation/` | Mundo, móvil, obstáculos, colisiones, navegación, paso de tiempo | optimization, sensors, editor, pygame; de `control` solo `control.controller` |
| `editor/` | Modelo del editor, guardado/carga JSON, generador aleatorio | optimization, rendering, ui, pygame |
| `optimization/` | Contrato `LearningStrategy`, fitness, evaluación, sesión, checkpoints, corridas y comparación, registro de plugins | pygame, ui, rendering, y cualquier plugin |
| `optimization/genetic/` | Plugin: algoritmo genético sobre los pesos de una red | simulation, sensors, editor, pygame, otros plugins |
| `optimization/aco_rules/` | Plugin: colonia de hormigas que asigna maniobras a situaciones | ídem |
| `optimization/aco_routes/` | Plugin: colonia de hormigas que traza una ruta por mapa | ídem |
| `rendering/` | Dibujo ASCII en Pygame; solo lee el estado | optimization |
| `ui/` | Ventana, vistas, panel de entrenamiento, resultados | cualquier plugin |
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

## Los tres algoritmos

| Plugin | Qué es una solución | Controlador | ¿Generaliza? |
|---|---|---|---|
| `genetic` | Vector de pesos de una red MLP | `PolicyController` | Sí: se valida en mapas no vistos |
| `aco_rules` | Tabla "situación → maniobra" (`RuleTable`) | `RuleTableController` | Sí |
| `aco_routes` | Una ruta de celdas por mapa | `RouteController` | No: una ruta solo sirve en su mapa |

Los dos primeros no usan el escenario para construir su controlador; el tercero
sí, y por eso existen los puntos de extensión de ADR-0005. Las dos colonias
están descritas en ADR-0006.

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

## Cómo agregar un algoritmo (PSO, ABC…)

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

No hay que tocar `simulation/`, `sensors/`, `editor/`, `ui/` ni `main.py`: el
registro lo descubre y aparece solo en el selector de la ventana y en
`--strategy`. `tests/test_architecture.py` comprueba que el proyecto siga
funcionando al borrar cualquier plugin.
