# Especificación: aprendizaje y evolución

> Documento editable por el usuario.

## Estrategia de aprendizaje (Learning Strategy)

El algoritmo administra el proceso de búsqueda, optimización o evolución. Debe
poder: crear candidatos, entregarlos para evaluación, recibir resultados,
actualizar su estado, generar nuevos candidatos, informar estadísticas y
guardar y recuperar su progreso.

No controla la física ni renderiza vehículos.

**No se fuerza a todos los algoritmos a usar un mismo genoma o representación
interna.** GA trabaja con genomas y poblaciones; PSO con partículas; ACO con
feromonas y construcción de soluciones; ABC con fuentes de alimento y abejas.
La interfaz común facilita la integración, pero cada algoritmo conserva sus
mecanismos propios.

## Primer algoritmo: Genetic Algorithms (GA)

GA tradicional que evoluciona redes neuronales de arquitectura fija. El genoma
de cada individuo son los pesos y sesgos de la red (un MLP de arquitectura
configurable).

Operadores: población inicial, fitness, selección, crossover, mutation,
elitismo y generación siguiente. Inicialmente:

- Selección por torneo.
- Crossover configurable.
- Mutación gaussiana de pesos.
- Elitismo configurable.
- Tamaño de población configurable.

Las operaciones genéticas no se mezclan con la lógica del simulador. GA es el
primer plugin concreto de optimización.

## Fitness

Debe considerar: progreso hacia el destino, llegada exitosa, colisiones, tiempo
utilizado, desviación respecto del camino, y calidad y suavidad del movimiento.

- Llegar al destino debe valer significativamente más que solo evitar colisiones.
- Un vehículo que permanece detenido no debe conseguir un fitness elevado.
- Los individuos se evalúan en varios escenarios, para que no aprendan un solo mapa.
- Todos los individuos de una generación se evalúan con un conjunto comparable
  de escenarios.
- Las semillas de los escenarios se guardan para reproducir experimentos.
- Los escenarios de validación se mantienen separados de los usados para
  seleccionar individuos.

## Poblaciones y visualización simultánea

Configuraciones separadas:

- `POPULATION_SIZE`: cantidad total de individuos (p. ej. 50).
- `VISIBLE_AGENTS`: vehículos que se muestran a la vez (p. ej. 4).

Cada móvil visible tiene su propio mapa o instancia de escenario, su propio
estado, sus propios obstáculos, su propia política candidata y su propio
fitness parcial. Todos pertenecen a la misma generación. Los demás individuos
se evalúan sin renderizado, con el mismo código de simulación. Una única
ventana Pygame reparte el espacio entre los móviles mostrados.

Al terminar la evaluación de todos los individuos:

1. Se ordenan por fitness.
2. Se conservan los mejores mediante elitismo.
3. Se seleccionan padres.
4. Se aplica crossover y mutation.
5. Se crea la siguiente generación.

No confundir individuos, episodios y generaciones. La generación siguiente solo
comienza cuando termina la evaluación de la anterior.

## Estadísticas

Mostrar: generación actual, individuo actual, fitness individual, mejor
fitness, fitness promedio, tasa de éxito, número de colisiones, distancia
recorrida, tiempo de navegación y número de evaluaciones.

Incluir un gráfico de evolución del fitness promedio y del mejor fitness.
Preparar estadísticas específicas de GA (tasa de mutación, diversidad de la
población) cuando corresponda.

## Checkpoints

Se debe poder guardar y recuperar el progreso del entrenamiento.

## Algoritmos futuros (no implementar todavía)

- **PSO:** partículas con posición, velocidad, pBest y gBest.
- **ACO:** feromonas, evaporación y construcción probabilística de soluciones.
- **ABC:** employed bees, onlooker bees, scout bees y abandono de fuentes.

Solo se definen las interfaces y dependencias necesarias para integrarlos más
adelante sin modificar el simulador, el móvil, el sensor ni el editor.
