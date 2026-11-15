# Informe: mapas nuevos por generación, camino más corto y evasión con FTG y APF

Fecha: 2026-11-15 · Solicitud: `docs/requests/done/2026-11-15-mapas-aleatorios-ftg-apf.md`

## 1. Objetivo de la tarea

Cambiar el enfoque del entrenamiento: dejar de entrenar en mapas elegidos y usar
mapas aleatorios distintos en cada generación, para que lo aprendido sirva en
cualquier mapa y busque el camino más corto. Permitir elegir, además del
algoritmo que aprende, el de evasión de obstáculos, agregando FTG (Follow the
Gap) y APF (campos potenciales artificiales). Orientar la aplicación a comparar
estadísticamente algoritmos de evasión y de camino más corto. Dejar registrado
el rumbo educativo, sin trabajarlo todavía.

El usuario pidió la tarea antes de irse a dormir, así que las decisiones de
diseño se tomaron sin consultarlo; están listadas en la solicitud y en la
sección 5 para su revisión.

## 2. Qué se implementó

- **Mapas nuevos en cada generación.** Todos los individuos de una generación
  comparten mapas, que cambian a la siguiente. La validación pasa a 20 mapas
  fijos. La colonia de rutas conserva mapas fijos.
- **Mapas de navegación libre** por defecto, con obstáculos y paredes en torno
  a la recta inicio-destino. Los mapas con ruta y los mixtos siguen disponibles.
- **Camino más corto.** Cada mapa conoce el largo de su camino más corto; la
  eficiencia de una llegada (camino más corto / distancia recorrida) se mide y
  suma al fitness. También se mide la holgura mínima a los obstáculos.
- **Capa de evasión de obstáculos**, componible con cualquier navegación:
  aprendida (como antes), FTG y APF.
- **Navegación de referencia sin aprendizaje**, que apunta al objetivo: línea de
  base y soporte para medir FTG y APF por sí solos.
- **Comparación estadística.** Las corridas guardan la evasión y el tipo de
  mapas; el resumen y la comparación incluyen colisiones, eficiencia, holgura,
  intervalo de confianza del éxito en validación y una prueba de significancia.
- **Interfaz y terminal.** Selectores de navegación, evasión y tipo de mapas;
  `train --avoidance` y `--maps`; `runs` muestra una tabla con todas las corridas.
- **Rumbo registrado** en `CLAUDE.md`, en la especificación y en el roadmap
  (etapa educativa, sin empezar).

## 3. Archivos creados

- `control/avoidance/` (`__init__.py`, `base.py`, `learned.py`, `ftg.py`, `apf.py`)
- `control/rays.py`, `control/goal_controller.py`
- `optimization/reactive/__init__.py`
- `tests/test_avoidance.py`, `tests/test_shortest_path.py`
- `docs/architecture/decisions/ADR-0007-evasion-como-capa-componible.md`,
  `ADR-0008-mapas-nuevos-por-generacion-y-camino-mas-corto.md`
- `docs/requests/done/2026-11-15-mapas-aleatorios-ftg-apf.md`
- Este informe.

## 4. Archivos modificados

- Mapas y métricas: `editor/map_generator.py`, `simulation/navigation.py`,
  `optimization/fitness.py`, `optimization/evaluation.py`, `optimization/training.py`.
- Composición y registro: `bootstrap.py`, `optimization/results.py`, `main.py`,
  `config/default.json`.
- Controladores: `control/rule_controller.py`, `control/route_controller.py`
  (usan la geometría de rayos compartida).
- Interfaz: `ui/simulation_view.py`, `ui/training_panel.py`, `ui/results_view.py`.
- Pruebas: `tests/test_map_generator.py`, `test_fitness.py`, `test_evaluation.py`,
  `test_training.py`, `test_results.py`, `test_architecture.py`, `test_app_smoke.py`.
- Documentación: `README.md`, `CLAUDE.md`, `docs/GUIDE.md`, `docs/CHANGELOG.md`,
  `docs/specification/PROJECT_SPEC.md`, `EVOLUTION.md`,
  `docs/architecture/OVERVIEW.md`, `MODULE_CONTRACTS.md`,
  `docs/status/PROJECT_STATUS.md`, `ROADMAP.md`, `BACKLOG.md`, `KNOWN_ISSUES.md`,
  y las capturas de `docs/images/`.

