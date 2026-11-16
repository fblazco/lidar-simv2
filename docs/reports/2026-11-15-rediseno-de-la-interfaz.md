# Informe: rediseño de la interfaz en modo claro y oscuro

Fecha: 2026-11-15 · Solicitud: `docs/requests/done/2026-11-15-rediseno-de-la-interfaz.md`

## 1. Objetivo de la tarea

Rehacer la interfaz para que sea más amigable, en tonos metálicos blancos,
grises y negros; elegir los algoritmos con íconos en lugar de flechas; y mostrar,
donde antes había un texto, una explicación visual de cada algoritmo que se vea
como una imagen de la simulación.

El usuario pidió discutir primero los estilos con maquetas. Se le presentaron
tres; eligió el estilo blanco como modo claro y los colores del estilo grafito
como modo oscuro, con una sola disposición de pantalla para los dos, y después
pidió implementarlo.

## 2. Qué se implementó

- **Dos temas, un diseño.** Modo claro (blanco, líneas finas, botones negros) y
  modo oscuro (grafito, botones plateados). Se cambia con un botón de la barra
  superior; el inicial sale de `window.theme`. No hay colores: solo blancos,
  grises y negros.
- **Barra superior** con cuatro secciones: Editor de mapas, Conducir, Entrenar y
  Resultados. Los atajos `F1`, `F2`, `M`, `T` y `C` se conservan.
- **Editor**: barra de herramientas con el símbolo que coloca cada una, el mapa
  en una tarjeta con su nombre y su modo de navegación, y un panel con las
  propiedades del obstáculo móvil elegido, el tamaño y los archivos.
- **Conducir**: selector de piloto, cifras del episodio en recuadros, ayuda de
  teclado y el camino recorrido dibujado.
- **Entrenar, preparar la corrida**: una tarjeta por algoritmo de navegación y
  de evasión, con su ícono, su descripción y una escena del simulador que lo
  muestra funcionando; tipo de mapas, generaciones y mapa del editor.
- **Entrenar, corrida en curso**: un agente en grande y los demás en miniatura,
  con su camino recorrido; generación, avance y cifras del algoritmo; tarjetas
  de última generación, validación y evolución del fitness.
- **Resultados**: lista con los íconos de cada corrida; resumen de una, o
  comparación de dos con barras, recuadros y la tabla completa a pedido.
- **Íconos y escenas dentro de cada plugin**: ADN para el genético, hormiga con
  casco para las dos colonias (con flechas de maniobra o con un rastro), y los
  de la referencia, la evasión aprendida, FTG y APF.

## 3. Archivos creados

- `rendering/palette.py`, `rendering/scene.py`
- `ui/theme.py`, `ui/assets/icons/` (10 íconos de la interfaz)
- `optimization/genetic/`, `aco_rules/`, `aco_routes/`, `reactive/`: `icon.svg`
  y `demo.json` en cada una
- `control/avoidance/assets/`: `learned`, `ftg` y `apf`, cada uno `.svg` y `.json`
- `tests/test_theme.py`
- `docs/architecture/decisions/ADR-0009-temas-y-presentacion-de-los-plugins.md`
- `docs/requests/done/2026-11-15-rediseno-de-la-interfaz.md`
- `docs/images/preparar.png`
- Este informe.

## 4. Archivos modificados

- Dibujo: `rendering/renderer.py` (paleta intercambiable, rayos suavizados,
  camino recorrido, obstáculos con fondo).
- Interfaz, rehecha: `ui/widgets.py`, `ui/application.py`, `ui/editor_view.py`,
  `ui/simulation_view.py`, `ui/training_panel.py`, `ui/results_view.py`. La
  lógica de las vistas (entrenar, guardar, comparar) no cambió.
- Contratos: `optimization/registry.py` y `control/avoidance/base.py` (campos
  `icon` y `demo`); los siete plugins los declaran.
