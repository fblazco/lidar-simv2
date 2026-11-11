# ADR-0001: Simulador independiente del aprendizaje, con dependencias inyectadas

Fecha: 2026-11-11

## Contexto

El requisito central es que el simulador, el móvil, el sensor y el editor no
dependan de ningún algoritmo de aprendizaje, y que el controlador de un móvil
sea intercambiable.

## Decisión

- El contrato `Controller` / `Action` / `Observation` vive en
  `control/controller.py`: solo datos e interfaces.
- `simulation/` importa de `control` únicamente ese módulo.
- El `Mobile` recibe su sensor y su controlador por el constructor. El sensor
  es cualquier objeto con `scan`, `num_rays` y `max_range`, así que `simulation/`
  tampoco importa `sensors/`.
- `SimulationFactory` y `bootstrap.py` son los únicos lugares donde se ensamblan
  las piezas concretas.
- `tests/test_architecture.py` revisa los imports y además ejecuta el proyecto
  en una copia sin `optimization/genetic/`.

## Alternativas consideradas

- Definir el contrato dentro de `simulation/`: dejaría a `control/` dependiendo
  del simulador y dificultaría probar controladores de forma aislada.
- Que el móvil cree su propio controlador según un nombre: acopla el móvil a
  las clases concretas, lo contrario de lo pedido.

## Consecuencias

- Se puede simular con control manual sin cargar ningún código de optimización.
- Cualquier controlador nuevo se conecta sin tocar `simulation/`.
- El simulador entrega una `Observation` estructurada; decidir qué entra a una
  red es responsabilidad de `ObservationBuilder`, del lado del controlador.
