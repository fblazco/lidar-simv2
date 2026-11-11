# ADR-0002: Estrategias con contrato pedir/informar y plugins descubiertos

Fecha: 2026-11-11

## Contexto

GA, PSO, ACO y ABC tienen representaciones y ciclos distintos. Hace falta una
interfaz común que no los fuerce a compartir genoma, y que permita agregar o
quitar un algoritmo sin modificar el resto.

## Decisión

- `LearningStrategy` expone `ask()` / `tell(results)`: la estrategia entrega
  candidatos y recibe sus resultados. `Candidate.solution` es opaca.
- Cada plugin entrega, junto con su estrategia, una `controller_factory` que
  convierte una solución en un `Controller`. La estrategia no conoce redes ni
  vehículos; el evaluador no conoce la representación.
- Los plugins son subpaquetes de `optimization/` que exponen `PLUGIN`.
  `discover_plugins()` los encuentra; nadie los importa por nombre.

## Alternativas consideradas

- Clase base con `population` y operadores genéricos: obligaría a PSO, ACO y
  ABC a imitar a GA.
- Que la estrategia construya los controladores: mezcla optimizador y política.
- Registro manual en `main.py`: borrar la carpeta de un algoritmo rompería la app.

## Consecuencias

- GA evoluciona vectores reales y reutiliza `MLPControllerFactory`; PSO y ABC
  podrán reutilizarla tal cual. ACO puede aportar su propio controlador.
- Algoritmos con varias fases por ciclo (ABC) pueden devolver distintas tandas
  en `ask()` sucesivos.
- Si no hay plugins instalados, la aplicación funciona y solo se deshabilita el
  entrenamiento.
