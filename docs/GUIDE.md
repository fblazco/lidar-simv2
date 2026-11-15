# Guía de uso

## Abrir la aplicación

```bash
.venv/bin/python main.py
```

Una sola ventana con dos modos: **F1 Editor de mapas** y **F2 Simulación**.

## Modo 1: Editor

![Editor de mapas](images/editor.png)

| Herramienta | Tecla | Uso |
|---|---|---|
| Camino | 1 | Arrastrar. El orden en que se dibuja es el orden de la ruta. |
| Borrar | 2 | Clic o arrastre sobre la celda. |
| Obstáculo X | 3 | Clic o arrastre. |
| Móvil * | 4 | Elegir Horizontal, Vertical o Circular y arrastrar: en los lineales, de un extremo al otro (empieza en el primero); en el circular, del centro a la posición inicial. Clic sin arrastrar usa un recorrido por defecto. Clic sobre uno existente lo selecciona para editar velocidad, pausa, extremos, radio y sentido. `Supr` lo elimina. |
| Inicio S | 5 | Clic para ubicar el vehículo; arrastrar para orientarlo. |
| Destino G | 6 | Clic. |

El panel permite además elegir el modo de navegación (seguir ruta o libre),
cambiar el tamaño de la grilla, poner nombre, guardar y cargar (`maps/*.json`),
generar un mapa aleatorio y vaciar el mapa. Abajo se indica si el mapa está
listo para simular o qué le falta.

El repositorio trae dos mapas de ejemplo en `maps/`: `ejemplo_ruta` (seguimiento
de ruta, con los tres tipos de obstáculo móvil) y `ejemplo_libre` (navegación
libre). Se abren con "Cargar...".

