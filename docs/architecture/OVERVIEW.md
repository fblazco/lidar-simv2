# Arquitectura: visión general

## Capas y dependencias

Qué importa cada paquete (grafo real, verificado por `tests/test_architecture.py`):

```
simulation            -> control.controller        (solo el contrato)
sensors               -> (nada del proyecto)
control               -> (nada del proyecto)
editor                -> simulation, control.controller
optimization          -> simulation, control
optimization/genetic  -> optimization (contratos), control
rendering             -> simulation, control.controller, pygame
bootstrap.py          -> simulation, sensors, editor, optimization
ui                    -> bootstrap, rendering, editor, control, optimization, pygame
main.py               -> bootstrap, config, optimization, ui
```

Nadie importa `optimization.genetic` por nombre: se descubre como plugin.

| Paquete | Responsabilidad | No puede importar |
|---|---|---|
| `control/` | Contrato `Controller`/`Action`/`Observation`, control manual, `ObservationBuilder`, política MLP | simulation, sensors, editor, optimization, pygame |
| `sensors/` | LiDAR por raycasting sobre arreglos NumPy | cualquier otro paquete del proyecto |
| `simulation/` | Mundo, móvil, obstáculos, colisiones, navegación, paso de tiempo | optimization, sensors, editor, pygame; de `control` solo `control.controller` |
| `editor/` | Modelo del editor, guardado/carga JSON, generador aleatorio | optimization, rendering, ui, pygame |
| `optimization/` | Contrato `LearningStrategy`, fitness, evaluación, sesión, checkpoints, registro de plugins | pygame, ui, rendering, y `optimization.genetic` |
| `optimization/genetic/` | Plugin GA | simulation, sensors, editor, pygame |
| `rendering/` | Dibujo ASCII en Pygame; solo lee el estado | optimization |
| `ui/` | Ventana, vistas, panel de entrenamiento | `optimization.genetic` |
| `bootstrap.py` | Único punto de ensamblado: construye objetos desde la configuración | `optimization.genetic`, pygame |

## Los tres conceptos

- **Simulador** (`simulation/`): `Simulation` avanza un `World` y sus `Mobile`
  con paso fijo. No sabe quién decide ni si alguien aprende.
- **Móvil** (`simulation/vehicle.py`): estado físico + modelo cinemático +
  sensor y controlador recibidos por el constructor.
- **Estrategia de aprendizaje** (`optimization/strategy.py`): contrato
  pedir/informar. `optimization/genetic/` es el único algoritmo concreto.

El puente entre una estrategia y el simulador es una `controller_factory`
(solución → `Controller`) que entrega cada plugin. Ver ADR-0002.

## Flujo de un paso de simulación

1. Para cada móvil activo: `Simulation` arma una `Observation` y le pide la
   acción a su controlador.
2. Avanza el tiempo y se mueven los obstáculos dinámicos.
3. Se integra el movimiento de cada móvil.
4. Se evalúan colisión, llegada al destino y límite de tiempo.
5. Cada móvil vuelve a medir con su LiDAR.

## Flujo de una generación

```
strategy.ask() ─► candidatos ─► Evaluator (N episodios por candidato, mismos escenarios)
                                   │  usa controller_factory + SimulationFactory
        strategy.tell(resultados) ◄┘  (antes se valida el mejor en escenarios aparte)
```

`TrainingSession.advance()` reparte ese trabajo en llamadas cortas: los
candidatos visibles avanzan unos pasos por cuadro y el resto se evalúa sin
dibujarse dentro de un presupuesto de tiempo. Sin ventana, `run_iteration()`
usa el mismo camino. Ver ADR-0003.

## Datos y persistencia

| Qué | Dónde | Formato |
|---|---|---|
| Parámetros | `config/default.json` (+ archivo del usuario) | JSON |
| Mapas | `maps/*.json` | JSON (`MapData.to_dict`) |
| Checkpoints | `models/*.npz` | NumPy + metadatos JSON, sin pickle |
| Registro de entrenamiento | `logs/*.jsonl` | una línea JSON por generación |

## Convenciones del mundo

- Unidades del mundo: una celda mide `cell_size` (1.0 por defecto). Eje Y hacia abajo.
- Ángulos en radianes; 0 apunta a +X; positivo gira hacia +Y (horario en pantalla).
- Cuerpos de colisión: vehículo y obstáculos dinámicos son círculos; cada
  obstáculo estático es el cuadrado de su celda; los bordes del mapa son paredes.
- Las posiciones de los obstáculos dinámicos son funciones cerradas del tiempo,
  así que la simulación es determinista y repetible.

## Cómo agregar un algoritmo (PSO, ACO, ABC…)

1. Crear `optimization/<nombre>/` con una clase que implemente `LearningStrategy`.
2. En su `__init__.py`, exponer `PLUGIN = StrategyPlugin(name, label, build)`,
   donde `build(config)` devuelve `StrategyBundle(strategy, controller_factory)`.
   - Si optimiza vectores reales (PSO, ABC): reutilizar
     `control.policy_controller.build_mlp_controller_factory(config)`.
   - Si construye otro tipo de solución (ACO): aportar su propio `Controller`
     y su propia fábrica.
3. Elegirlo con `training.strategy` en la configuración.

No hay que tocar `simulation/`, `sensors/`, `control/controller.py`, `editor/`
ni `ui/`: el registro lo descubre solo.