## 5. Decisiones técnicas adoptadas

Tomadas sin poder consultar al usuario; las arquitectónicas están en ADR-0007 y
ADR-0008.

1. **Dos selectores independientes**, navegación y evasión, en lugar de una
   lista única de algoritmos. La evasión es una capa que corrige lo que propone
   la navegación.
2. **Navegación de referencia sin aprendizaje**: no la pidió el usuario, pero sin
   ella FTG y APF no se pueden medir por sí solos.
3. **Navegación libre por defecto** en los mapas aleatorios: "encontrar el camino
   más corto" no significa nada si el camino ya está dibujado.
4. **El camino más corto se mide** contra el camino entre los obstáculos fijos
   (sin holgura para el vehículo), no contra la línea recta.
5. **La colonia de rutas conserva mapas fijos.**
6. **Validación de 20 mapas** (antes 5), para que el intervalo de confianza diga algo.
7. **Estadística**: intervalo de Wilson para el éxito en validación y prueba z de
   dos proporciones entre corridas.
8. **Ajustes a los métodos clásicos** (ADR-0007): FTG con el centro angular del
   hueco; APF con una componente tangencial; ambos dejan de intervenir con el
   destino a la vista.
9. **Calibración**: se probaron varios valores sobre 40 mapas con la navegación
   de referencia. FTG pasó de 26 a 31 llegadas al subir el peso del hueco
   (`alpha` de 1.0 a 2.5); APF, de 17 a 26 al subir la repulsión de 0.3 a 2.0.
   Sin evasión, 1 de 40.
10. **Parte educativa**: no se tocó, como se pidió.

## 6. Pruebas ejecutadas y resultados

Se trabajó por etapas, con las pruebas escritas antes que el código.

| Comprobación | Resultado |
|---|---|
| `.venv/bin/python -m pytest` (suite completa) | **349 pasaron, 0 fallaron** (28 archivos, ≈ 37 s) |
| Las combinaciones de navegación y evasión entrenan y reanudan desde checkpoint con resultados idénticos | `test_avoidance` (parametrizada) |
| FTG y APF llevan la navegación de referencia alrededor de un obstáculo fijo y sobreviven a uno que cruza; sin evasión, choca | `test_avoidance` |
| El proyecto funciona al borrar cada plugin de navegación, y todos | `test_architecture` (5 casos) |
| Corridas de referencia sin ventana: 30 generaciones de cada combinación, configuración por defecto, misma semilla | Completadas; resultados abajo |
| Capturas de entrenamiento con los selectores nuevos, comparación y resumen | Revisadas visualmente |

Resultados de las corridas de referencia (población 50, 3 mapas nuevos por
generación, 20 mapas de validación, navegación libre):

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

**No ejecutado:** la aplicación no se abrió en una ventana real; la interfaz se
verificó con el driver de video `dummy` de SDL (pruebas y capturas). Las
corridas de referencia se lanzaron de a cuatro en paralelo, así que los tiempos
por generación son orientativos.

## 7. Limitaciones conocidas

Ver `status/KNOWN_ISSUES.md`. Las principales:

- Las curvas de entrenamiento son ruidosas por diseño (mapas nuevos en cada
  generación); la referencia estable es la validación.
- Un modelo entrenado con una evasión no sirve con otra.
- FTG da rodeos amplios y no ve lo que llega de costado; APF se atasca frente a
  paredes anchas.
- Los resultados son de una sola semilla y 20 mapas de validación: los
  intervalos de confianza son anchos.
- Las corridas anteriores (mapas de ruta, fijos) no son comparables con estas.

## 8. Tareas pendientes y recomendaciones

1. Revisar las decisiones de la sección 5, en especial la navegación libre por
   defecto y la navegación de referencia.
2. Definir el alcance de la etapa educativa (etapa 13 del roadmap).
3. Repetir la matriz con varias semillas antes de sacar conclusiones firmes.
4. Probar a mano las vistas nuevas en la ventana.
