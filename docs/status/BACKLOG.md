# Backlog

Ideas y mejoras aún no implementadas. Nada de esto está comprometido: para
pedir algo, crear una solicitud en `requests/open/`.

## Educación (rumbo fijado por el usuario, postergado a propósito)

- Dibujar en vivo lo que decide cada evasor: huecos y hueco elegido de FTG;
  vectores de atracción, repulsión y resultante de APF. Hoy solo existe una
  escena fija por algoritmo en las tarjetas de Entrenar.
- Animar las escenas de las tarjetas y agregarles una leyenda.
- Explicar cada algoritmo dentro de la aplicación, con sus parámetros y su
  efecto en vivo.
- Modo paso a paso: avanzar la simulación de a un paso y ver la decisión.
- Mostrar la tabla de reglas aprendida y qué regla se está aplicando.
- Escenarios didácticos preparados (mínimo local de APF, pasillo estrecho,
  obstáculo que cruza).

## Algoritmos

- Plugin PSO (partículas, velocidad, pBest, gBest) sobre los pesos de la red.
- Plugin ABC (employed, onlooker, scout, abandono de fuentes).
- Evasión: DWA (ventana dinámica) y VFH (histograma de campo vectorial).
- FTG: fórmula original del centro del hueco con las distancias a sus bordes;
  elegir el hueco más cercano a la dirección deseada en lugar del más ancho.
- APF: escape de mínimos locales frente a paredes anchas.
- Entrenar la navegación con una evasión y probarla con otra.
- Colonia de reglas: más situaciones (velocidad, desvío del camino) o umbrales
  aprendidos en lugar de fijos.
- Colonia de rutas: suavizar la ruta antes de conducirla; planificar con
  obstáculos móviles que recorren el propio camino; reutilizar feromonas entre
  mapas parecidos.

## Entrenamiento

- Elegir el modelo final por su validación, no por la última generación.
- Más mapas por individuo en cada generación, para reducir el ruido del fitness.
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

- Guardar el tema elegido entre sesiones.
- Incluir las tipografías de las maquetas (Outfit y DM Mono) en lugar de usar
  las del sistema.
- Guion reproducible para regenerar la escena de cada plugin.
- Un color de acento opcional para los estados (llegó, chocó).
- Mostrar la mejor solución de cada generación en una vista fija.
- Elegir qué individuos mostrar (los mejores, al azar, por id).
- Ver la tabla de reglas aprendida por la colonia de reglas.
