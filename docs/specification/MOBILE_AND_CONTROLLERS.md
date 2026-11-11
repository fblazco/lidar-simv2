# Especificación: móvil y controladores

> Documento editable por el usuario.

## Móvil (Mobile)

Es una entidad del simulador. Cada móvil tiene: estado físico, posición X/Y,
orientación, velocidad, modelo de movimiento, sensor LiDAR y un controlador
asociado.

El controlador es intercambiable:

- `Mobile + ManualController`
- `Mobile + GeneticPolicyController`
- en el futuro: `Mobile + PSOPolicyController`, `Mobile + ACORouteController`…

El móvil no implementa GA, PSO, ACO ni ABC. Solo consulta a su controlador para
saber qué acción ejecutar. Las dependencias se inyectan: el móvil no importa
directamente las clases de los algoritmos.

## Interfaz del controlador

Interfaz sencilla para conectar distintos controladores:

- `Controller.observe(observation)`
- `Controller.act(observation) -> action`
- `Controller.reset()`

El controlador recibe información numérica del vehículo y del entorno. Su
implementación no contiene código de renderizado ni depende de Pygame.

## Controller/Policy frente a LearningStrategy/Optimizer

Son conceptos separados:

- **Controller/Policy:** transforma observaciones del vehículo en acciones.
- **LearningStrategy/Optimizer:** genera y optimiza las políticas o soluciones.

## Entradas de la política neuronal

- Las 72 distancias LiDAR.
- Orientación del vehículo.
- Velocidad.
- Información relativa al destino.
- Información del siguiente waypoint.
- Desviación respecto del camino.
- Modo de navegación.
- Opcional: la medición LiDAR anterior, para aportar información temporal sobre
  los obstáculos móviles.

Un `ObservationBuilder` independiente genera el vector de entrada y calcula sus
dimensiones. No se deben escribir dimensiones fijas en distintos módulos.

## Salidas

Dos salidas continuas:

- **Steering:** dirección entre -1 y 1.
- **Acceleration:** aceleración/frenado entre -1 y 1.

La política convierte estas salidas en controles para el móvil.
