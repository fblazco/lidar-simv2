# ADR-0003: Evaluación por pasos y cooperativa, sin hilos

Fecha: 2026-11-11

## Contexto

El entrenamiento no debe bloquear el ciclo de Pygame; hay que mostrar algunos
individuos mientras el resto se evalúa sin dibujarse, con el mismo código de
simulación, y el entrenamiento también debe correr sin ventana.

## Decisión

- `CandidateEvaluation.step()` avanza un paso de simulación de un candidato.
- `TrainingSession.advance(visible_steps, time_budget)` avanza los candidatos
  visibles y dedica como máximo `time_budget` segundos por cuadro a los demás.
- `run_iteration()` (sin ventana) llama a `advance` en un bucle: no hay un
  segundo camino de código.
- Los resultados se ordenan por id antes de `tell()`, de modo que el resultado
  no depende de los tiempos.

## Alternativas consideradas

- Hilo o proceso de entrenamiento: evita repartir el trabajo, pero agrega
  sincronización, complica la reproducibilidad y el GIL limita la ganancia con
  hilos. Los procesos quedan como mejora futura (ver BACKLOG).
- Evaluar toda la generación entre cuadros: bloquea la ventana varios segundos.

## Consecuencias

- La ventana responde siempre; el resultado con y sin ventana es idéntico
  (verificado en `tests/test_training.py`).
- Con velocidad x1 la generación dura lo que tarden los individuos visibles; el
  usuario puede acelerarlos.
- La validación del mejor individuo se hace antes de `tell()`, así que la
  generación siguiente nace exactamente cuando termina la anterior.
