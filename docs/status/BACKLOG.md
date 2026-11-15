# Backlog

Ideas y mejoras aún no implementadas. Nada de esto está comprometido: para
pedir algo, crear una solicitud en `requests/open/`.

## Algoritmos

- Plugin PSO (partículas, velocidad, pBest, gBest) sobre los pesos de la red.
- Plugin ABC (employed, onlooker, scout, abandono de fuentes).
- Colonia de reglas: más situaciones (velocidad, desvío del camino) o umbrales
  aprendidos en lugar de fijos.
- Colonia de rutas: suavizar la ruta antes de conducirla; planificar con
  obstáculos móviles que recorren el propio camino; reutilizar feromonas entre
  mapas parecidos.

## Entrenamiento

- Medir cuánto mejora la validación al remuestrear escenarios en cada generación
  y al usar más escenarios por individuo (etapa 11 del roadmap).
- Evaluar candidatos en procesos paralelos para acortar cada generación.
- Seguir entrenando en segundo plano mientras se usa el editor o la conducción manual.
- Ajustar hiperparámetros de cada algoritmo; decaimiento de sigma por defecto.
- No reevaluar a los élites cuando los escenarios no cambian.
- Elegir un checkpoint concreto desde la interfaz (hoy: "Cargar último").

## Resultados

- Borrar o renombrar corridas desde la interfaz.
- Comparar más de dos corridas y promediar varias semillas por algoritmo.
- Exportar la comparación a un archivo (CSV o imagen).
- Repetir una corrida guardada con otra semilla desde la interfaz.

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

- Mostrar la mejor solución de cada generación en una vista fija.
- Elegir qué individuos mostrar (los mejores, al azar, por id).
- Ver la tabla de reglas aprendida por la colonia de reglas.
