# Informe: algoritmo a elección, colonias de hormigas y comparación de corridas

Fecha: 2026-11-14 · Solicitud: `docs/requests/done/2026-11-14-seleccion-de-algoritmo-aco-y-comparacion.md`

## 1. Objetivo de la tarea

Que el simulador pueda entrenar al móvil con distintos algoritmos a elección del
usuario; agregar un algoritmo de colonia de hormigas; mostrar estadísticas al
finalizar una simulación y permitir comparar dos corridas distintas.

Antes de implementar se le planteó al usuario una contradicción de la
especificación sobre qué debía aprender la colonia (ver la solicitud). Eligió
implementar **las dos variantes**.

## 2. Qué se implementó

- **Selección de algoritmo.** Selector en la vista de entrenamiento y
  `train --strategy` en la terminal. Los algoritmos se descubren como plugins,
  así que el selector y la ayuda de la terminal se llenan solos.
- **Colonia de hormigas de reglas (`aco_rules`).** Las hormigas eligen con
  feromonas una maniobra para cada una de 135 situaciones (dirección del
  waypoint y cercanía de obstáculos en tres sectores del LiDAR). El resultado es
  una tabla de reglas que sirve en cualquier mapa.
- **Colonia de hormigas de rutas (`aco_routes`).** Una colonia por mapa traza
  rutas celda a celda con feromonas en la grilla; un controlador las conduce en
  el simulador y el fitness decide el depósito. Durante el entrenamiento se ven
  las feromonas y la ruta de cada hormiga.
- **Fin de un entrenamiento.** Límite de generaciones configurable y botón
  Finalizar. Al terminar se muestran las estadísticas y la corrida queda
  guardada en `logs/runs/`.
- **Resultados y comparación.** Vista con el resumen de una corrida o la
  comparación de dos (tabla con el mejor valor resaltado y curvas
  superpuestas). En la terminal: `main.py runs` y `main.py compare A B`.
- **Resumen del episodio manual** al llegar, chocar o quedarse sin tiempo.
- **Conducir con lo aprendido** por cualquiera de los tres algoritmos.

## 3. Archivos creados

- `control/rule_controller.py`, `control/route_controller.py`
- `optimization/aco_rules/` (`__init__.py`, `colony.py`, `heuristic.py`)
- `optimization/aco_routes/` (`__init__.py`, `colony.py`)
- `optimization/results.py`
- `ui/results_view.py`
- `tests/test_rule_controller.py`, `test_aco_rules.py`, `test_route_controller.py`,
  `test_aco_routes.py`, `test_results.py`
- `docs/architecture/decisions/ADR-0005-soluciones-que-dependen-del-escenario.md`,
  `ADR-0006-dos-colonias-de-hormigas.md`
- `docs/requests/done/2026-11-14-seleccion-de-algoritmo-aco-y-comparacion.md`
- `docs/images/feromonas.png`, `docs/images/comparacion.png`
- Este informe.

## 4. Archivos modificados

- Contratos y sesión: `control/controller.py` (posición en la observación),
  `simulation/environment.py` (la publica), `simulation/map_data.py` (huella del
  mapa), `optimization/strategy.py`, `evaluation.py`, `registry.py`, `training.py`,
  `optimization/genetic/__init__.py`, `bootstrap.py`, `main.py`,
  `config/default.json`.
- Interfaz: `ui/simulation_view.py` (reescrita), `ui/training_panel.py`,
  `ui/widgets.py`, `rendering/renderer.py`.
- Pruebas: `tests/test_evaluation.py`, `test_simulation.py`, `test_training.py`,
  `test_architecture.py`, `test_config.py`, `test_app_smoke.py`.
- Documentación: `README.md`, `CLAUDE.md`, `docs/README.md`, `docs/GUIDE.md`,
  `docs/CHANGELOG.md`, `docs/specification/EVOLUTION.md`,
  `docs/architecture/OVERVIEW.md`, `MODULE_CONTRACTS.md`,
  `docs/status/PROJECT_STATUS.md`, `ROADMAP.md`, `BACKLOG.md`, `KNOWN_ISSUES.md`,
  `docs/images/manual.png`, `entrenamiento.png`.

## 5. Decisiones técnicas adoptadas

Las arquitectónicas están en ADR-0005 (soluciones que dependen del escenario) y
ADR-0006 (dos colonias de hormigas). Además:

- **"Finalizar una simulación"** se interpretó como el fin de un entrenamiento.
  Por si se refería a un episodio, la vista manual también muestra un resumen.
