# ADR-0005: Soluciones que dependen del escenario

Fecha: 2026-11-14

## Contexto

El contrato original (ADR-0002) suponía que una solución sirve en cualquier
mapa: `controller_factory(solución) -> Controller` y nada más. La colonia de
hormigas que traza rutas rompe ese supuesto: su solución es una ruta por mapa,
el controlador necesita saber en qué mapa está y dónde está el vehículo, y la
estrategia necesita conocer los mapas antes de construir candidatos.

## Decisión

Se amplía el contrato de optimización con piezas opcionales, sin cambiar el
núcleo pedir/informar:

- La fábrica pasa a ser `controller_factory(solución, escenario)` y el evaluador
  crea un controlador por episodio. `for_any_scenario` adapta las fábricas que
  ignoran el escenario (el genético y la colonia de reglas).
- `LearningStrategy.prepare(escenarios)`: se llama antes de cada `ask()`. Por
  defecto no hace nada.
- `LearningStrategy.generalizes`: si es `False`, la sesión no valida en mapas no
  vistos y la interfaz lo indica.
- `CandidateResult.scores`: el fitness de cada episodio, para algoritmos que
  aprenden por escenario.
- `Scenario.key`: la huella del contenido del mapa, para reconocerlo.
- `Observation` incluye la posición absoluta `x`, `y`.
- `LearningStrategy.cell_heatmap(escenario)`: datos opcionales para dibujar.

## Alternativas consideradas

- Que el controlador de rutas adivinara su mapa (por el orden de los episodios o
  por su primera observación): frágil y oculto.
- Una jerarquía aparte para "planificadores": duplicaría evaluación, sesión,
  checkpoints, interfaz y comparación.
- No ofrecer la variante de rutas: el usuario pidió las dos.

## Consecuencias

- El simulador solo cambió en dos líneas: publicar `x`, `y` en la observación.
  La física, el móvil, el sensor y el editor no se tocaron.
- El genético y la colonia de reglas no usan ninguna de las piezas nuevas; un
  PSO o un ABC tampoco las necesitarán.
- Un algoritmo que no generaliza no tiene cifras de validación: la comparación
  las muestra como "no aplica" en lugar de inventarlas.
- "Conducir con lo aprendido" solo es posible, para esos algoritmos, en los
  mapas con que entrenaron.
