# Especificación: simulador

> Documento editable por el usuario.

## Responsabilidad

El simulador gestiona exclusivamente el mundo físico: mapa, caminos,
posiciones, vehículos, obstáculos, movimiento, colisiones, sensor LiDAR y
tiempo de simulación.

No debe conocer qué algoritmo está entrenando un vehículo. Debe poder
ejecutarse sin ningún algoritmo de aprendizaje (por ejemplo, con un vehículo
controlado manualmente) y aceptar cualquier controlador que respete la interfaz.

## Vehículo

Movimiento continuo en coordenadas reales, con un modelo físico simplificado:
posición X/Y, orientación angular, velocidad lineal, control de dirección,
aceleración y frenado. No se necesita una simulación automotriz avanzada.

El movimiento y las colisiones son independientes del renderizado.

## LiDAR

Raycasting geométrico. Configuración inicial:

- 72 rayos, campo de visión de 360°, separación angular de 5°.
- Distancia máxima configurable.
- Detecta obstáculos estáticos y dinámicos.
- Distancias normalizadas entre 0 y 1.

El LiDAR está siempre visible durante la simulación. Cada vehículo tiene su
propio sensor y sus propias mediciones.

## Obstáculos

- **Estáticos.**
- **Dinámicos**, con tres trayectorias:
  1. Horizontal: ida y vuelta entre dos extremos.
  2. Vertical: ida y vuelta entre dos extremos.
  3. Circular: trayectoria circular continua.

Cada obstáculo dinámico permite configurar posición inicial, velocidad,
extremos (cuando corresponda), centro y radio (movimiento circular), pausas en
los extremos y sentido del movimiento.

Los obstáculos son independientes de los caminos: pueden desplazarse sobre
ellos o atravesar otras zonas. Los obstáculos pueden atravesarse entre sí; las
colisiones entre vehículos y obstáculos se detectan normalmente.

## Navegación

Dos modos, con **una sola** implementación del simulador:

- **Navegación libre:** el vehículo intenta llegar a un destino evitando
  obstáculos.
- **Seguimiento de ruta:** el vehículo intenta seguir los caminos definidos,
  pero puede apartarse temporalmente para evitar obstáculos y luego regresar.

El modo y la información del objetivo están disponibles para el controlador.

Las rutas tienen una representación interna ordenada de puntos o waypoints. La
navegación no depende de interpretar los caracteres ASCII.

## Varios móviles

El simulador debe poder ejecutar múltiples móviles con controladores diferentes.
