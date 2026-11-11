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
| 6. Documentación viva | `CLAUDE.md`, `docs/` completo, informe de la tarea | — | Cerrada (2026-11-11) |

## Después de la primera versión

Primer paso recomendado: probar la interfaz a mano en una ventana real y ajustar lo que surja.

Ver [BACKLOG.md](BACKLOG.md). Los algoritmos PSO, ACO y ABC se incorporarán
como plugins nuevos en `optimization/<nombre>/` sin tocar simulador, móvil,
sensor ni editor.
