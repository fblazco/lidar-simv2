# ADR-0008: Mapas nuevos en cada generación y medida del camino más corto

Fecha: 2026-11-15

## Contexto

Con tres mapas fijos durante todo el entrenamiento, los algoritmos aprendían a
resolver esos mapas: el éxito en validación quedaba muy por debajo del de
entrenamiento. El usuario pidió entrenar con mapas aleatorios distintos en cada
generación, para que lo aprendido sirva "independientemente del mapa", y que el
objetivo sea encontrar el camino más corto.

## Decisión

- `training.resample_scenarios_every = 1`: cada generación recibe mapas nuevos,
  iguales para todos sus individuos. El conjunto de validación sigue fijo y
  crece a 20 mapas.
- Las estrategias con `generalizes = False` (colonia de rutas) conservan mapas
  fijos: aprenden una ruta por mapa.
- Los mapas aleatorios pasan a ser de **navegación libre** por defecto, con los
  obstáculos repartidos en torno a la recta inicio-destino y algunos formando
  paredes. Los mapas con ruta dibujada siguen disponibles (`generator.navigation_mode`,
  selector "Mapas" y `--maps`).
- Cada escenario conoce el largo de su camino más corto
  (`Scenario.reference_length`): en modo libre, el camino entre los obstáculos
  fijos; en modo ruta, el camino dibujado. La **eficiencia** de un episodio que
  llega es ese largo dividido por la distancia recorrida, y suma al fitness
  (`fitness.efficiency`).

## Alternativas consideradas

- Mantener los mapas fijos y solo agregar más: reduce el sobreajuste pero no lo
  elimina, y cada generación cuesta más.
- Seguir con mapas de ruta: "encontrar el camino más corto" no significa nada si
  el camino ya está dibujado.
- Medir el camino más corto con la línea recta: castigaría rodeos inevitables.

## Consecuencias

- El mejor fitness ya no es monótono: el mismo individuo puntúa distinto en
  mapas distintos. Las curvas de entrenamiento son ruidosas por diseño; la
  referencia estable es la validación.
- La comparación entre corridas se apoya en la validación (mismos 20 mapas para
  todas las que comparten semilla), con intervalo de confianza y prueba de
  significancia.
- El camino más corto de referencia no deja holgura para el cuerpo del
  vehículo: es una cota optimista, así que una eficiencia del 100 % es
  prácticamente inalcanzable cuando hay que rodear algo.
- Las corridas anteriores a este cambio (mapas de ruta, fijos) no son
  comparables con las nuevas; el registro de cada corrida guarda el tipo de
  mapas y la vista de resultados avisa cuando difieren.