- **Límite por defecto de 30 generaciones** (`training.max_iterations`), para que
  una corrida termine sola; se cambia en la ventana o se pone en 0.
- **La especificación se amplió** con los requisitos nuevos, fechados y marcados
  como pedidos por el usuario (`docs/specification/EVOLUTION.md`).
- **Registro de corridas en JSON** con el historial completo; las cifras de
  resumen se derivan al leerlo, así que agregar una métrica no invalida corridas viejas.
- **Tiempos**: se mide el tiempo de cómputo de cada generación, no el de reloj,
  para que una pausa en la ventana no cuente.
- **Etiquetas de las estadísticas** de cada algoritmo las aporta su plugin; la
  interfaz ya no conoce las del genético.
- **Checkpoints anteriores** siguen cargando: los ajustes que no existían toman
  su valor por defecto.

Ajustes que resultaron necesarios durante el desarrollo de la colonia de rutas,
todos encontrados al medir por qué fallaban las hormigas:

1. El seguidor cambiaba de waypoint demasiado pronto y recortaba esquinas; ahora
   persigue un punto adelantado sobre la ruta.
2. Su frenado reactivo lo dejaba detenido junto a cualquier obstáculo fijo (no
   puede girar sin avanzar); el corredor vigilado se estrechó y se orienta hacia
   el lado del giro.
3. Las hormigas trazaban giros de 90° que el vehículo no puede tomar; ahora giran
   como mucho 45° por paso.
4. Con esa restricción algunas pasaban de largo del destino y daban vueltas;
   ahora entran directamente cuando lo tienen al lado y la ruta tiene un largo máximo.

Con esos cuatro cambios, las hormigas que llegaban en la primera iteración
pasaron de aproximadamente 1 de cada 10 a más de la mitad.

## 6. Pruebas ejecutadas y resultados

Se trabajó por etapas, con las pruebas escritas antes que el código y
comprobando que fallaban antes de implementarlo.

| Comprobación | Resultado |
|---|---|
| `.venv/bin/python -m pytest` (suite completa) | **291 pasaron, 0 fallaron** (26 archivos, ≈ 26 s) |
| Copia del proyecto sin cada algoritmo, y sin ninguno | Simulación, editor y aplicación funcionan (`test_architecture`, 4 casos) |
| Los tres algoritmos entrenan y reanudan desde checkpoint con resultados idénticos | `test_training` (parametrizada) |
| Los tres algoritmos entrenan dentro de la ventana sin bloquearla | `test_app_smoke` (parametrizada) |
| Línea de comandos: `train --strategy` con los tres, `runs`, `compare`, errores | `test_results` |
| Corridas de referencia sin ventana: 30 generaciones con cada algoritmo, configuración por defecto, misma semilla y mismos mapas | Completadas; resultados abajo |
| Capturas de entrenamiento, feromonas, resultados, comparación y resumen manual | Revisadas visualmente; se corrigieron cuatro detalles (mapa de calor, una etiqueta que se solapaba, márgenes del gráfico y un color de estado) |

Resultados de las corridas de referencia (población 50, 3 mapas aleatorios por
individuo, 5 mapas de validación):

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

Lectura: la colonia de reglas y el genético resuelven el mismo problema y son
comparables de igual a igual. La colonia de rutas planifica sobre mapas que
conoce: llega antes y más a menudo en ellos, pero no tiene validación porque lo
que aprende no sirve en otros mapas. Es una sola semilla: sirve para ver que
los tres funcionan y la tendencia, no para declarar un ganador.

**No ejecutado:** la aplicación no se abrió en una ventana real; la interfaz se
verificó con el driver de video `dummy` de SDL (pruebas y capturas).

## 7. Limitaciones conocidas

Ver `status/KNOWN_ISSUES.md`. Las principales:

- La colonia de rutas no generaliza y no resuelve un obstáculo móvil que recorre
  el propio camino.
- La tabla de reglas es gruesa: aprende rápido pero choca a menudo.
- Una comparación solo es de igual a igual con la misma semilla, población y
  mapas; la vista avisa si los mapas difieren.
- Los resultados son de una sola semilla.

## 8. Tareas pendientes y recomendaciones

1. Probar a mano en la ventana el selector, Finalizar y la vista de resultados.
2. Repetir las corridas con varias semillas antes de sacar conclusiones sobre
   qué algoritmo es mejor.
3. Las etapas propuestas siguen en `status/ROADMAP.md` (revisión manual,
   generalización, PSO, ABC, rendimiento).
