# Especificación del proyecto

> Documento editable por el usuario. Describe lo que se espera del proyecto, no
> cómo está hecho hoy (para eso: `status/PROJECT_STATUS.md`).

## Objetivo

Simulador 2D de un vehículo autónomo que usa un sensor LiDAR para detectar
obstáculos y aprende a navegar mediante algoritmos evolutivos.

La aplicación (Python, Pygame, NumPy) debe permitir:

1. Crear mapas mediante un editor visual ASCII.
2. Agregar caminos, vehículos, obstáculos estáticos y dinámicos.
3. Simular un vehículo con movimiento continuo y un LiDAR de 72 rayos.
4. Entrenar vehículos mediante algoritmos evolutivos.
5. Visualizar distintos individuos de una población simultáneamente.
6. Observar cómo evoluciona el desempeño entre generaciones.

## Prioridad: modularidad

El simulador debe ser completamente independiente del algoritmo de aprendizaje.
La física, el vehículo, el LiDAR y el editor no dependen de Genetic Algorithms
ni de ninguna implementación particular de aprendizaje.

Primero se implementa Genetic Algorithms (GA). La arquitectura queda preparada
para incorporar después PSO, ACO y ABC, **sin implementarlos ahora** y sin crear
clases vacías, código ficticio ni implementaciones simuladas.

**Restricción final:** si se elimina por completo `optimization/genetic/`, el
simulador, el editor, los vehículos, los sensores y los obstáculos deben seguir
funcionando. Si se agrega PSO, ACO o ABC, no debe hacer falta modificar la
física ni la implementación del móvil.

## Tecnologías

- Python 3; Pygame (ventana y renderizado); NumPy (cálculo numérico); JSON
  (mapas y configuraciones).
- Sin dependencias innecesarias. OpenCV no es necesario: el LiDAR es raycasting
  geométrico.

## Dos modos en una misma ventana

1. **Editor de mapas** — ver [MAPS_AND_EDITOR.md](MAPS_AND_EDITOR.md).
2. **Simulación** — ver [SIMULATOR.md](SIMULATOR.md) y [EVOLUTION.md](EVOLUTION.md).

## Requisitos de calidad

- Implementar por etapas y comprobar cada parte antes de continuar.
- Separar con claridad: simulación, entidades físicas, sensores, controladores,
  estrategias de optimización, evaluación, renderizado e interfaz.
- No usar variables globales para compartir el estado del simulador.
- Configuración externa para los parámetros ajustables.
- El entrenamiento debe poder ejecutarse sin abrir una ventana gráfica.
- No bloquear el ciclo de Pygame mientras se entrena.
- Pruebas para: movimiento, colisiones, raycasting LiDAR, trayectorias de
  obstáculos, guardado y carga de mapas, reproducibilidad de semillas,
  operadores genéticos, evaluación de fitness, evolución de generaciones e
  independencia entre el simulador y el algoritmo.
- Priorizar una implementación funcional, modular y fácil de mantener por sobre
  la cantidad de funcionalidades. No agregar complejidad sin necesidad concreta.

## Criterios de aceptación de la primera versión

1. Se pueden crear, guardar y cargar mapas.
2. Los vehículos se desplazan de forma continua.
3. El LiDAR detecta correctamente los obstáculos.
4. Existen obstáculos estáticos y dinámicos.
5. Se pueden ejecutar múltiples móviles independientes.
6. Cada móvil puede usar un controlador intercambiable.
7. GA puede evolucionar una población de políticas neuronales.
8. Se generan nuevas generaciones correctamente.
9. Se pueden visualizar varios individuos de la misma generación.
10. El entrenamiento funciona sin renderizado.
11. Se pueden guardar y recuperar checkpoints.
12. El simulador funciona sin importar ni conocer GA.