Símbolos: `|` `-` `/` `\` caminos, `X` obstáculo estático, `*` obstáculo
dinámico, `S` inicio, `G` destino, `o` sobre `| |` el vehículo.

## Modo 2: Simulación

Tiene tres vistas: **M** Manual, **T** Entrenar y **C** Resultados.

### Manual (M)

![Conducción manual](images/manual.png)

Se conduce el mapa del editor con flechas o WASD. Si el mapa está incompleto se
usa uno aleatorio. `R` reinicia, `N` genera otro mapa y `P` alterna entre el
piloto manual y **lo aprendido** por el último entrenamiento.

Cuando el episodio termina (el vehículo llega, choca o se queda sin tiempo)
aparece su resumen: resultado, tiempo, distancia, velocidad media, avance,
desvío medio, suavidad y el fitness que habría obtenido.

Con la colonia de rutas, "lo aprendido" solo existe para los mapas con que
entrenó: si el mapa actual no es uno de ellos, se muestra el primero de
entrenamiento.

### Entrenar (T)

![Entrenamiento](images/entrenamiento.png)

| Control | Tecla | Qué hace |
|---|---|---|
| Algoritmo `<` `>` | | Elige con qué algoritmo entrenar. Se aplica al pulsar Nuevo o al iniciar por primera vez. |
| Iniciar / Pausar | Espacio | Arranca o detiene el entrenamiento. |
| Nuevo | | Descarta el entrenamiento actual y prepara otro con el algoritmo elegido. |
| Finalizar | F | Da por terminada la corrida, guarda su registro y muestra sus estadísticas. |
| Velocidad `-` `+` | `-` `+` | Velocidad de los agentes visibles (x1 a x32). |
| Límite `-` `+` | | Generaciones tras las que la corrida finaliza sola. "Sin límite" entrena hasta pulsar Finalizar. |
| Guardar checkpoint / Cargar último | | Guarda en `models/` o retoma el más reciente. |
| Usar el mapa del editor | | Suma ese mapa a los de cada individuo (al pulsar Nuevo). |

Se muestran `visible_agents` individuos de la generación en curso, cada uno en
su propio escenario; el resto se evalúa sin dibujarse. Cada vista indica el
número de individuo, el episodio en curso (uno por escenario), su fitness
parcial y su estado. El vehículo se ve blanco mientras está activo, rojo si
chocó, verde si llegó y gris si se le acabó el tiempo. El entrenamiento solo
avanza mientras esta vista está abierta.

**Algoritmos disponibles**

| Algoritmo | Qué aprende | Validación en mapas no vistos |
|---|---|---|
| Genético | Los pesos de una red neuronal que conduce | Sí |
| ACO reglas | Una tabla "situación del LiDAR y del objetivo → maniobra", elegida con feromonas | Sí |
| ACO rutas | Una ruta celda a celda sobre cada mapa de entrenamiento | No aplica |

![Colonia de rutas con sus feromonas](images/feromonas.png)

Con ACO rutas se ven las feromonas de cada mapa (manchas anaranjadas, más
intensas donde se concentra el rastro) y, en azul, la ruta que sigue cada hormiga.
Para que la colonia aprenda un mapa propio, dibújalo en el editor y activa
"Usar el mapa del editor" antes de pulsar Nuevo.

### Resultados (C)

![Comparación de dos corridas](images/comparacion.png)

Cada corrida finalizada queda en la lista, de la más reciente a la más antigua.

- **Una seleccionada:** su resumen (mejor fitness, tasas de éxito, generación del
  primer éxito, validación, colisiones, tiempos) y sus curvas de fitness y de éxito.
- **Dos seleccionadas (A y B):** la misma tabla lado a lado, con el mejor valor
  de cada fila en verde, y las curvas de ambas superpuestas. Si no usaron los
  mismos mapas, se avisa.

Al finalizar una corrida se abre esta vista con ella como A y, si existe, la
última corrida de otro algoritmo como B.

## Línea de comandos

```bash
.venv/bin/python main.py train --strategy aco_rules --generations 30
.venv/bin/python main.py train --strategy genetic --generations 30
.venv/bin/python main.py runs
.venv/bin/python main.py compare genetic aco_rules
```

- `train` entrena sin ventana. `--strategy` elige el algoritmo (`genetic`,
  `aco_rules`, `aco_routes`); `--name` cambia el nombre de la corrida (por
  defecto, el del algoritmo); `--resume models/<nombre>.npz` continúa una.
  Al terminar imprime el resumen y deja el checkpoint en `models/<nombre>.npz`,
  una línea JSON por generación en `logs/<nombre>.jsonl` y el registro de la
  corrida en `logs/runs/<nombre>.json`.
- `runs` lista las corridas terminadas (también las hechas desde la ventana).
- `compare A B` imprime la tabla comparativa; un asterisco marca el mejor valor.

## Configuración

Todos los parámetros están en `config/default.json`. Para cambiarlos sin
tocarlo, crear un JSON solo con las claves a modificar y pasarlo con `--config`:

```json
{"training": {"population_size": 80, "visible_agents": 6}, "lidar": {"max_range": 10.0}}
```

| Sección | Qué controla |
|---|---|
| `window` | tamaño de ventana y cuadros por segundo |
| `map` | tamaño de grilla por defecto |
| `simulation` | paso de tiempo, límite del episodio, radio de llegada |
| `vehicle` | radio, velocidades, aceleración, ángulo de dirección |
| `lidar` | rayos, campo de visión, alcance |
| `observation`, `policy` | entradas de la red y capas ocultas |
| `training` | algoritmo (`strategy`), `population_size`, `visible_agents`, semilla, escenarios, `max_iterations`, checkpoints |
| `fitness` | pesos de la función de fitness |
| `generator` | mapas aleatorios |
| `genetic` | elitismo, torneo, crossover, mutación |
| `rule_policy` | distancias "cerca" y "medio" de la tabla de reglas |
| `aco_rules` | alfa, beta, evaporación, hormigas que depositan, cotas de feromona |
| `aco_routes` | lo mismo, más atracción al camino dibujado, holgura junto a obstáculos y parámetros del seguidor de rutas |

`population_size` es también el número de hormigas de las colonias.

## Pruebas

```bash
.venv/bin/python -m pytest
```
