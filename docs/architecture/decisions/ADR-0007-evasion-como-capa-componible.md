# ADR-0007: La evasión de obstáculos es una capa componible

Fecha: 2026-11-15

## Contexto

El usuario quiere elegir, además del algoritmo que aprende a navegar, un
algoritmo de evasión de obstáculos: la evasión aprendida que ya existía, FTG
(Follow the Gap) o APF (campos potenciales artificiales), y comparar
estadísticamente unas combinaciones con otras.

## Decisión

- La evasión es un `ObstacleAvoider`: recibe la observación y la acción que
  propone la navegación, y devuelve la acción corregida. No decide a dónde ir.
- `AvoidanceController(inner, avoider)` compone cualquier controlador con
  cualquier evasor. `bootstrap` envuelve la fábrica de controladores de la
  navegación cuando la evasión elegida no es la aprendida.
- La dirección propuesta se interpreta como intención ("quiero ir hacia allí"),
  no como orden de volante: es lo que FTG y APF necesitan como dirección deseada.
- Los evasores son plugins de `control/avoidance/`, descubiertos igual que los
  algoritmos de navegación.
- Se agrega una navegación de referencia sin aprendizaje (`reactive`), que solo
  apunta al objetivo: es la línea de base y permite medir FTG y APF por sí solos.

Variantes adoptadas de los métodos clásicos, para que sean utilizables aquí:

- FTG usa el centro angular del hueco (no la fórmula con las distancias a sus
  bordes) y mantiene el hueco elegido ante empates, para no oscilar.
- APF suma una componente tangencial (campo de vórtice): con el método puro, un
  obstáculo alineado con el destino cancela la atracción y el vehículo choca o
  se detiene.
- Ambos dejan de intervenir cuando el destino está a la vista y más cerca que
  cualquier obstáculo; si no, no podrían llegar a un destino con una pared detrás.

## Alternativas consideradas

- FTG y APF como controladores completos, alternativos a los aprendidos: no
  permite combinarlos con una navegación aprendida ni comparar "misma
  navegación, distinta evasión".
- Meter la evasión dentro de cada algoritmo de navegación: multiplicaría el
  código por cada combinación.
- Que el evasor usara siempre el rumbo al destino e ignorara a la navegación:
  la navegación aprendida no tendría ningún efecto.

## Consecuencias

- 4 navegaciones por 3 evasiones dan 12 combinaciones sin código adicional por
  combinación; agregar DWA o VFH es un archivo.
- Un modelo entrenado con una evasión aprende a proponer intenciones para esa
  evasión: no es intercambiable sin volver a entrenar.
- Con evasión aprendida la dirección es orden directa de volante; con FTG o APF
  es intención. La diferencia queda dentro de `control/avoidance/`.
- La referencia sin aprendizaje evalúa un solo controlador por iteración: sus
  estadísticas por generación tienen pocos episodios y deben leerse en el
  conjunto de validación o promediando generaciones.
