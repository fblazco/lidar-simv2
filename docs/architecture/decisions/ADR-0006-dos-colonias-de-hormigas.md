# ADR-0006: Dos colonias de hormigas

Fecha: 2026-11-14

## Contexto

Había que agregar Ant Colony Optimization. La especificación mencionaba un
controlador de rutas para ACO, pero también exige evaluar en varios mapas y
validar en mapas no vistos, lo que una ruta por mapa no puede cumplir. Se le
planteó la contradicción al usuario, que eligió implementar las dos variantes.

## Decisión

Dos plugins independientes, ambos con los mecanismos propios de ACO (feromonas,
evaporación, construcción probabilística, cotas mínima y máxima al estilo
MAX-MIN, depósito por ranking y refuerzo de la mejor solución conocida).

**`aco_rules` — reglas de conducción.** El grafo de construcción tiene una etapa
por situación (135: dirección del waypoint y cercanía en tres sectores del
LiDAR) y una arista por maniobra (15). Cada hormiga elige una maniobra por
situación; la solución es una tabla de reglas y generaliza a cualquier mapa. La
heurística codifica lo obvio (girar hacia el objetivo, alejarse de lo cercano,
no acelerar con algo delante) y solo depositan las decisiones que la hormiga
usó de verdad al conducir.

**`aco_routes` — rutas por mapa.** ACO clásico de planificación: una colonia por
mapa, feromona en las celdas, hormigas que avanzan de celda en celda sin
repetir. La heurística premia acercarse al destino (o avanzar por el camino
dibujado, en modo ruta). Un `RouteController` conduce la ruta en el simulador y
el fitness obtenido decide el depósito.

Decisiones propias de la variante de rutas:

- Las hormigas conocen el plano estático (grilla, inicio, destino, obstáculos
  fijos, camino dibujado). Los obstáculos móviles no están en el plano: se
  manifiestan solo en el fitness, y el controlador frena ante ellos con el LiDAR.
- Una hormiga gira como mucho 45° entre un paso y el siguiente (salvo al entrar
  al destino). Sin esa restricción trazaba giros que el vehículo, con radio de
  giro de una celda, no podía tomar.
- El seguidor persigue un punto adelantado sobre la ruta y orienta su corredor
  de frenado hacia el lado al que gira; con un corredor recto quedaba detenido
  junto a cualquier obstáculo fijo, porque no puede girar sin avanzar.

## Alternativas consideradas

- Solo la colonia de reglas: comparable con el genético, pero no es lo que la
  especificación sugería para ACO.
- Solo la colonia de rutas: no generaliza ni admite validación.
- ACO continuo sobre los pesos de la red: reutilizaba todo, pero se aleja de la
  construcción de soluciones con feromonas que pedía la especificación.

## Consecuencias

- La colonia de reglas y el genético resuelven el mismo problema y se comparan
  de igual a igual, validación incluida.
- La colonia de rutas resuelve otro problema (planificar en mapas conocidos):
  suele llegar antes en sus mapas de entrenamiento, no tiene validación y la
  comparación lo deja a la vista.
- Los umbrales del discretizador y los parámetros del seguidor quedan en la
  configuración (`rule_policy`, `aco_routes.follower`).
