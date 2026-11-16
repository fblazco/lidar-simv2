# Simulador LiDAR con algoritmos evolutivos

Simulador 2D de un vehículo autónomo con un sensor LiDAR de 72 rayos, pensado
para **comparar algoritmos de búsqueda del camino más corto y de evasión de
obstáculos**. Eliges por separado quién aprende a navegar (algoritmo genético,
colonias de hormigas o una referencia sin aprendizaje) y quién esquiva (lo
aprendido, Follow the Gap o campos potenciales), entrenas sobre mapas
aleatorios que cambian en cada generación y comparas las corridas con las
mismas métricas y su significancia estadística. Incluye un editor visual de
mapas en ASCII.

![Tarjetas para elegir la navegación y la evasión](docs/images/preparar.png)

*Cada algoritmo se elige con una tarjeta que lo muestra funcionando en el
simulador: arriba, quién aprende el camino; abajo, quién esquiva.*

## Qué hace

- **Editor de mapas** sobre una grilla: caminos dibujados con el mouse,
  obstáculos estáticos (`X`), obstáculos dinámicos (`*`) con trayectoria
  horizontal, vertical o circular, inicio (`S`) con orientación y destino (`G`).
  Los mapas se guardan en JSON.
- **Simulación continua**: vehículo con posición, orientación, velocidad,
  dirección, aceleración y frenado; colisiones; LiDAR por raycasting geométrico.
- **Dos modos de navegación** con un mismo simulador: seguir la ruta dibujada
  (pudiendo apartarse para esquivar y volver) o navegar libremente al destino.
- **Navegación a elección** (quién decide hacia dónde ir):

  | Opción | Qué aprende |
  |---|---|
  | Genético (GA) | Los pesos de una red neuronal que conduce el vehículo |
  | Colonia de hormigas: reglas | Una tabla "situación → maniobra" elegida con feromonas |
  | Colonia de hormigas: rutas | Una ruta, celda a celda, sobre cada mapa de entrenamiento |
  | Sin aprendizaje | Nada: apunta al objetivo. Es la línea de base |

- **Evasión de obstáculos a elección** (quién esquiva), combinable con cualquier
  navegación:

  | Opción | Cómo esquiva |
  |---|---|
  | Aprendida | La navegación aprende a esquivar con lo que ve el LiDAR |
  | FTG (Follow the Gap) | Encara el hueco más ancho entre los obstáculos |
  | APF (campos potenciales) | El destino atrae y los obstáculos repelen |

- **Mapas aleatorios nuevos en cada generación**, de navegación libre: lo
  aprendido no puede memorizar un mapa. El mejor de cada generación se prueba
  en 20 mapas de validación que nunca intervienen en la selección.
- **Camino más corto medible**: cada mapa conoce el largo de su camino más
  corto, y la eficiencia de cada llegada entra en el fitness.
- **Con o sin ventana**: se entrena viendo `visible_agents` individuos a la vez,
  o desde la terminal sin abrir nada. Hay checkpoints y un registro por generación.
- **Tres temas de interfaz**: claro, oscuro y Aula Ubuntu, con papel cálido,
  tinta ciruela y acentos naranjas. Comparten disposición y se recorren desde
  el botón de la barra superior. Cada algoritmo trae su
  ícono y una escena del simulador que muestra cómo funciona.
- **Resultados y comparación estadística**: al finalizar un entrenamiento se
  muestran sus estadísticas y quedan guardadas; dos corridas se comparan lado a
  lado (éxito, colisiones, eficiencia del camino, tiempos), con el intervalo de
  confianza del éxito en validación y una prueba de significancia.
- **Arquitectura modular**: el simulador no conoce ningún algoritmo. Cada
  algoritmo de navegación o de evasión es un plugin; agregar otro (PSO, ABC,
  DWA, VFH) no exige tocar la física ni el vehículo.

## Requisitos

