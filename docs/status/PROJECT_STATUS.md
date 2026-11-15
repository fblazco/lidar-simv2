# Estado del proyecto

Última actualización: 2026-11-14 · Versión: 0.2.0

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
| Algoritmo a elección del usuario: selector en la ventana y `train --strategy` en la terminal | `test_app_smoke`, `test_results`, `test_training` |
| Colonia de hormigas de reglas (`aco_rules`): feromonas por situación y maniobra, evaporación, depósito por ranking, heurística; controlador de tabla de reglas | `test_aco_rules`, `test_rule_controller`, `test_training` |
| Colonia de hormigas de rutas (`aco_routes`): una colonia por mapa, rutas celda a celda con giros de hasta 45°, feromonas por celda; controlador seguidor de rutas | `test_aco_routes`, `test_route_controller`, `test_training` |
| Feromonas y ruta de cada hormiga visibles durante el entrenamiento | `test_app_smoke` + captura |
| Fin de un entrenamiento: límite de generaciones o botón Finalizar; estadísticas al terminar; corrida guardada en `logs/runs/` | `test_training`, `test_app_smoke`, `test_results` |
| Comparación de dos corridas con las mismas métricas (ventana y `main.py compare`); lista de corridas (`main.py runs`) | `test_results`, `test_app_smoke` + captura |
| Resumen al terminar un episodio de conducción manual | `test_app_smoke` + captura |
| Conducir con lo aprendido por cualquiera de los tres algoritmos | `test_app_smoke`, `test_aco_routes` + captura |
| Fitness: avance, llegada, colisión, tiempo, desvío, suavidad; el vehículo detenido puntúa bajo | `test_fitness`, `test_evaluation` |
| Evaluación en varios escenarios, comparables dentro de la generación; semillas registradas; validación separada | `test_evaluation`, `test_training` |
| GA: población inicial, torneo, crossover (uniforme, un punto, mezcla), mutación gaussiana, elitismo, generación siguiente, estadísticas propias | `test_genetic_operators`, `test_genetic_algorithm` |
| Entrenamiento sin ventana (`main.py train`), sin importar Pygame | `test_training`, `test_cli` |
| Checkpoints: guardar y reanudar con resultados idénticos | `test_training`, `test_cli`, `test_app_smoke` |
| Reproducibilidad por semilla | `test_training`, `test_map_generator`, `test_simulation` |
| Ventana única con modo Editor y modo Simulación | `test_app_smoke` (driver de video `dummy`) + capturas |
| `VISIBLE_AGENTS` individuos visibles, cada uno con su propio mundo; el resto sin renderizado; no bloquea el ciclo de Pygame | `test_training`, `test_app_smoke` + captura |
| Estadísticas y gráfico de mejor fitness y fitness promedio | `test_app_smoke` + captura |
| El proyecto funciona al borrar cualquiera de los algoritmos, o todos | `test_architecture` (ejecuta copias sin esas carpetas) |
| Mapas de ejemplo `maps/ejemplo_ruta` y `maps/ejemplo_libre`, válidos y simulables | `test_docs` |
| Documentación con enlaces válidos y capturas reales de la aplicación | `test_docs` + revisión de las capturas |

### Resultados medidos

Corridas de referencia del 2026-11-14, sin ventana: 30 generaciones con cada
algoritmo, configuración por defecto (población 50, 3 mapas aleatorios por
individuo, 5 de validación), misma semilla (2024) y mismos mapas.

| Métrica | Genético | ACO reglas | ACO rutas |
|---|---|---|---|
| Mejor fitness | 658.7 | 670.2 | 661.6 |
| Generación del mejor fitness | 27 | 28 | 27 |
| Generación del primer éxito | 4 | 1 | 1 |
| Fitness promedio final | 270.1 | 290.4 | 491.5 |
| Tasa de éxito final (entrenamiento) | 39.3 % | 41.3 % | 72.7 % |
| Mejor tasa de éxito (entrenamiento) | 39.3 % | 55.3 % | 80.0 % |
| Éxito en validación (5 mapas no vistos) | 20.0 % | 40.0 % | no aplica |
| Colisiones en la última generación (de 150 episodios) | 65 | 88 | 38 |
| Tiempo por generación | 5.5 s | 5.0 s | 9.8 s |

