# Changelog

Historial resumido. El detalle de cada tarea está en `reports/`.

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
