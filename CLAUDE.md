# CLAUDE.md

Instrucciones permanentes para Claude Code en este repositorio. La documentación
detallada vive en `docs/`; este archivo solo dice qué leer y qué reglas respetar.

## Qué es

Simulador 2D (Python, Pygame, NumPy) de un vehículo autónomo con un LiDAR de 72
rayos que aprende a navegar mediante algoritmos evolutivos. Incluye un editor
visual de mapas en ASCII. El algoritmo lo elige el usuario entre tres plugins:
algoritmo genético (`genetic`), colonia de hormigas de reglas (`aco_rules`) y
colonia de hormigas de rutas (`aco_routes`). PSO y ABC podrán sumarse igual.

## Objetivos

1. Crear, guardar y cargar mapas con caminos, obstáculos estáticos y dinámicos.
2. Simular vehículos de movimiento continuo con LiDAR por raycasting.
3. Entrenar con el algoritmo que elija el usuario, con o sin ventana.
4. Ver varios individuos de una generación a la vez y cómo evoluciona el fitness.
5. Mostrar las estadísticas de un entrenamiento al finalizarlo y comparar dos.

## Principios arquitectónicos (no negociables)

- **La modularidad es la prioridad.** El simulador no conoce ningún algoritmo de
  aprendizaje y debe funcionar sin ellos (p. ej. con control manual).
- **Tres conceptos separados:** simulador (mundo físico), móvil (entidad con
  sensor y controlador inyectados) y estrategia de aprendizaje (optimizador).
- **Controller ≠ LearningStrategy.** El controlador convierte observaciones en
  acciones; la estrategia genera y optimiza soluciones. Se conectan con una
  `controller_factory`, nunca importándose entre sí.
- **Dependencias inyectadas.** El móvil no importa clases de algoritmos.
- **Prueba de fuego:** borrar la carpeta de cualquier algoritmo no debe romper
  simulador, editor, vehículos, sensores ni obstáculos; agregar un algoritmo
  nuevo no debe exigir tocar la física, el móvil ni la interfaz.
  `tests/test_architecture.py` lo verifica. Ningún plugin importa a otro.
- No forzar a todos los algoritmos a usar la misma representación interna.
- No crear clases vacías ni implementaciones simuladas de algoritmos futuros.

## Restricciones técnicas

- Python 3, Pygame, NumPy y JSON. No agregar dependencias sin justificarlo.
- Sin variables globales para compartir estado del simulador.
- Parámetros ajustables en `config/default.json`, no en el código.
- Movimiento y colisiones independientes del renderizado; paso de tiempo fijo.
- Pygame solo en `rendering/` y `ui/`. El entrenamiento debe correr sin ventana
  y nunca bloquear el ciclo de Pygame.
- Las dimensiones de entrada de la red salen solo de `ObservationBuilder.size`.
- La ruta es una lista ordenada de celdas; nunca interpretar caracteres ASCII.

## Estructura

```
main.py            entrada: ventana, o train / runs / compare sin ventana
bootstrap.py       ensamblado: construye todo a partir de la configuración
config/            default.json y cargador
simulation/        mundo, vehículo, obstáculos, colisiones, navegación
sensors/           LiDAR
control/           contrato Controller y controladores: manual, política MLP, tabla de reglas, seguidor de rutas
optimization/      contrato LearningStrategy, fitness, evaluación, sesión, checkpoints, corridas y comparación
optimization/genetic/      plugin: algoritmo genético
optimization/aco_rules/    plugin: colonia de hormigas de reglas de conducción
optimization/aco_routes/   plugin: colonia de hormigas de rutas por mapa
editor/            modelo del editor, guardado/carga, generador aleatorio
rendering/         dibujo ASCII en Pygame
ui/                ventana, vistas, panel de entrenamiento y resultados
maps/ models/ logs/     datos del usuario (mapas, checkpoints, registros, corridas en logs/runs/); maps/ejemplo_* son de muestra
tests/             pruebas (pytest)
docs/              documentación viva
```

Dependencias permitidas: ver `docs/architecture/OVERVIEW.md`.

## Antes de implementar cualquier tarea

1. Leer este archivo.
2. Consultar `docs/README.md` y `docs/status/PROJECT_STATUS.md`.
3. Leer la especificación (`docs/specification/`) y la arquitectura
   (`docs/architecture/`) relacionadas con la tarea.
4. Inspeccionar el código existente.
5. Revisar `git status` para no sobrescribir cambios del usuario.

## Reglas de desarrollo

- Implementar por etapas; escribir la prueba antes que el código y comprobar
  que cada parte funciona antes de continuar.
- Ejecutar la suite completa antes de dar algo por terminado:
  `.venv/bin/python -m pytest`
- No reescribir lo que ya funciona. Preferir lo simple; no agregar complejidad
  sin una necesidad concreta.
- Identificadores en inglés; comentarios, textos de interfaz y documentación en
  español.
- No hacer commits salvo que el usuario lo pida.

## Los documentos del usuario son parte del contrato

- `docs/specification/` y `docs/requests/open/` los edita el usuario. Su versión
  actual es la referencia.
- Una solicitud en `docs/requests/open/` **no autoriza su implementación**: el
  usuario debe pedir expresamente que se revise, discuta o implemente.
- No modificar una especificación para que coincida con lo implementado. Si algo
  está implementado distinto, documentar la diferencia en `PROJECT_STATUS.md`.
- No sobrescribir solicitudes ni borrar comentarios del usuario.
- Si hay contradicciones entre documentos, explicarlas antes de decidir.

## Después de implementar

1. Ejecutar las pruebas relevantes y la suite completa.
2. Actualizar `docs/status/PROJECT_STATUS.md` (solo marcar como implementado lo
   verificado) y `docs/CHANGELOG.md`.
3. Actualizar `docs/architecture/` si cambió un contrato o una dependencia;
   registrar un ADR en `docs/architecture/decisions/` solo para decisiones
   arquitectónicas relevantes.
4. Actualizar `docs/status/BACKLOG.md` y `KNOWN_ISSUES.md` cuando corresponda.
5. Crear un informe en `docs/reports/YYYY-MM-DD-nombre-de-la-tarea.md`. No
   afirmar que una prueba se ejecutó si no se ejecutó.
6. Si la tarea venía de una solicitud: actualizar su estado y moverla a
   `docs/requests/done/`.
7. Si cambió la interfaz o los símbolos, actualizar las capturas de
   `docs/images/` y el `README.md`.
8. Resumir al usuario qué se construyó, cómo probarlo y qué quedó pendiente.

Mantener la documentación sin duplicados (cada dato vive en un solo lugar) y
**completa**: ningún documento, carpeta o sección debe quedar a medio rellenar.
El `README.md` debe bastar para entender qué es el proyecto, verlo e instalarlo
sin abrir nada más. `tests/test_docs.py` comprueba enlaces y mapas de ejemplo.
