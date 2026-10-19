# Especificación: 001 — Filtrar y listar citas

**Versión:** 1.1.0 (final)
**Estado:** Aprobada

## 1. Objetivo y contexto

Permitir al barbero y a los usuarios filtrar las citas por fecha, estado y usuario, combinando
varios filtros a la vez, y ordenarlas por fecha ascendente. Amplía el endpoint existente
`GET /citas/` sin romper su contrato actual (sin filtros devuelve todas las citas).

Además resuelve, en el mismo cambio, el problema de **solapamiento de horarios** detectado en la
constitución (principio I.13): dos citas no pueden ocupar el mismo espacio de tiempo, aunque
tengan servicios distintos.

### Contexto

- Ya existe el filtro por `origen` (`usuario` | `barbero`).
- Las citas pueden tener varios servicios (tabla intermedia `cita_servicio`).
- No hay autenticación todavía; el filtro por usuario se hace por `usuario_id` pasado por query param.
- El frontend no existe; esta spec cubre únicamente la API.

## 2. Requisitos funcionales

### RF-1 — Filtros combinables (AND)

`GET /citas/` acepta los siguientes query params, todos opcionales y combinables:

| Param | Tipo | Descripción |
| --- | --- | --- |
| `fecha_desde` | `datetime \| date` | Inicio del rango (inclusive). Si se envía solo este, filtra ese día completo. |
| `fecha_hasta` | `datetime \| date` | Fin del rango (inclusive). Si se envía solo este, filtra ese día completo. |
| `estado` | string | Uno de: `pendiente`, `confirmada`, `cancelada`, `terminada`. |
| `usuario_id` | string | Filtra por usuario. |
| `origen` | string | Ya existente: `usuario` o `barbero`. |
| `limit` | int | Máximo de resultados (default 100, máximo 500). |
| `offset` | int | Desplazamiento para paginación (default 0, mínimo 0). |

- Si no se envía ningún filtro, se devuelven todas las citas.
- Los filtros se combinan con AND.
- **Orden:** ascendente por `fecha_hora`, con tiebreaker por `id` ascendente para garantizar
  orden estable al paginar. Cuando el filtro cubre un solo día, esto equivale a ordenar por hora
  de inicio, de la más temprana a la más tardía. No se ordena por duración ni por usuario.

### RF-2 — Filtrar por día completo

Si se envía `fecha_desde` o `fecha_hasta` como fecha sin hora (`YYYY-MM-DD`), se interpreta como
el día completo: desde `00:00:00` hasta `23:59:59`. Si se envía con hora, se usa el instante exacto.

Si se envía una fecha con zona horaria (ej. `2026-12-01T10:00:00Z`), se normaliza a naive
(consistente con el almacenamiento en BD y con `actualizar_cita`).

Si `fecha_desde` == `fecha_hasta` (mismo día), se filtra ese día completo.

### RF-3 — Validación de `estado`

`estado` solo acepta los 4 valores: `pendiente`, `confirmada`, `cancelada`, `terminada`.
Cualquier otro valor devuelve `400` con el mensaje
"El estado debe ser uno de: pendiente, confirmada, cancelada, terminada."

La validación se hace manualmente en el endpoint (no con `Literal` de Pydantic, que daría `422`).
El tipo en `CitaResponse.estado` se tipa como `Literal` para consistencia en la serialización.

`CitaCreate` no incluye campo `estado`: siempre se crea como `pendiente`.

### RF-4 — Solapamiento de horarios

Al crear (`POST /citas/`) o modificar (`PATCH /citas/{id}`) una cita, el servidor valida que su
intervalo `[inicio, inicio + suma de duraciones)` no se solape con el de ninguna otra cita activa.

- Dos citas se solapan si `(inicio_nuevo < fin_existente) Y (inicio_existente < fin_nuevo)`.
- **Cita activa** = `estado IN ('pendiente', 'confirmada')`. Las citas `cancelada` y `terminada`
  no bloquean (liberan el hueco).
- Al actualizar una cita, se excluye la propia cita de la comprobación (`id != cita_id`).
- La validación se ejecuta **solo si** se envía `fecha_hora` o `servicios_ids` en el body.
  Si solo se cambia `estado`, no se valida solapamiento.
- Si se solapa, se devuelve `400` con el mensaje "La cita se solapa con otra cita existente."

La duración total se calcula sumando `duracion_minutos` de todos los servicios de la cita
(no se almacena; se computa en memoria).

### RF-5 — Recálculo de precio y duración

- `precio_total` se recalcula en cada escritura (ya implementado).
- La duración total se calcula en memoria para la validación de solapamiento.
- Al cambiar servicios en `PATCH`, se recalcula `precio_total` y se revalida el solapamiento
  con la nueva duración.

## 3. Restricciones y lo que no incluye

- **No incluye autenticación.** El filtro por `usuario_id` es "honor system": el cliente envía su
  propio ID. La restricción "el usuario solo ve sus citas" se aplicará cuando exista auth.
- **No incluye frontend.** Solo API.
- **No incluye solapamiento retroactivo** al cambiar la duración de un servicio: las citas ya
  creadas conservan su validez; solo las nuevas/actualizadas usan la nueva duración. Esta es una
  **aceptación de riesgo** documentada: el precio se recalcula (valor derivado que debe reflejar
  el estado actual), pero el solapamiento es una restricción de creación, no un valor derivado.
  Nota: al validar solapamiento de una nueva cita, la duración de las citas existentes se calcula
  con las duraciones actuales de sus servicios (que pueden haber cambiado).
