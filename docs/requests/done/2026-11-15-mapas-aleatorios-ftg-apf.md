# Solicitud: Mapas aleatorios por generación, camino más corto y evasión con FTG y APF

> Llegó por conversación la noche del 2026-11-14; el usuario se fue a dormir y
> pidió que se implementara sin esperarlo. El texto de "Objetivo" es literal.

## Objetivo

"OK now i want you to change a little bit the approach, right now we are
training the movile robotol in a choosen map, so we are not actually taking
advantage of the genetic algorithm, now i want you to change thtat, we will use
random maps for every generation so in the loing run it learns to find the
shortest path indeppendent of wich map the robot is placed. Also I want to be
more abitius, now we will not only chosse the algorithm to train the model in
the shortest path but we will also train it to avoid the obstacles (just like we
did before) but we will allow the user to also choose different algorithms i
want you to implement FTG (follow the gap) algorithm and APF (artificial
potencial fields) now i want the app to be educative and stadistical to compare
between different algoritms for obstacle avoiding and shortest path founding,
but dont focus on the educational path yet just change it in your context to
keep it if we run out of context tokens lol. So yeah implement that, now im
going to sleep so do your work."

## Cambios solicitados

- Mapas aleatorios distintos en cada generación, para que lo aprendido sirva en
  cualquier mapa.
- Aprender a encontrar el camino más corto.
- Seguir pudiendo aprender a evitar obstáculos, y además elegir un algoritmo
  clásico de evasión: FTG (Follow the Gap) y APF (Artificial Potential Fields).
- Aplicación estadística para comparar algoritmos de evasión de obstáculos y de
  búsqueda del camino más corto.
- Rumbo futuro: aplicación educativa. **No trabajarlo todavía**; solo dejarlo
  registrado.

## Estado

Implementada y verificada el 2026-11-15, salvo la parte educativa, que el usuario
pidió postergar. Informe: `docs/reports/2026-11-15-mapas-aleatorios-ftg-apf.md`.
Las decisiones de más abajo se tomaron sin consultar y esperan revisión del usuario.

---

## Notas de Claude: decisiones tomadas sin poder consultar

El usuario no estaba disponible, así que estas decisiones quedan a su revisión.

1. **Dos selectores independientes.** "Navegación" (quién decide hacia dónde ir:
   genético, ACO reglas, ACO rutas, o una referencia sin aprendizaje) y "Evasión"
   (quién esquiva: lo aprendido por el propio algoritmo, FTG o APF). La evasión
   es una capa que envuelve a cualquier controlador.
2. **Referencia sin aprendizaje.** Para medir FTG y APF por sí solos hace falta
   un navegador que no aprenda: apunta al objetivo y nada más.
3. **Mapas de navegación libre por defecto** para los mapas aleatorios: "encontrar
   el camino más corto" no tiene sentido si el camino ya está dibujado. Los mapas
   con ruta siguen disponibles (configuración y selector).
4. **Camino más corto medible:** eficiencia = largo del camino más corto posible
   dividido por lo recorrido, y entra en el fitness.
5. **ACO rutas sigue con mapas fijos:** aprende una ruta por mapa; con mapas
   nuevos cada generación empezaría de cero.
6. **Comparación estadística** sobre un conjunto fijo de mapas de validación, con
   intervalo de confianza y prueba de significancia.

## Plan (completado)

- [x] Generador: modo libre por defecto, obstáculos entre inicio y destino.
- [x] `resample_scenarios_every = 1`; estrategias que no generalizan, mapas fijos.
- [x] Largo del camino más corto por mapa; eficiencia y holgura mínima en las métricas; peso en el fitness.
- [x] `control/avoidance/`: contrato `ObstacleAvoider`, `AvoidanceController`, FTG, APF, registro.
- [x] `control/goal_controller.py` y plugin `optimization/reactive/` (referencia sin aprendizaje).
- [x] `training.avoidance` en configuración, `bootstrap`, CLI (`--avoidance`, `--maps`).
- [x] Estadísticas de validación ampliadas, intervalo de confianza, significancia; `RunRecord.avoidance`.
- [x] Interfaz: selectores de evasión y de mapas; resultados con curvas de validación.
- [x] Corridas de referencia de las combinaciones; capturas; documentación; informe.