Curvas (mejor fitness y tasa de éxito en entrenamiento):

- Genético: generación 1, -3 y 0 %; generación 10, 441 y 4 %; generación 20,
  644 y 27 %; generación 30, 659 y 39 %.
- ACO reglas: generación 1, 460 y 11 %; generación 10, 463 y 29 %; generación
  20, 668 y 46 %; generación 30, 670 y 41 %.
- ACO rutas: generación 1, 651 y 57 %; generación 10, 661 y 66 %; generación
  20, 661 y 71 %; generación 30, 662 y 73 %.

Cómo leerlo:

- Un mejor fitness por encima de 650 significa que el mejor individuo llega al
  destino en sus tres mapas de entrenamiento. Los tres algoritmos lo consiguen.
- **Genético y ACO reglas resuelven el mismo problema** (una política que sirve
  en cualquier mapa) y se comparan de igual a igual. En esta corrida la colonia
  de reglas llegó antes (generación 1 frente a 4) y generalizó mejor (40 %
  frente a 20 % en validación), aunque choca más.
- **ACO rutas resuelve otro problema**: planifica sobre mapas que conoce. Por eso
  llega mucho más a menudo en ellos y no tiene validación.
- Es una sola semilla: muestra que los tres funcionan y la tendencia, no un
  ganador. La generalización sigue siendo baja en todos (etapa 11 del roadmap).

Antes de esta versión, un entrenamiento hecho desde la ventana con el genético
había llegado a la generación 40 con mejor fitness 655.0, 38.7 % de éxito en
entrenamiento y 20 % en validación.

Para repetir las corridas:

```bash
.venv/bin/python main.py train --strategy genetic --generations 30
.venv/bin/python main.py train --strategy aco_rules --generations 30
.venv/bin/python main.py train --strategy aco_routes --generations 30
.venv/bin/python main.py compare genetic aco_rules
```

## Parcialmente implementadas

| Funcionalidad | Qué falta |
|---|---|
| Interfaz gráfica | Verificada por pruebas automáticas y capturas con el driver `dummy`. El entrenamiento con el genético se usó en una ventana real, pero **falta un recorrido manual** de las vistas nuevas (selector de algoritmo, Finalizar, resultados y comparación), de cada herramienta del editor, del teclado y del redimensionado. |
| Edición de obstáculos dinámicos | El centro de una órbita y la posición inicial no se pueden mover tras crearlos (hay que borrar y volver a crear). |
| Colonia de rutas con obstáculos móviles | Evita los fijos y espera a los móviles que cruzan; no resuelve los que recorren el propio camino (ver `KNOWN_ISSUES.md`). |
| Calidad del aprendizaje | Los tres algoritmos aprenden a llegar en sus mapas de entrenamiento, pero las políticas generalizan poco (20 % a 40 % de éxito en validación) y se midió una sola semilla. No se ajustaron hiperparámetros ni se probó remuestrear escenarios. |

## Pendientes

- PSO y ABC (previstos como plugins; no implementados a propósito).
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
| Ejemplo `ACORouteController` | El controlador se llama `RouteController` y está en `control/` | No depende de ACO: sigue la ruta de cualquier planificador. |
| "Agregar un algoritmo no debe exigir modificar la física ni el móvil" | La colonia de rutas necesitó que la observación incluyera la posición (dos líneas en `simulation/environment.py`) y ampliar contratos de `optimization/` | La física y el móvil no cambiaron. Detalle en ADR-0005. La colonia de reglas no necesitó ningún cambio fuera de su carpeta y de `control/`. |
| Evaluar en varios escenarios y validar en mapas no vistos | La colonia de rutas aprende una ruta por mapa: se evalúa en varios mapas pero no se valida | Es inherente a planificar rutas; el usuario pidió incluir esta variante. La comparación muestra "no aplica". |
| "Estadísticas cuando se finalice una simulación" | Se muestran al finalizar un entrenamiento y, además, al terminar un episodio manual | La frase admitía las dos lecturas; se cubrieron ambas. |
