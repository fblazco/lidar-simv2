# Estado del proyecto

Última actualización: 2026-11-12 · Versión: primera versión funcional (0.1.0)

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
| Mapas de ejemplo `maps/ejemplo_ruta` y `maps/ejemplo_libre`, válidos y simulables | `test_docs` |
| Documentación con enlaces válidos y capturas reales de la aplicación | `test_docs` + revisión de las capturas |

### Aprendizaje observado (configuración por defecto: población 50, 3 escenarios)

| Corrida | Generación | Mejor fitness | Fitness promedio | Éxito en entrenamiento | Éxito en validación |
|---|---|---|---|---|---|
| Sin ventana (2026-11-11) | 1 | -2.8 | -30.4 | 0 % | 0 % |
| Sin ventana (2026-11-11) | 12 | 440.9 | 11.7 | 4 % | 20 % |
| Desde la ventana (`logs/entrenamiento_gui.jsonl`) | 40 | 655.0 | 263.7 | 38.7 % | 20 % |

Un mejor fitness de 655 significa que el mejor individuo llega al destino en
sus tres escenarios de entrenamiento. La validación (cinco mapas que no
intervienen en la selección) se queda en 20 %: lo aprendido todavía generaliza
poco. Ver `KNOWN_ISSUES.md` y la etapa 8 del `ROADMAP.md`.

## Parcialmente implementadas

| Funcionalidad | Qué falta |
|---|---|
| Interfaz gráfica | Verificada por pruebas automáticas y capturas con el driver `dummy`. El entrenamiento se usó en una ventana real durante 40 generaciones (hay registro y checkpoints), pero **falta un recorrido manual sistemático** de cada herramienta del editor, del teclado y del redimensionado. |
| Edición de obstáculos dinámicos | El centro de una órbita y la posición inicial no se pueden mover tras crearlos (hay que borrar y volver a crear). |
| Calidad del aprendizaje | El GA aprende a llegar en sus escenarios de entrenamiento (38.7 % de éxito en la generación 40), pero en validación llega solo en 1 de 5 mapas. No se ajustaron hiperparámetros ni se probó remuestrear escenarios. |

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
