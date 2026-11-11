# Estado del proyecto

Última actualización: 2026-11-11 · Versión: primera versión funcional (0.1.0)

Solo figura como implementado lo que fue verificado. "Verificado con" indica la
prueba automática o la comprobación realizada.

## Implementadas

| Funcionalidad | Verificado con |
|---|---|
| Vehículo de movimiento continuo (posición, orientación, velocidad, dirección, aceleración, frenado) | `test_vehicle` |
| Obstáculos estáticos y dinámicos (horizontal, vertical, circular; velocidad, extremos, centro y radio, pausas, sentido); se atraviesan entre sí | `test_obstacles` |
| Colisiones del vehículo con obstáculos estáticos, dinámicos y bordes | `test_collision`, `test_simulation` |
| LiDAR de 72 rayos, 360°, 5° de separación, alcance configurable, distancias 0..1, detecta estáticos y dinámicos | `test_lidar`, `test_simulation` |
| Navegación libre y seguimiento de ruta con un único simulador; ruta como waypoints ordenados | `test_navigation`, `test_simulation` |
| Varios móviles independientes con controladores distintos | `test_simulation` |
| Contrato `Controller` (`observe`, `act`, `reset`), control manual, política MLP, `ObservationBuilder` como única fuente de dimensiones | `test_controllers` |
| Mapas: modelo, validación, guardado y carga en JSON | `test_map_manager` |
| Generador de mapas aleatorios válidos y reproducibles por semilla | `test_map_generator` |
| Editor (modelo): caminos por arrastre, borrar, obstáculos, inicio con orientación, destino, redimensionar | `test_map_editor` |
| Vista ASCII con los símbolos especificados | `test_ascii` + capturas |
| Configuración externa en JSON | `test_config` |
| Contrato `LearningStrategy` (pedir/informar) y plugins descubiertos automáticamente | `test_architecture`, `test_training` |
| Fitness: avance, llegada, colisión, tiempo, desvío, suavidad; el vehículo detenido puntúa bajo | `test_fitness`, `test_evaluation` |
| Evaluación en varios escenarios, comparables dentro de la generación; semillas registradas; validación separada | `test_evaluation`, `test_training` |
| GA: población inicial, torneo, crossover (uniforme, un punto, mezcla), mutación gaussiana, elitismo, generación siguiente, estadísticas propias | `test_genetic_operators`, `test_genetic_algorithm` |
| Entrenamiento sin ventana (`main.py train`), sin importar Pygame | `test_training`, `test_cli` |
| Checkpoints: guardar y reanudar con resultados idénticos | `test_training`, `test_cli`, `test_app_smoke` |
| Reproducibilidad por semilla | `test_training`, `test_map_generator`, `test_simulation` |
| Ventana única con modo Editor y modo Simulación | `test_app_smoke` (driver de video `dummy`) + capturas |
| `VISIBLE_AGENTS` individuos visibles, cada uno con su propio mundo; el resto sin renderizado; no bloquea el ciclo de Pygame | `test_training`, `test_app_smoke` + captura |
| Estadísticas y gráfico de mejor fitness y fitness promedio | `test_app_smoke` + captura |
| El simulador funciona sin `optimization/genetic/` | `test_architecture` (ejecuta una copia sin esa carpeta) |

Aprendizaje observado: con la configuración por defecto (población 50, 3
escenarios), en 12 generaciones el mejor fitness pasó de -2.8 a 440.9 y la
validación de -11.5 a 143.7 (≈ 4.5 s por generación sin ventana). Detalle en
`reports/2026-11-11-primera-version-simulador.md`.

## Parcialmente implementadas

| Funcionalidad | Qué falta |
|---|---|
| Interfaz gráfica | Verificada por pruebas automáticas y capturas con el driver `dummy`; **no se probó a mano en una ventana real** (mouse, teclado, redimensionado). |
| Edición de obstáculos dinámicos | El centro de una órbita y la posición inicial no se pueden mover tras crearlos (hay que borrar y volver a crear). |
| Calidad del aprendizaje | El GA mejora de forma sostenida, pero no se ajustaron hiperparámetros ni se midió la tasa de éxito a largo plazo. |

## Pendientes

- PSO, ACO y ABC (previstos como plugins; no implementados a propósito).
- Todo lo listado en [BACKLOG.md](BACKLOG.md).

## En desarrollo

Nada en este momento.

## Diferencias respecto de la especificación

| Especificación | Implementación | Motivo y consecuencia |
|---|---|---|
| Árbol sugerido: `optimization/genetic/fitness.py` | `optimization/fitness.py` | El fitness es común a todos los algoritmos (ADR-0004). Borrar el plugin GA no afecta la evaluación. |
| Árbol sugerido: `editor/map_editor.py` como editor visual | `editor/map_editor.py` es el modelo sin Pygame; la vista está en `ui/editor_view.py` | Permite probar el editor sin ventana y mantiene Pygame solo en `rendering/` y `ui/`. |
| Módulos no previstos en el árbol | `bootstrap.py`, `simulation/map_data.py`, `navigation.py`, `factory.py`, `geometry.py`, `control/policy.py`, `optimization/training.py`, `checkpoint.py`, `registry.py`, `ui/editor_view.py`, `simulation_view.py`, `widgets.py` | Separan responsabilidades que el árbol no detallaba. La especificación permite adaptar los nombres. |
| "Las 72 distancias LiDAR" como entradas | La red recibe proximidad (`1 - distancia`); el sensor sigue entregando distancias 0..1 | Con "nada cerca = 0" el GA aprende más fácil. Se cambia en `ObservationBuilder`. |
| Checkpoints | Archivo `.npz` (NumPy) con metadatos JSON | Un genoma en JSON ocupa varias veces más. Mapas y configuración sí son JSON. |
| Móviles en un mismo mundo | No colisionan entre sí ni se ven con el LiDAR | La especificación pide móviles independientes; la interacción está en el backlog. |
| Entrenamiento en la ventana | Solo avanza mientras la vista de entrenamiento está abierta | Simplicidad; ejecutarlo en segundo plano está en el backlog. |
