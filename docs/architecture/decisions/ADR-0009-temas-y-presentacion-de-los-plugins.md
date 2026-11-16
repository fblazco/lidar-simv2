# ADR-0009: Temas de la interfaz y presentación de cada algoritmo dentro de su plugin

Fecha: 2026-11-15 · Estado: aceptada

## Contexto

El usuario pidió rehacer la interfaz: más amigable, en blancos, grises y negros
metálicos, con un modo claro y uno oscuro; elegir los algoritmos con íconos en
vez de flechas; y, donde antes había un texto que describía cada algoritmo,
mostrar "una explicación visual… no un dibujo, sino como una imagen de la
simulación". Eligió las maquetas en una conversación (ver la solicitud
`requests/done/2026-11-15-rediseno-de-la-interfaz.md`).

Dos reglas del proyecto condicionan cómo hacerlo:

- La interfaz no puede conocer ningún algoritmo por nombre: agregar uno no debe
  exigir tocar `ui/`, y borrar su carpeta no debe romper nada.
- Pygame vive solo en `rendering/` y `ui/`: un plugin no puede dibujar.

## Decisión

1. **Un diseño, dos temas.** `ui/theme.py` define `Theme` (colores de la
   interfaz) y `rendering/palette.py` define `WorldPalette` (colores del
   simulador). Hay un tema claro y uno oscuro; comparten la disposición de
   pantalla y solo cambian los colores. Ninguna vista escribe un color: lo toma
   del tema activo. El tema inicial sale de `window.theme` y se cambia en la
   barra superior.
2. **Sin tono.** Las paletas son grises fríos. Lo que antes distinguía un color
   (llegó, chocó, corrida A o B) ahora lo distinguen el símbolo, el brillo, el
   texto o el trazo (línea sólida y línea cortada; barra maciza y barra con
   contorno).
3. **El ícono y la escena viajan con el plugin.** `StrategyPlugin` y
   `AvoidancePlugin` ganan dos campos opcionales: `icon` (ruta de un SVG de un
   solo color, que la interfaz tiñe con el color del tema) y `demo` (ruta de un
   JSON con una escena). Los archivos están en la carpeta del plugin. La
   interfaz los carga sin saber de qué algoritmo son; si faltan, muestra la
   inicial del nombre y la descripción.
4. **La escena es un dato, no una imagen.** Una escena guarda un mapa y una
   lista de operaciones en coordenadas del mundo (rayos del LiDAR de un
   instante, recorridos, flechas, sectores, celdas con intensidad).
   `rendering/scene.py` la dibuja con el mismo renderizador del simulador y con
   la paleta activa. Las escenas incluidas se capturaron de corridas reales con
   los modelos de referencia.

## Consecuencias

- Agregar un algoritmo sigue sin tocar la interfaz: aparece con su tarjeta. Su
  ícono y su escena son opcionales.
- Las escenas se ven bien en los dos temas y a cualquier tamaño, y ocupan pocos
  kilobytes; no hay imágenes duplicadas por tema.
- Una escena es una foto fija: no cambia con la configuración del usuario ni se
  anima. Convertirla en explicación interactiva queda para la etapa educativa.
- El contrato de los plugins creció con dos campos opcionales; los plugins
  anteriores siguen siendo válidos.
- `rendering/` conoce un formato más (la escena), documentado en
  `MODULE_CONTRACTS.md`. Una operación desconocida se ignora, para poder
  ampliarlo.
- Sin color, dos estados solo se distinguen si además cambian de forma o de
  texto: toda vista nueva debe respetarlo.

## Alternativas descartadas

- **Imágenes PNG por algoritmo y por tema.** Simples, pero duplican archivos,
  se ven mal al cambiar de tamaño y no pueden usar los colores del tema.
- **Íconos y explicaciones dentro de `ui/`, indexados por nombre de
  algoritmo.** Rompe la regla de que la interfaz no conoce algoritmos: cada
  plugin nuevo obligaría a editarla.
- **Que el plugin dibuje su explicación.** Obligaría a importar Pygame fuera de
  `rendering/` y `ui/`.
- **Simulación en vivo dentro de cada tarjeta.** Necesita un modelo ya
  entrenado para los algoritmos que aprenden, que no existe al abrir la
  aplicación por primera vez.
- **Un color de acento para los estados.** Se propuso; el usuario eligió
  estilos estrictamente monocromos.
