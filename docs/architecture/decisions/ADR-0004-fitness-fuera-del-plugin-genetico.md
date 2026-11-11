# ADR-0004: El fitness vive fuera del plugin genético

Fecha: 2026-11-11

## Contexto

El árbol de archivos sugerido en la especificación ubica el fitness en
`optimization/genetic/fitness.py`. Pero puntuar un episodio (avance, llegada,
colisión, tiempo, desvío, suavidad) no tiene nada específico de GA: PSO, ABC o
ACO necesitarán el mismo criterio, y los candidatos de distintos algoritmos
deben poder compararse.

## Decisión

Las métricas de un episodio y la función de fitness están en
`optimization/fitness.py`, y la evaluación en `optimization/evaluation.py`.
`optimization/genetic/` contiene solo lo propio de GA: genoma, selección,
crossover, mutación y el algoritmo.

## Alternativas consideradas

- Respetar el árbol sugerido: un algoritmo nuevo tendría que importar desde
  `optimization/genetic/` o duplicar el fitness, y borrar esa carpeta rompería
  la evaluación.

## Consecuencias

- Borrar `optimization/genetic/` no afecta al evaluador.
- Es una diferencia respecto del árbol sugerido (que la especificación permite
  adaptar); queda registrada en `status/PROJECT_STATUS.md`.
