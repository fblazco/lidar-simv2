# Roadmap

Etapas de desarrollo. Cada etapa se implementa con pruebas primero y solo se
da por cerrada cuando sus pruebas pasan. El estado verificado de cada
funcionalidad vive en [PROJECT_STATUS.md](PROJECT_STATUS.md).

| Etapa | Objetivo | Pruebas que la cierran | Estado |
|---|---|---|---|
| 1. Núcleo de simulación | Vehículo cinemático, obstáculos estáticos/dinámicos, colisiones, LiDAR de 72 rayos, navegación (libre y ruta), `Simulation` con N móviles | `test_vehicle`, `test_obstacles`, `test_collision`, `test_lidar`, `test_navigation`, `test_simulation` | Cerrada (2026-11-11) |
| 2. Controladores | Contrato `Controller`, control manual, `ObservationBuilder`, política MLP | `test_controllers` | Cerrada (2026-11-11) |
| 3. Mapas | Modelo `MapData`, guardado/carga JSON, generador aleatorio con semillas, modelo del editor, vista ASCII | `test_map_manager`, `test_map_generator`, `test_map_editor`, `test_ascii` | Cerrada (2026-11-11) |
| 4. Optimización | Contrato `LearningStrategy`, fitness, evaluador por pasos, sesión de entrenamiento, checkpoints, plugin GA | `test_fitness`, `test_evaluation`, `test_genetic_operators`, `test_genetic_algorithm`, `test_training`, `test_architecture` | Cerrada (2026-11-11) |
| 5. Interfaz | Ventana única con modo Editor y modo Simulación (manual + entrenamiento con N agentes visibles, estadísticas y gráfico) | `test_app_smoke` + revisión visual | Cerrada (2026-11-11) |
| 6. Documentación viva | `CLAUDE.md`, `docs/` completo, informe de la tarea | `test_docs` (enlaces, capturas del README, mapas de ejemplo) | Cerrada (2026-11-11) |
| 7. Selección de algoritmo | El usuario elige el algoritmo en la ventana y en la línea de comandos; contratos ampliados para soluciones que dependen del mapa | `test_training`, `test_evaluation`, `test_architecture`, `test_app_smoke`, `test_results` | Cerrada (2026-11-14) |
| 8. Colonias de hormigas | Plugins `aco_rules` (reglas de conducción) y `aco_routes` (rutas por mapa) con sus controladores | `test_aco_rules`, `test_rule_controller`, `test_aco_routes`, `test_route_controller` | Cerrada (2026-11-14) |
| 9. Resultados y comparación | Estadísticas al finalizar una corrida, corridas guardadas y comparación de dos | `test_results`, `test_app_smoke` | Cerrada (2026-11-14) |

## Etapas siguientes (propuesta)

Ninguna está empezada ni aprobada: el orden y el alcance los decide el usuario,
editando esta tabla o creando una solicitud en `requests/open/`.

| Etapa | Objetivo | Se da por cerrada cuando |
|---|---|---|
| 10. Revisión manual de la interfaz | Recorrer a mano cada herramienta del editor y cada control de la simulación en una ventana real, y corregir lo que aparezca | Lista de comprobación completa, sin fallos abiertos en `KNOWN_ISSUES.md` |
| 11. Generalización del aprendizaje | Que lo aprendido sirva en mapas no vistos: medir el efecto de remuestrear escenarios y de usar más escenarios por individuo; ajustar fitness, operadores y la tabla de reglas | La tasa de éxito en validación se acerca a la de entrenamiento |
| 12. PSO | Plugin `optimization/pso/` que reutiliza la fábrica de controladores MLP | PSO entrena y se compara con los demás sin modificar nada fuera de su carpeta |
| 13. ABC | Plugin `optimization/abc/` con employed, onlooker y scout bees | Igual que la etapa 12 |
| 14. Rendimiento | Evaluar candidatos en procesos paralelos; entrenar en segundo plano | Una generación de 50 individuos tarda claramente menos que hoy |

Más ideas, sin orden ni compromiso: [BACKLOG.md](BACKLOG.md).