- Python 3.10 o superior.
- [Pygame](https://www.pygame.org/) 2.5+ y [NumPy](https://numpy.org/) 1.21+
  (`requirements.txt`); `pytest` para las pruebas (`requirements-dev.txt`).

Probado con Python 3.10, Pygame 2.6 y NumPy 2.2 en Linux.

## Instalación

```bash
git clone https://github.com/fblazco/lidar-sim.git
cd lidar-sim
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
```

En Ubuntu sin el paquete `python3-venv`, el segundo comando falla por falta de
`ensurepip`. Alternativa sin permisos de administrador (ajusta `3.10` a tu
versión de Python):

```bash
python3 -m venv --without-pip .venv
python3 -m pip install --target .venv/lib/python3.10/site-packages -r requirements-dev.txt
```

## Inicio rápido

```bash
.venv/bin/python main.py
```

1. Se abre el **Editor de mapas**. Pulsa "Cargar…" y elige `ejemplo_ruta`, o
   dibuja tu propio mapa.
2. Pasa a **Conducir**, en la barra superior, y maneja con las flechas o WASD.
3. En **Entrenar**, elige con las tarjetas quién navega y quién esquiva, el
   tipo de mapas y las generaciones, y pulsa "Empezar entrenamiento". Con `+`
   aceleras a los agentes visibles.
4. La corrida termina sola al llegar al límite de generaciones, o cuando pulsas
   "Finalizar". Se abre **Resultados** con sus estadísticas.
5. Repite con otra combinación ("Nueva corrida"): al finalizar, las dos
   aparecen comparadas.
6. Vuelve a **Conducir** y elige "Lo aprendido" para ver conducir al modelo.

El botón de la derecha de la barra recorre los temas claro, oscuro y Aula Ubuntu.

## La aplicación

### Editor de mapas (F1)

![Editor de mapas](docs/images/editor.png)

| Símbolo | Elemento | Herramienta |
|---|---|---|
| `-` `\|` `/` `\` | Camino | `1` arrastrar; el orden del trazo es el orden de la ruta |
| `X` | Obstáculo estático | `3` clic o arrastre |
| `*` | Obstáculo dinámico | `4` arrastrar: extremos (lineales) o centro y radio (circular) |
| `S` | Inicio del vehículo | `5` clic para ubicar, arrastrar para orientar |
| `G` | Destino | `6` clic |
| | Borrar | `2` clic o arrastre |

Al seleccionar un obstáculo dinámico se editan su velocidad, pausas, extremos,
radio y sentido. Bajo el mapa se indica si está listo para simular o qué falta.

### Conducir, Entrenar y Resultados (F2)

Son las tres vistas de la simulación. Se abren desde la barra superior o con
`M`, `T` y `C`.

![Conducción con el LiDAR visible](docs/images/manual.png)

- **Conducir (`M`)**: flechas o WASD. `R` reinicia, `N` genera un mapa aleatorio,
  `P` alterna entre el piloto manual y lo aprendido por el último entrenamiento.
  El vehículo se dibuja como `o` sobre `| |`, su LiDAR está siempre visible y
  una línea marca el camino recorrido. Al terminar el episodio aparece su
  resumen (resultado, tiempo, distancia, fitness).
- **Entrenar (`T`)**: primero se prepara la corrida con las tarjetas de la
  primera imagen. Al empezar se ve un agente en grande y los demás en
  miniatura; `Espacio` inicia o pausa, `F` finaliza, `+` y `-` cambian la
  velocidad. Se muestran la generación, los individuos evaluados, las cifras
  propias del algoritmo, la última generación (fitness, éxito, colisiones,
  eficiencia del camino), la validación y la evolución del fitness.

![Entrenamiento en modo oscuro](docs/images/entrenamiento.png)

*Una corrida en curso, en modo oscuro: el agente elegido, los demás en
miniatura y las cifras de la generación.*

![Colonia de hormigas trazando rutas](docs/images/feromonas.png)

*Colonia de hormigas de rutas: las celdas sombreadas son la feromona de cada
mapa y la línea es la ruta que sigue cada hormiga.*

- **Resultados (`C`)**: lista de corridas terminadas. Con una seleccionada se ve
  su resumen; con dos, si su diferencia es significativa, barras para lo
  esencial y, con "Todas las métricas", la tabla completa.

![Comparación de dos corridas](docs/images/comparacion.png)

Guía completa: [docs/GUIDE.md](docs/GUIDE.md).

## Entrenar y comparar sin ventana

```bash
.venv/bin/python main.py train --strategy genetic --avoidance learned --generations 30
.venv/bin/python main.py train --strategy genetic --avoidance ftg --generations 30
.venv/bin/python main.py train --strategy reactive --avoidance apf --generations 30
.venv/bin/python main.py runs
.venv/bin/python main.py compare genetic genetic_ftg
```

`--strategy` acepta `genetic`, `aco_rules`, `aco_routes` y `reactive`;
`--avoidance`, `learned`, `ftg` y `apf`; `--maps`, `free`, `route` y `mixed`.
Cada entrenamiento imprime su resumen al terminar y deja el checkpoint en
`models/<nombre>.npz`, una línea JSON por generación en `logs/<nombre>.jsonl` y
el registro de la corrida en `logs/runs/<nombre>.json`. `runs` lista las
corridas con sus cifras de validación, `compare` imprime la tabla comparativa y
la prueba de significancia, y `--resume models/<nombre>.npz` continúa una.

## Configuración

Todos los parámetros ajustables están en
[config/default.json](config/default.json): tema de la interfaz (`window.theme`:
`light`, `dark` o `ubuntu`), navegación, evasión, población,
agentes visibles, límite de generaciones, semilla, escenarios, pesos del
fitness, vehículo, LiDAR, red neuronal, generador de mapas y los parámetros de
cada algoritmo de navegación y de evasión. Para cambiarlos sin editar ese archivo, crea un JSON solo con lo que
quieras modificar:

```json
{"training": {"population_size": 80, "visible_agents": 6}, "lidar": {"max_range": 10.0}}
```

```bash
.venv/bin/python main.py --config mi_config.json
```

## Estructura del proyecto

```
main.py              entrada: ventana, o train / runs / compare sin ventana
bootstrap.py         ensambla el sistema a partir de la configuración
config/              parámetros (default.json)
simulation/          mundo, vehículo, obstáculos, colisiones, navegación
sensors/             LiDAR
control/             contrato Controller y controladores: manual, red MLP, tabla de reglas, seguidor de rutas, referencia
control/avoidance/   capa de evasión de obstáculos: aprendida, FTG, APF (plugins)
optimization/        contrato LearningStrategy, fitness, evaluación, entrenamiento, checkpoints, corridas
optimization/genetic/      plugin: algoritmo genético
optimization/aco_rules/    plugin: colonia de hormigas de reglas de conducción
optimization/aco_routes/   plugin: colonia de hormigas de rutas por mapa
optimization/reactive/     plugin de referencia: navegación sin aprendizaje
editor/              modelo del editor, guardado y carga, generador de mapas
rendering/           dibujo ASCII, paletas clara y oscura, escenas de los algoritmos
ui/                  ventana, temas, componentes, vistas e íconos propios
maps/                mapas guardados (incluye dos ejemplos)
models/  logs/       checkpoints, registros y corridas (no se versionan)
tests/               pruebas automáticas
docs/                especificación, arquitectura, estado y solicitudes
```

Cada plugin lleva además su ícono (`icon.svg`) y su escena (`demo.json`): la
interfaz los muestra sin conocer ningún algoritmo por nombre.

La regla central: **el simulador, el vehículo, el sensor y el editor no
dependen de ningún algoritmo de aprendizaje**. Si se borra la carpeta de
cualquier algoritmo, todo lo demás sigue funcionando, y una prueba lo
comprueba. Detalle en [docs/architecture/OVERVIEW.md](docs/architecture/OVERVIEW.md).

## Pruebas

```bash
.venv/bin/python -m pytest
```

Cubren movimiento, colisiones, LiDAR, trayectorias de obstáculos, mapas,
reproducibilidad por semilla, los algoritmos de navegación y de evasión, el
camino más corto, fitness, evolución de generaciones, corridas, comparación y
su estadística, los temas, íconos y escenas, la aplicación (sin ventana real),
la independencia entre el
simulador y los algoritmos, y los enlaces de esta documentación.

## Estado

Qué está verificado, qué es parcial, qué falta y los resultados medidos de cada
algoritmo: [docs/status/PROJECT_STATUS.md](docs/status/PROJECT_STATUS.md).
Lo que sigue: [docs/status/ROADMAP.md](docs/status/ROADMAP.md).

## Documentación

| Documento | Contenido |
|---|---|
| [docs/README.md](docs/README.md) | Índice y forma de trabajo |
| [docs/GUIDE.md](docs/GUIDE.md) | Uso de la aplicación y de la configuración |
| [docs/specification/](docs/specification/) | Requisitos del proyecto (editables) |
| [docs/architecture/](docs/architecture/) | Organización, contratos y decisiones |
| [docs/status/](docs/status/) | Estado, roadmap, backlog y problemas conocidos |
| [docs/CHANGELOG.md](docs/CHANGELOG.md) | Historial de cambios |

## Cómo pedir cambios

Los requisitos se cambian en Markdown, sin tocar el código: editando un
documento de `docs/specification/` o creando una solicitud en
`docs/requests/open/` a partir de la plantilla. El procedimiento está en
[docs/requests/README.md](docs/requests/README.md).
