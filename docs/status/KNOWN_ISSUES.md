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

- Con velocidad x1 una generación dura lo que tarden los individuos visibles.
  Subir la velocidad o poner `visible_agents` en 0 la acorta.
- Un checkpoint solo se puede reanudar con la misma arquitectura de red y el
  mismo tamaño de población con que se guardó (se informa con un error claro).
- Los checkpoints se guardan en el límite entre generaciones: una generación a
  medio evaluar se repite al reanudar.

## Interfaz

- No se probó a mano en una ventana real (ver `PROJECT_STATUS.md`).
- La lista "Cargar..." muestra como máximo 8 mapas.
