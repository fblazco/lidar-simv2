# Estado del proyecto

Última actualización: 2026-11-15 · Versión: 0.3.0

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
| Conducir con lo aprendido por cualquiera de los algoritmos | `test_app_smoke`, `test_aco_routes` + captura |
| Mapas aleatorios nuevos en cada generación; validación fija de 20 mapas; mapas fijos para las estrategias que no generalizan | `test_training` |
| Mapas aleatorios de navegación libre con obstáculos y paredes entre inicio y destino; selector de tipo de mapas (libres, con ruta, mixtos) | `test_map_generator`, `test_app_smoke` |
| Largo del camino más corto por mapa; eficiencia del camino y holgura mínima en las métricas; eficiencia en el fitness | `test_shortest_path`, `test_fitness`, `test_evaluation` |
| Evasión de obstáculos a elección, componible con cualquier navegación: aprendida, FTG (Follow the Gap) y APF (campos potenciales) | `test_avoidance`, `test_app_smoke` |
| Navegación de referencia sin aprendizaje, para medir FTG y APF por sí solos | `test_avoidance` |
| Comparación estadística: colisiones, eficiencia, holgura, intervalo de confianza del éxito en validación y prueba de significancia; tabla de todas las corridas en `main.py runs` | `test_results`, `test_app_smoke` + captura |
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

Corridas de referencia del 2026-11-15, sin ventana: 30 generaciones de cada
combinación con la configuración por defecto (población 50, 3 mapas de
navegación libre nuevos en cada generación, 20 mapas de validación) y la misma
semilla (2024). "Éxito en validación" es la fracción de los 20 mapas no vistos
en que llega el mejor individuo de la última generación.

| Navegación | Evasión | Éxito en validación | IC 95 % | Colisiones en validación | Eficiencia del camino | Tiempo al destino | Éxito en entrenamiento (últ. 10 gen.) | Tiempo por generación |
|---|---|---|---|---|---|---|---|---|
| Genético | Aprendida | 75 % | 53–89 % | 25 % | 92 % | 8.1 s | 53 % | 5.1 s |
| Genético | FTG | 75 % | 53–89 % | 15 % | 93 % | 10.0 s | 56 % | 7.8 s |
| Genético | APF | 70 % | 48–85 % | 15 % | 85 % | 10.9 s | 69 % | 8.4 s |
| ACO reglas | Aprendida | 55 % | 34–74 % | 45 % | 99 % | 7.5 s | 36 % | 3.8 s |
| ACO reglas | FTG | 90 % | 70–97 % | 5 % | 96 % | 8.8 s | 76 % | 7.2 s |
| ACO reglas | APF | 70 % | 48–85 % | 25 % | 96 % | 10.6 s | 78 % | 8.2 s |
| Sin aprender | Ninguna | 0 % | 0–16 % | 100 % | no aplica | no aplica | 0 % | 0.3 s |
| Sin aprender | FTG | 70 % | 48–85 % | 15 % | 96 % | 13.0 s | 73 % | 1.2 s |
| Sin aprender | APF | 70 % | 48–85 % | 20 % | 95 % | 13.9 s | 63 % | 1.3 s |
| ACO rutas | Propia (frena) | no aplica | no aplica | no aplica | 91 % | no aplica | 91 % | 8.0 s |

Lectura:

- **Los mapas exigen esquivar.** Sin evasión, la navegación de referencia no
  llega en ninguno de los 20 mapas de validación.
- **FTG y APF solos**, sin aprender nada, llegan en 14 de 20.
- **El genético** que aprende a esquivar por sí mismo llega en 15 de 20. Con FTG
  empata en éxito y choca menos (15 % frente a 25 %).
- **La colonia de reglas es la que más cambia con la evasión:** 11 de 20
  aprendiendo sola y 18 de 20 con FTG, la mejor combinación de esta tanda. Esa
  diferencia sí es estadísticamente significativa (p = 0.013).
- **Casi todas las demás diferencias no son significativas** con 20 mapas: los
  intervalos de confianza se solapan (por ejemplo, 15 frente a 14 da p = 0.72).
- **Camino más corto:** la eficiencia va de 85 % a 99 %; el genético con APF es
  el que más rodea. Con evasión aprendida se llega antes (7.5 a 8.1 s) que con
  FTG o APF (8.8 a 13.9 s), porque las capas clásicas frenan cerca de los obstáculos.
- **La colonia de rutas** llega en el 91 % de los episodios sobre sus tres mapas
  fijos; no tiene validación porque su ruta no sirve en otro mapa.

Es una sola semilla. Sirve para ver que todas las combinaciones funcionan y la
tendencia general, no para declarar un ganador.

Para repetir una corrida y compararla:

```bash
.venv/bin/python main.py train --strategy aco_rules --avoidance ftg --generations 30
.venv/bin/python main.py train --strategy aco_rules --avoidance learned --generations 30
.venv/bin/python main.py compare aco_rules_ftg aco_rules
```

Las corridas de la versión 0.2.0 usaban tres mapas fijos con ruta dibujada: el
genético llegaba entonces en el 20 % de sus 5 mapas de validación y la colonia
de reglas en el 40 %. No son comparables de forma directa con estas (otros
mapas, otra tarea), pero el cambio a mapas nuevos por generación es lo que
buscaba mejorar esa generalización.

## Parcialmente implementadas

| Funcionalidad | Qué falta |
|---|---|
| Interfaz gráfica | Verificada por pruebas automáticas y capturas con el driver `dummy`. **Falta un recorrido manual** en una ventana real de las vistas nuevas (selectores de navegación, evasión y mapas; Finalizar; resultados y comparación), de cada herramienta del editor, del teclado y del redimensionado. |
| Edición de obstáculos dinámicos | El centro de una órbita y la posición inicial no se pueden mover tras crearlos (hay que borrar y volver a crear). |
| Colonia de rutas con obstáculos móviles | Evita los fijos y espera a los móviles que cruzan; no resuelve los que recorren el propio camino (ver `KNOWN_ISSUES.md`). |
| Calidad de la comparación | Se midió una sola semilla y 20 mapas de validación: los intervalos de confianza son anchos y casi ninguna diferencia entre combinaciones es significativa. No se ajustaron hiperparámetros de los algoritmos de navegación. |

## Pendientes

- Parte educativa de la aplicación (postergada a pedido del usuario; etapa 13 del roadmap).
- PSO y ABC en navegación; DWA y VFH en evasión (previstos como plugins).
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
| "Mapas aleatorios para cada generación" | Vale para el genético, la colonia de reglas y la referencia; la colonia de rutas conserva mapas fijos | Aprende una ruta por mapa: con mapas nuevos empezaría de cero en cada generación. |
| "Encontrar el camino más corto" | Los mapas aleatorios pasaron a navegación libre por defecto y se mide la eficiencia del camino | Con el camino ya dibujado no hay nada que encontrar. Los mapas con ruta siguen disponibles. Decisión tomada sin poder consultar al usuario (ADR-0008). |
| FTG y APF | FTG usa el centro angular del hueco; APF suma una componente tangencial; ambos dejan de intervenir con el destino a la vista | Sin esos ajustes chocaban o no llegaban a destinos cercanos a una pared (ADR-0007). |
| "Elegir distintos algoritmos" de evasión | Se agregó además una navegación sin aprendizaje | Sin ella no se puede medir FTG o APF por sí solos. |
| Aplicación educativa | No se trabajó | El usuario pidió postergarla; está registrada como rumbo y como etapa 13 del roadmap. |
