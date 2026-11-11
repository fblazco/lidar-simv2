# Backlog

Ideas y mejoras aún no implementadas. Nada de esto está comprometido: para
pedir algo, crear una solicitud en `requests/open/`.

## Algoritmos

- Plugin PSO (partículas, velocidad, pBest, gBest) sobre los pesos de la red.
- Plugin ABC (employed, onlooker, scout, abandono de fuentes).
- Plugin ACO (feromonas, evaporación, construcción de rutas) con su propio controlador.
- Elegir la estrategia desde la interfaz cuando haya más de una.

## Entrenamiento

- Evaluar candidatos en procesos paralelos para acortar cada generación.
- Seguir entrenando en segundo plano mientras se usa el editor o la conducción manual.
- Ajustar hiperparámetros de GA y fitness; decaimiento de sigma por defecto.
- No reevaluar a los élites cuando los escenarios no cambian.
- Elegir un checkpoint concreto desde la interfaz (hoy: "Cargar último").
- Comparar varios experimentos a partir de `logs/*.jsonl`.

## Simulación

- Interacción entre vehículos (colisión y detección mutua con el LiDAR).
- Cuerpo rectangular del vehículo en lugar de círculo.
- Marcha atrás habilitada por defecto para la conducción manual.
- Controlador automático sin aprendizaje (seguidor de waypoints) como referencia.

## Editor

- Mover y redimensionar obstáculos dinámicos ya creados arrastrándolos.
- Deshacer / rehacer.
- Varios tramos de camino independientes o bifurcaciones.
- Vista previa animada de las trayectorias en el editor.

## Interfaz

- Mostrar la mejor política de cada generación en una vista fija.
- Elegir qué individuos mostrar (los mejores, al azar, por id).