- `config/default.json` (`window.theme`), `tests/test_app_smoke.py`.
- Documentación: `README.md`, `CLAUDE.md`, `docs/GUIDE.md`, `docs/CHANGELOG.md`,
  `docs/specification/PROJECT_SPEC.md`, `docs/architecture/OVERVIEW.md`,
  `MODULE_CONTRACTS.md`, `docs/status/PROJECT_STATUS.md`, `ROADMAP.md`,
  `BACKLOG.md`, `KNOWN_ISSUES.md` y las capturas de `docs/images/`.

## 5. Decisiones técnicas adoptadas

La decisión arquitectónica está en ADR-0009. Las que el usuario no llegó a ver
están también listadas en la solicitud.

1. **El ícono y la escena de cada algoritmo viven en su plugin** (`icon`,
   `demo`). La interfaz los carga sin conocer ningún algoritmo por nombre; si
   faltan, muestra la inicial y la descripción.
2. **La explicación visual es una escena guardada como datos**: el mapa y una
   lista de operaciones en coordenadas del mundo, que la aplicación dibuja con
   su propio renderizador y con el tema activo. Las siete escenas se capturaron
   de corridas reales con los modelos de referencia.
3. **Sin color.** Los estados se distinguen por texto, brillo, trazo y relleno.
4. **Fuentes del sistema** en lugar de las de las maquetas.
5. **Formas suavizadas**: tarjetas, botones e íconos se dibujan al triple de
   tamaño y se reducen; el resultado se guarda para no repetirlo en cada cuadro.
6. **La lógica de las vistas se conservó tal cual**; solo se reescribió el
   dibujo y la resolución de clics. Por eso las 26 pruebas de la aplicación que
   ya existían pasaron sin cambios.
7. **Se agregaron**, respecto de las maquetas: el estado "corrida en pausa /
   terminada", el enlace "Nueva corrida", el interruptor para sumar el mapa del
   editor y la tabla "Todas las métricas".

## 6. Pruebas ejecutadas y resultados

| Comprobación | Resultado |
|---|---|
| `.venv/bin/python -m pytest` (suite completa) | **371 pasaron, 0 fallaron** (29 archivos, ≈ 58 s) |
| Pruebas de la aplicación anteriores al rediseño | Las 26 pasan sin modificarlas |
| Temas: legibilidad del texto (contraste), solo grises, paletas del simulador | `test_theme` |
| Cada plugin trae ícono y escena válidos; íconos teñidos; escenas dibujadas en los dos temas | `test_theme` |
| Cambio de tema, las cuatro secciones con el mouse, barra de herramientas del editor, pantalla de preparación, plugin sin ícono ni escena, resumen y tabla de la comparación | `test_app_smoke` (7 pruebas nuevas) |
| El proyecto funciona al borrar cada plugin de navegación | `test_architecture` |
| Capturas de las cinco vistas en los dos temas, a 1280×800 y a 1000×640 | Revisadas; se ajustaron el espaciado de las barras y el alto de los valores resaltados |

**No ejecutado:** la aplicación no se abrió en una ventana real. Todo se
comprobó con el driver de video `dummy` de SDL (pruebas y capturas). No se
probaron el redimensionado en vivo, el teclado real ni otras resoluciones.

## 7. Limitaciones conocidas

Ver `status/KNOWN_ISSUES.md`. Las principales:

- Falta el recorrido manual en una ventana real.
- El tema elegido con el botón no se guarda entre sesiones.
- Las escenas son fijas y el guion que las generó no está en el repositorio.
- Las fuentes dependen del sistema; no son las de las maquetas.
- Por debajo de 1000×640 hay textos recortados.

## 8. Tareas pendientes y recomendaciones

1. Abrir la aplicación y recorrer cada sección en los dos temas.
2. Revisar las decisiones de la sección 5, en especial las fuentes del sistema
   y que las escenas sean fijas.
3. Decidir si se quiere un color de acento para los estados: la pregunta quedó
   abierta.
4. La etapa educativa (14 del roadmap) puede partir de estas escenas:
   animarlas y dibujarlas en vivo durante la simulación.
