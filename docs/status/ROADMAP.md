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

## Etapas siguientes (propuesta)

Ninguna está empezada ni aprobada: el orden y el alcance los decide el usuario,
editando esta tabla o creando una solicitud en `requests/open/`.

| Etapa | Objetivo | Se da por cerrada cuando |
|---|---|---|
| 7. Revisión manual de la interfaz | Recorrer a mano cada herramienta del editor y cada control de la simulación en una ventana real, y corregir lo que aparezca | Lista de comprobación completa, sin fallos abiertos en `KNOWN_ISSUES.md` |
| 8. Generalización del aprendizaje | Que lo aprendido sirva en mapas no vistos: medir el efecto de remuestrear escenarios y de usar más escenarios por individuo; ajustar fitness y operadores | La tasa de éxito en validación se acerca a la de entrenamiento (hoy 20 % frente a 39 %) |
| 9. Segundo algoritmo: PSO | Plugin `optimization/pso/` que reutiliza la fábrica de controladores MLP; elegir la estrategia desde la interfaz | PSO entrena con y sin ventana sin modificar `simulation/`, `sensors/`, `control/controller.py` ni `editor/` |
| 10. ABC y ACO | Plugins restantes; ACO con su propio controlador de rutas | Igual que la etapa 9 para cada uno |
| 11. Rendimiento | Evaluar candidatos en procesos paralelos; entrenar en segundo plano | Una generación de 50 individuos tarda claramente menos que hoy (≈ 4.5 s sin ventana) |

Más ideas, sin orden ni compromiso: [BACKLOG.md](BACKLOG.md).
