# Solicitud: Rediseño de la interfaz en modo claro y oscuro

> Llegó por conversación el 2026-11-15, en cuatro mensajes. Los textos entre
> comillas son literales.

## Objetivo

"ok, ahora trabajemos en la interfaz, quiero que sea mas amigable en el
approach, con tonos metalicos blancos, grises y negros, amigable en el approach.
ese es el primer camino. pero antes de hacerlo quiero que discutamos que estilos
podriamos tomar siguiendo eso. me des imagen de ejemplo y segun eso lo cambiamos.
en esta ocasion no cambiaremos codigo, solo quieo que me generes imagenes de las
vistas que tendria con distintos tipo de disenos. lo otro quiero que por cada
modelo donde ahora sale el texto salga como una explicacion visual de como
funciona cada algoritmo. ahora agragalo a la imagen simplemente. no quiero un
dibujo si no como una imagen de la simulacion. y quiero que a la hora de
seleccionar algoritmos en vez de con flechas, tengamos como un selector donde
hayan como icono, por ejemplo para genetico un adn y para ACO ant colony, una
ormiga con casco militar."

## Cambios solicitados

- Interfaz más amigable, en tonos metálicos blancos, grises y negros.
- Antes de cambiar el código: maquetas de las vistas en distintos estilos, para
  elegir.
- Donde aparecía el texto de cada algoritmo, una explicación visual que se vea
  como una imagen de la simulación, no como un dibujo.
- Elegir los algoritmos con un selector de íconos en vez de flechas: ADN para el
  genético y una hormiga con casco militar para las colonias de hormigas.

## Lo que se decidió en la conversación

1. Se presentaron tres estilos, cada uno en tres vistas: A "Aluminio" (paneles
   claros, pantallas oscuras), B "Grafito" (todo oscuro, barra lateral) y C
   "Blanco" (todo claro, tarjetas con imagen por algoritmo).
2. El usuario eligió: **"deja la opcion C y B como modo oscuro"**.
3. Como C y B tenían disposiciones de pantalla distintas, se le preguntó cuál
   usar en el modo oscuro. Eligió **"La de C"**: una sola disposición y dos
   temas; solo cambian los colores.
4. Se completaron las maquetas de las cinco vistas en los dos modos y el usuario
   respondió **"Sí, implementar"**.

## Decisiones tomadas al implementar (sin consultar)

- **El ícono y la escena de cada algoritmo viven en su plugin**, no en la
  interfaz, para respetar que agregar o borrar un algoritmo no toque `ui/`
  (ADR-0009).
- **La explicación visual es una escena fija**: un cuadro real del simulador con
  capas dibujadas encima, guardado como datos y dibujado por la aplicación con
  el tema activo. No es una animación.
- **Tipografía del sistema** (Ubuntu o DejaVu Sans, y DejaVu Sans Mono) en lugar
  de las fuentes de las maquetas (Outfit, DM Mono): usarlas exigía descargar y
  agregar archivos de fuentes.
- **Nombres de las tarjetas**: los nombres breves que ya tenían los plugins
  ("ACO reglas", "ACO rutas") en lugar de "Hormigas: reglas / rutas".
- **Estrictamente sin color**, como en los estilos elegidos. La pregunta sobre
  un color de acento para los estados quedó sin respuesta.
- **Tema inicial claro**, configurable en `window.theme`. El tema elegido con el
  botón no se guarda entre sesiones.
- **Cuatro secciones en la barra superior** (Editor de mapas, Conducir, Entrenar,
  Resultados); por dentro siguen siendo los dos modos de siempre y `F1`, `F2`,
  `M`, `T` y `C` siguen funcionando.
- **Comparación**: resumen con barras y recuadros, y la tabla completa con el
  botón "Todas las métricas", para no perder ninguna cifra de las que ya se
  mostraban.
- **Camino recorrido** dibujado al conducir y en cada agente del entrenamiento.

## Plan (completado)

1. Paletas del simulador y renderizador con temas.
2. Escenas de cada algoritmo como datos y su dibujo.
3. Íconos y escenas dentro de cada plugin; campos `icon` y `demo`.
4. Temas y componentes de la interfaz.
5. Barra superior, editor, conducción, entrenamiento (preparar y en curso) y
   resultados.
6. Pruebas, capturas y documentación.

## Estado

Implementada y verificada el 2026-11-15. Informe:
`reports/2026-11-15-rediseno-de-la-interfaz.md`.
