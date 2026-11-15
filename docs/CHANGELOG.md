# Changelog

Historial resumido. El detalle de cada tarea está en `reports/`.

## 0.3.0 — 2026-11-15

Mapas nuevos por generación, camino más corto y evasión con FTG y APF.
Informe: `reports/2026-11-15-mapas-aleatorios-ftg-apf.md`.

- Rumbo del proyecto: aplicación educativa y estadística para comparar
  algoritmos de camino más corto y de evasión (la parte educativa, postergada).
- Cada generación se entrena con mapas aleatorios nuevos; la validación pasa a
  20 mapas fijos. La colonia de rutas conserva mapas fijos.
- Los mapas aleatorios son de navegación libre por defecto, con obstáculos y
  paredes entre el inicio y el destino. Selector "Mapas" y `--maps`.
- Largo del camino más corto por mapa; eficiencia del camino y holgura mínima
  en las métricas; la eficiencia suma al fitness.
- Capa de evasión de obstáculos componible con cualquier navegación
  (`control/avoidance/`): aprendida, FTG (Follow the Gap) y APF (campos
  potenciales). Selector "Evasión" y `--avoidance`.
- Navegación de referencia sin aprendizaje (`reactive`), para medir FTG y APF
  por sí solos.
- Comparación estadística: colisiones, eficiencia, holgura, intervalo de
  confianza del éxito en validación y prueba de significancia. `main.py runs`
  muestra una tabla con todas las corridas.

## 0.2.0 — 2026-11-14

Algoritmo a elección, colonias de hormigas y comparación de corridas.
Informe: `reports/2026-11-14-seleccion-de-algoritmo-aco-y-comparacion.md`.

- El algoritmo de aprendizaje se elige en la ventana (selector en la vista de
  entrenamiento) y en la línea de comandos (`train --strategy`).
- Plugin `aco_rules`: colonia de hormigas que elige con feromonas una maniobra
  para cada situación; controlador `RuleTableController`.
- Plugin `aco_routes`: colonia de hormigas que traza una ruta por mapa;
  controlador `RouteController`; feromonas y rutas visibles durante el entrenamiento.
- Los entrenamientos tienen fin: límite de generaciones (`training.max_iterations`)
  o botón Finalizar. Al terminar se muestran sus estadísticas y se guardan en
  `logs/runs/`.
- Vista de resultados: resumen de una corrida o comparación de dos, con tabla y
  curvas superpuestas. En la terminal: `main.py runs` y `main.py compare`.
- Resumen al terminar un episodio de conducción manual.
- Contratos de optimización ampliados para soluciones que dependen del mapa
  (ADR-0005); la observación incluye la posición del vehículo.
- La prueba de independencia ahora borra cada algoritmo por separado y todos a la vez.

## 0.1.1 — 2026-11-12

Documentación completada. Informe: `reports/2026-11-12-completar-readme-y-docs.md`.

- `README.md` reescrito: qué hace, requisitos, instalación, inicio rápido,
  controles, entrenamiento sin ventana, configuración, estructura y estado.
- Capturas reales de la aplicación en `docs/images/`.
- Mapas de ejemplo `maps/ejemplo_ruta.json` y `maps/ejemplo_libre.json`.
- `docs/requests/README.md`: flujo y estados de una solicitud.
- Roadmap con las etapas siguientes propuestas; estado y problemas conocidos
  actualizados con los resultados de 40 generaciones de entrenamiento.
- `tests/test_docs.py`: enlaces de la documentación y mapas de ejemplo.

## 0.1.0 — 2026-11-11

Primera versión funcional. Informe: `reports/2026-11-11-primera-version-simulador.md`.

- Simulador 2D: vehículo cinemático, obstáculos estáticos y dinámicos
  (horizontal, vertical, circular), colisiones, navegación libre y por ruta.
- LiDAR geométrico de 72 rayos.
- Contrato `Controller`, control manual, política MLP y `ObservationBuilder`.
- Mapas en JSON, editor visual ASCII y generador aleatorio con semillas.
- Contrato `LearningStrategy` con plugins; evaluación por pasos; fitness;
  sesión de entrenamiento; checkpoints; registro por generación.
- Plugin GA: torneo, crossover configurable, mutación gaussiana, elitismo.
- Ventana única con modo Editor y modo Simulación (manual y entrenamiento con
  varios agentes visibles, estadísticas y gráfico de fitness).
- Entrenamiento sin ventana: `python main.py train`.
- 174 pruebas automáticas, incluidas las de independencia arquitectónica.
- Documentación viva: `CLAUDE.md` y `docs/`.
