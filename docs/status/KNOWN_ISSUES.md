# Problemas conocidos y limitaciones

## Entorno

- **`python3 -m venv` falla si falta `ensurepip`** (Ubuntu sin `python3-venv`).
  Solución sin permisos de administrador:
  ```bash
  python3 -m venv --without-pip .venv
  python3 -m pip install --target .venv/lib/python3.10/site-packages -r requirements-dev.txt
  ```
- **Plugins de pytest de ROS.** Si el entorno tiene ROS en `PYTHONPATH`, pytest
  intenta cargar plugins ajenos (`launch_testing`, `ament_*`) y falla al
  arrancar. `pytest.ini` ya los desactiva.

## Simulación

- Un obstáculo dinámico puede alcanzar a un vehículo detenido; cuenta como
  colisión del vehículo.
- La colisión se evalúa una vez por paso (`dt` = 0.05 s). Con velocidades muy
  superiores a las configuradas un vehículo podría atravesar un obstáculo fino.
- El avance en modo ruta se busca en una ventana alrededor del último punto
  alcanzado; si el vehículo se aleja mucho del camino, el avance deja de crecer
  hasta que regresa.

## Entrenamiento

- **Generaliza poco con la configuración por defecto.** Tras 40 generaciones el
  mejor individuo llega al destino en sus tres escenarios de entrenamiento,
  pero solo en 1 de los 5 de validación. Los tres escenarios son fijos durante
  todo el entrenamiento, así que la población se especializa en ellos. Es de
  esperar que ayude poner `training.resample_scenarios_every` en 1 o subir
  `training.scenarios_per_candidate`; todavía no se midió (etapa 11 del roadmap).
- Con velocidad x1 una generación dura lo que tarden los individuos visibles.
  Subir la velocidad o poner `visible_agents` en 0 la acorta.
- Un checkpoint solo se puede reanudar con la misma arquitectura de red y el
  mismo tamaño de población con que se guardó (se informa con un error claro).
- Los checkpoints se guardan en el límite entre generaciones: una generación a
  medio evaluar se repite al reanudar.

## Colonias de hormigas

- **La colonia de rutas no generaliza.** Aprende una ruta para cada mapa de
  entrenamiento; no tiene cifras de validación ("no aplica") y "lo aprendido"
  solo se puede conducir en esos mapas. Con `resample_scenarios_every` distinto
  de 0 empezaría de cero en cada cambio de mapas.
- **Obstáculo móvil que recorre el camino.** Si un obstáculo va y viene sobre el
  propio camino dibujado, la colonia de rutas rara vez encuentra un trazado
  paralelo: el vehículo se detiene a esperar y el obstáculo lo alcanza.
- **El seguidor de rutas puede quedar detenido** frente a un obstáculo fijo si la
  ruta pasa a menos de un radio de vehículo de él; el episodio se corta por
  falta de avance y esa ruta recibe poco refuerzo.
- **La tabla de reglas es gruesa:** 135 situaciones sin velocidad ni desvío del
  camino. Aprende rápido, pero choca a menudo con obstáculos móviles.
- En las primeras iteraciones de la colonia de rutas casi no se ven feromonas:
  el mapa de calor muestra diferencias, y al principio todo el mapa tiene la misma.

## Comparación

- Dos corridas solo son comparables de igual a igual si usaron la misma semilla,
  población y mapas; la vista avisa cuando los mapas difieren, pero no impide comparar.
- Los tiempos dependen de la máquina y, en la ventana, de la velocidad elegida y
  de cuántos agentes se dibujan. Para comparar tiempos conviene entrenar sin ventana.
- Una corrida finalizada antes de terminar su generación en curso descarta esa
  generación a medias.

## Interfaz

- Falta un recorrido manual sistemático de la interfaz en una ventana real
  (ver `PROJECT_STATUS.md`); hasta ahora solo se usó así el entrenamiento.
- La lista "Cargar..." muestra como máximo 8 mapas.
