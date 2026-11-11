# Documentación del proyecto

El repositorio es la fuente de verdad del proyecto y el lugar donde el usuario
y Claude colaboran. Todo está en Markdown.

## ¿Qué busco?

| Pregunta | Documento |
|---|---|
| ¿Qué estamos construyendo? | [specification/PROJECT_SPEC.md](specification/PROJECT_SPEC.md) |
| ¿Cómo está organizado? | [architecture/OVERVIEW.md](architecture/OVERVIEW.md) |
| ¿Qué promete cada módulo? | [architecture/MODULE_CONTRACTS.md](architecture/MODULE_CONTRACTS.md) |
| ¿Por qué se decidió así? | [architecture/decisions/](architecture/decisions/) |
| ¿Qué funcionalidades existen hoy? | [status/PROJECT_STATUS.md](status/PROJECT_STATUS.md) |
| ¿Qué se implementó recientemente? | [CHANGELOG.md](CHANGELOG.md) y [reports/](reports/) |
| ¿Qué problemas conocemos? | [status/KNOWN_ISSUES.md](status/KNOWN_ISSUES.md) |
| ¿Qué sigue? | [status/ROADMAP.md](status/ROADMAP.md) y [status/BACKLOG.md](status/BACKLOG.md) |
| ¿Cómo uso la aplicación? | [GUIDE.md](GUIDE.md) |

## Especificación (la edita el usuario)

- [PROJECT_SPEC.md](specification/PROJECT_SPEC.md): objetivos, tecnologías y criterios de aceptación.
- [SIMULATOR.md](specification/SIMULATOR.md): mundo, vehículo, LiDAR, obstáculos, navegación.
- [MOBILE_AND_CONTROLLERS.md](specification/MOBILE_AND_CONTROLLERS.md): móvil, controladores, observaciones.
- [EVOLUTION.md](specification/EVOLUTION.md): estrategias de aprendizaje, GA, fitness, poblaciones, estadísticas.
- [MAPS_AND_EDITOR.md](specification/MAPS_AND_EDITOR.md): editor, formato de mapas, generador aleatorio.

## ¿Cómo cambio los requisitos?

Hay dos caminos, ambos sin tocar código:

1. **Editar una especificación** en `specification/`. La versión que quede en el
   archivo pasa a ser la referencia.
2. **Crear una solicitud**: copiar [requests/TEMPLATE.md](requests/TEMPLATE.md) a
   `requests/open/mi-cambio.md` y completarla.

Después hay que pedírselo a Claude de forma expresa ("revisa", "discute" o
"implementa la solicitud X"): escribir un documento no dispara su implementación.

Cuando una solicitud se implementa y verifica, Claude actualiza su estado, la
mueve a `requests/done/`, escribe un informe en `reports/` y actualiza
`PROJECT_STATUS.md`, `CHANGELOG.md` y la documentación técnica afectada. Claude
no reescribe las solicitudes ni borra comentarios del usuario; si lo implementado
difiere de lo especificado, la diferencia queda anotada en `PROJECT_STATUS.md`.
