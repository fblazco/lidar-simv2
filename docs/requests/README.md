# Solicitudes

Espacio para pedir cambios al proyecto en Markdown, sin tocar el código.

| Carpeta o archivo | Contenido |
|---|---|
| [TEMPLATE.md](TEMPLATE.md) | Plantilla de una solicitud |
| `open/` | Solicitudes pendientes o en discusión |
| `done/` | Solicitudes ya implementadas y verificadas |

Hoy no hay solicitudes abiertas ni cerradas: la primera versión se construyó a
partir de la especificación, no de solicitudes.

## Cómo crear una

1. Copiar la plantilla con un nombre descriptivo:
   ```bash
   cp docs/requests/TEMPLATE.md docs/requests/open/agregar-pso.md
   ```
2. Completar objetivo, contexto, cambios solicitados, restricciones y criterios
   de aceptación. El estado inicial es "Pendiente".
3. Pedirle a Claude, de forma expresa, que la **revise**, la **discuta** o la
   **implemente**. Crear el archivo no dispara nada por sí solo.

## Estados

| Estado | Significado |
|---|---|
| Pendiente | Escrita por el usuario; nadie trabajó en ella todavía |
| En discusión | Claude dejó preguntas o un análisis de impacto al final del documento |
| En desarrollo | Se está implementando |
| Implementada | Implementada y verificada; el archivo pasa a `done/` |
| Descartada | El usuario decidió no hacerla; el archivo pasa a `done/` con el motivo |

## Qué hace Claude con una solicitud

- La usa como especificación de la tarea, junto con `docs/specification/`.
- No reescribe el texto del usuario ni borra sus comentarios: agrega sus notas
  en una sección propia al final.
- Si la solicitud contradice una especificación o una decisión registrada, lo
  explica antes de tomar decisiones de arquitectura.
- Al implementarla y verificarla: actualiza su estado, la mueve a `done/`,
  escribe un informe en `docs/reports/` y actualiza `PROJECT_STATUS.md`,
  `CHANGELOG.md` y la documentación técnica afectada.
