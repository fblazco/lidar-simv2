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

- **Las curvas de entrenamiento son ruidosas.** Con mapas nuevos en cada
  generación, el mismo individuo puntúa distinto de una generación a otra: el
  mejor fitness sube y baja, y un élite puede perder su lugar por mala suerte
  con los mapas. La cifra estable es la validación.
- **"Lo aprendido" es el mejor de la última generación**, no el de mejor
  validación; con ruido, puede no ser el mejor modelo de la corrida.
- Con velocidad x1 una generación dura lo que tarden los individuos visibles.
  Subir la velocidad o poner `visible_agents` en 0 la acorta.
- Un checkpoint solo se puede reanudar con la misma arquitectura de red y el
  mismo tamaño de población con que se guardó (se informa con un error claro).
- Los checkpoints se guardan en el límite entre generaciones: una generación a
  medio evaluar se repite al reanudar.
- Un modelo entrenado con una evasión no sirve con otra: aprendió a proponer
  intenciones para esa capa.

## Evasión de obstáculos

- **FTG** gira a fondo ante cualquier obstáculo dentro de su distancia libre y
  suele dar rodeos amplios; puede chocar con obstáculos móviles que llegan de
  costado, fuera de su campo de visión de 200°.
- **APF** puede quedar atrapado frente a paredes anchas (mínimo local) y oscila
  en pasos estrechos; la componente tangencial resuelve el obstáculo aislado
  alineado con el destino, no una pared.
- Ninguno de los dos da marcha atrás: el vehículo no la tiene habilitada.
- La **referencia sin aprendizaje** evalúa un solo controlador por generación
  (3 episodios): sus cifras por generación valen poco; hay que mirar la validación.
- El **camino más corto** de referencia no deja holgura para el cuerpo del
  vehículo, así que la eficiencia es algo pesimista cuando hay que rodear algo.

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

- **Falta un recorrido manual** de la interfaz en una ventana real (ver
  `PROJECT_STATUS.md`). Se rehízo entera el 2026-11-15 y solo se comprobó con
  pruebas automáticas y capturas sin pantalla.
- **El tema elegido con el botón no se guarda**: al abrir la aplicación vuelve
  el de `window.theme`.
- **Sin colores, por diseño.** Que un vehículo llegó, chocó o se quedó sin
  tiempo se lee en el texto de estado y en que se dibuja más apagado; A y B se
  distinguen por trazo y relleno.
- **Las escenas de las tarjetas son fijas.** Se capturaron el 2026-11-15 con los
  modelos de las corridas de referencia y no cambian con la configuración. El
  guion que las generó no está en el repositorio; el formato sí está descrito
  en `architecture/MODULE_CONTRACTS.md`.
- **Fuentes del sistema.** La interfaz busca Ubuntu, DejaVu Sans, Liberation
  Sans o Noto Sans, y DejaVu Sans Mono para símbolos y cifras. Si no hay
  ninguna, Pygame usa su fuente por defecto: los textos cambian de ancho y las
  flechas de la ayuda de teclado pueden no verse.
- **Ventanas pequeñas.** Por debajo de 1000×640 algunos textos se recortan con
  "…" y el panel del editor puede no mostrar todos sus controles.
- La lista de mapas guardados muestra como máximo 9.
- En la corrida en curso, las cifras propias del algoritmo solo aparecen si
  queda espacio en su tarjeta (no caben en ventanas bajas).
