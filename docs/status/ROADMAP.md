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
| 10. Mapas nuevos por generación y camino más corto | Mapas aleatorios de navegación libre que cambian en cada generación; largo del camino más corto por mapa; eficiencia en las métricas y en el fitness | `test_map_generator`, `test_shortest_path`, `test_fitness`, `test_evaluation`, `test_training` | Cerrada (2026-11-15) |
| 11. Evasión de obstáculos a elección | Capa de evasión componible con cualquier navegación: aprendida, FTG y APF; navegación de referencia sin aprendizaje | `test_avoidance`, `test_architecture`, `test_app_smoke` | Cerrada (2026-11-15) |
| 12. Comparación estadística | Registro de la evasión y del tipo de mapas; colisiones, eficiencia y holgura; intervalo de confianza y prueba de significancia sobre la validación | `test_results`, `test_app_smoke` | Cerrada (2026-11-15) |
| 13. Interfaz clara y oscura | Dos temas monocromos con la misma disposición, cuatro secciones en la barra superior, algoritmos elegidos con tarjetas (ícono y escena aportados por cada plugin), comparación con barras | `test_theme`, `test_app_smoke`, `test_architecture` + capturas | Cerrada (2026-11-15) |

## Etapas siguientes (propuesta)

Ninguna está empezada ni aprobada: el orden y el alcance los decide el usuario,
editando esta tabla o creando una solicitud en `requests/open/`.

| Etapa | Objetivo | Se da por cerrada cuando |
|---|---|---|
| 14. Aplicación educativa | El rumbo que fijó el usuario y pidió postergar: explicar cada algoritmo dentro de la aplicación y mostrar lo que "piensa" (huecos de FTG, fuerzas de APF, tabla de reglas, feromonas) | A definir con el usuario |
| 15. Comparación con más rigor | Varias semillas por combinación, comparar más de dos corridas a la vez, exportar tablas | Las conclusiones no dependen de una sola semilla |
| 16. Revisión manual de la interfaz | Recorrer a mano cada vista en una ventana real y corregir lo que aparezca | Lista de comprobación completa |
| 17. Más algoritmos | Navegación: PSO, ABC. Evasión: DWA, VFH | Cada uno entra como plugin sin tocar nada fuera de su archivo o carpeta |
| 18. Rendimiento | Evaluar candidatos en procesos paralelos; entrenar en segundo plano | Una generación de 50 individuos tarda claramente menos que hoy |

Más ideas, sin orden ni compromiso: [BACKLOG.md](BACKLOG.md).
