# Solicitud: Elegir el algoritmo, agregar colonia de hormigas y comparar corridas

> Esta solicitud llegó por conversación, no como archivo. Se transcribe aquí
> para que quede en el repositorio. El texto de "Objetivo" es literal.

## Objetivo

"quiero que hagas posible que el simulador pueda entrenar el movil con distintos
algorimos, y que el algoritmo con el que se simule quede a seleccion del
ususario, en estos momentos esta implementado un algoritmo genetico. Quiero que
agregues un algoritmo de ant colony. tomate tu tiempo. tambien anade
estadisticas cuando se finalice una simulacion y si se corrieron dos distintas
la posibilidad de comparara. tomate tu tiempo"

## Contexto

Hasta ahora solo existía el algoritmo genético y no había forma de dar por
terminado un entrenamiento ni de comparar dos.

## Cambios solicitados

- Poder entrenar con distintos algoritmos, a elección del usuario.
- Agregar un algoritmo de colonia de hormigas.
- Estadísticas al finalizar una simulación.
- Comparar dos corridas distintas.

## Restricciones

Las de `CLAUDE.md`: el simulador, el móvil, el sensor y el editor no dependen de
ningún algoritmo.

## Criterios de aceptación

- [x] El algoritmo se elige en la ventana y en la línea de comandos.
- [x] Hay al menos un algoritmo de colonia de hormigas que entrena al móvil.
- [x] Al finalizar un entrenamiento se muestran sus estadísticas y quedan guardadas.
- [x] Dos corridas terminadas se pueden comparar con las mismas métricas.

## Estado

Implementada y verificada el 2026-11-14.
Informe: `docs/reports/2026-11-14-seleccion-de-algoritmo-aco-y-comparacion.md`.

---

## Notas de Claude

**Pregunta hecha antes de implementar.** La especificación mencionaba un
`ACORouteController` (rutas), pero también exige evaluar en varios mapas y
validar en mapas no vistos, lo que solo es posible si lo aprendido no depende de
un mapa. Se plantearon tres opciones: reglas de conducción, rutas sobre cada
mapa, o las dos. **El usuario eligió "Las dos".**

**Interpretación de "cuando se finalice una simulación".** Se tomó como el fin de
un entrenamiento: al llegar al límite de generaciones o al pulsar Finalizar. Por
si se refería al fin de un episodio de conducción, la vista manual también
muestra un resumen cuando el vehículo llega, choca o se queda sin tiempo.
