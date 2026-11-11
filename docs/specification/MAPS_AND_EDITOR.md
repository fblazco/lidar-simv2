# Especificación: mapas y editor

> Documento editable por el usuario.

## Editor de mapas (modo 1)

Permite crear escenarios sobre una grilla de dimensiones personalizables.

### Representación ASCII

Caracteres monoespaciados; dibujo minimalista y fácil de interpretar.

| Elemento | Símbolo |
|---|---|
| Camino vertical | `\|` |
| Camino diagonal | `/` |
| Camino diagonal inverso | `\` |
| Camino horizontal | `-` |
| Vehículo | `o` y `\| \|` |
| Obstáculo estático | `X` |
| Obstáculo dinámico | `*` |
| Inicio | `S` |
| Destino | `G` |

### Herramientas

- Dibujar caminos arrastrando el mouse.
- Borrar elementos.
- Agregar obstáculos estáticos.
- Agregar obstáculos dinámicos (horizontal, vertical, circular) y configurar
  sus parámetros: ver [SIMULATOR.md](SIMULATOR.md).
- Definir posición y orientación inicial del vehículo.
- Definir destino.
- Guardar y cargar mapas.

### Caminos

Los caminos representan una ruta objetivo. El vehículo puede apartarse
temporalmente para evitar obstáculos y luego reincorporarse.

Internamente las rutas son una lista ordenada de puntos o waypoints. No se
depende de interpretar los caracteres ASCII para calcular la navegación.

## Formato

Los mapas se guardan en JSON.

## Generador de mapas aleatorios

Debe producir: diferentes caminos, distintos destinos, obstáculos estáticos,
obstáculos móviles, y diferentes velocidades y trayectorias.

Los mapas deben ser válidos y reproducibles mediante semillas.