- **No incluye paginación por cursor** ni ordenamiento distinto a ascendente por fecha.
- **No se modifica el modelo de datos** para añadir un campo de duración total a `Cita` (se
  calcula en memoria). Esta decisión evita una regeneración de la base.
- **No se añade un endpoint nuevo**: se amplía `GET /citas/`.

## 4. Casos borde y manejo de errores

| Caso | Comportamiento |
| --- | --- |
| Sin filtros | `200` con todas las citas, ordenadas por fecha ascendente. |
| Filtro sin resultados | `200` con lista vacía `[]`. El aviso es responsabilidad del frontend; el texto depende de los filtros aplicados. |
| `estado` inválido | `400` "El estado debe ser uno de: pendiente, confirmada, cancelada, terminada." |
| `origen` inválido | `400` "El origen debe ser 'usuario' o 'barbero'." |
| `fecha_desde` > `fecha_hasta` | `400` "El rango de fechas es inválido: la fecha inicial no puede ser posterior a la final." |
| Fecha mal formada | `422` (validación automática de Pydantic). |
| Fecha con zona horaria | Se normaliza a naive (no error). |
| `usuario_id` inexistente | `400` "El usuario no está registrado." |
| `usuario_id` válido sin citas | `200` con lista vacía `[]`. |
| Solapamiento al crear/actualizar | `400` "La cita se solapa con otra cita existente." |
| Cita cancelada en el rango | Se incluye en los resultados (el filtro no la excluye). |
| `limit` fuera de [1, 500] | `422`. |
| `offset` < 0 | `422`. |
| `limit`/`offset` no numéricos | `422`. |

## 5. Criterios de aceptación y verificación

Se verifica levantando uvicorn y consultando los endpoints (constitución VI).

1. `GET /citas/` sin params devuelve todas las citas ordenadas por fecha ascendente.
2. `GET /citas/?fecha_desde=2026-12-01` devuelve solo las del 1 de diciembre (día completo).
3. `GET /citas/?fecha_desde=2026-12-01&fecha_hasta=2026-12-15` devuelve el rango.
4. `GET /citas/?estado=pendiente` devuelve solo pendientes.
5. `GET /citas/?usuario_id=<id>` devuelve solo las de ese usuario.
6. `GET /citas/?usuario_id=<id_valido_sin_citas>` devuelve `200` con `[]`.
7. Combinación de varios filtros devuelve la intersección.
8. `GET /citas/?origen=barbero` sigue funcionando (regresión).
9. `GET /citas/?estado=xyz` devuelve `400`.
10. `GET /citas/?fecha_desde=2026-12-15&fecha_hasta=2026-12-01` devuelve `400`.
11. `GET /citas/?fecha_desde=2026-12-01&fecha_hasta=2026-12-01` devuelve las citas de ese día.
12. `POST /citas/` con solapamiento devuelve `400`.
13. `POST /citas/` sin solapamiento se crea correctamente.
14. Una cita cancelada no bloquea la creación de otra en el mismo hueco.
15. `PATCH /citas/{id}` con cambio de fecha o servicios valida solapamiento.
16. `PATCH /citas/{id}` con solo cambio de estado no valida solapamiento.
17. Todos los endpoints declaran `response_model` y usan `HTTPException` con códigos correctos.
18. Al filtrar por un solo día con varias citas, las citas se devuelven ordenadas por hora de
    inicio ascendente (la de las 09:00 antes que la de las 11:30).
19. Paginación con `limit`/`offset` devuelve resultados consistentes (sin duplicados ni saltos).

## 6. Cambios de código previstos

| Archivo | Cambio |
| --- | --- |
| `schemas.py` | Añadir `Literal` para `estado` en `CitaResponse` (4 valores). |
| `main.py` | Ampliar `listar_citas` con los nuevos filtros (`Query` en main.py), orden ascendente con tiebreaker, paginación. Añadir validación de solapamiento en `crear_cita` y `actualizar_cita`. Añadir `response_model=list[CitaResponse]` a `listar_citas`. |
| `models.py` | **Sin cambios estructurales.** (Añadir `CHECK` constraint para `estado` es opcional y requiere aprobación.) |
| `AGENTS.md` | Documentar el nuevo contrato y la validación de intervalos. |
| `memory.md` | Registrar la decisión. |

## 7. Decisiones aprobadas (opciones recomendadas)

1. **Mensaje en respuesta vacía:** la API devuelve solo `[]`. El aviso "no existen citas registradas para esa fecha" es responsabilidad del frontend.
2. **`CHECK` constraint en `estado`:** validar solo en Pydantic (sin tocar `models.py`). No se añade constraint en BD.
3. **Paginación:** `limit`/`offset` con defaults (`limit=100`, `offset=0`), `limit` máximo 500.

## 8. Preguntas resueltas durante la revisión QA

- **`terminada`**: se marca manualmente vía `PATCH /citas/{id}` con `{"estado": "terminada"}`. No hay automatización por fecha.
- **`origen` inválido**: mensaje exacto "El origen debe ser 'usuario' o 'barbero'."
- **Decisión de implementación:** usar `Query` en `main.py` (no schema nuevo de query params).
- **Aceptación de riesgo:** el precio se recalcula retroactivamente al cambiar un servicio, pero el
  solapamiento no se revalida retroactivamente. Documentado en AGENTS.md.
  