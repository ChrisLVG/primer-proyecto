# Tareas de desarrollo: 001 — Filtrar y listar citas

**Estado:** T1-T6 completadas. T7 (verificación) en curso.

## Resumen de dependencias

```text
T1 (schemas) ──┐
               ├──► T3 (listar_citas) ──► T7 (verificación HTTP)
T2 (helpers) ──┤
               ├──► T4 (crear_cita solapamiento) ──► T7
               └──► T5 (actualizar_cita solapamiento + estado) ──► T7
T6 (docs) ──────────────────────────────────────────────► (independiente)
```

---

## T1 — Actualizar esquemas Pydantic (`schemas.py`)

**Estado:** ✅ Completada (commit `f514bbe`)

**Dependencias:** Ninguna (primera tarea).

**Descripción detallada:**
Modificar `src/primer_proyecto/schemas.py` para añadir validación de `estado` y normalizar `origen` en `CitaCreate`. No se tocan los modelos ORM.

**Archivos a modificar:** `src/primer_proyecto/schemas.py`

**Cambios a realizar:**

1. Añadir import: `from typing import Literal`
2. En `CitaResponse`, cambiar `estado: str` por `estado: Literal["pendiente", "confirmada", "cancelada", "terminada"]`
3. En `CitaCreate`, cambiar `origen: Optional[str] | None = None` por `origen: str | None = None` (quitar la redundancia `Optional`)

**Validaciones de entrada/salida:**

- `CitaResponse.estado` solo acepta los 4 valores al serializar (si la BD tiene un valor inválido, Pydantic lanza error al serializar → 500, lo cual es deseable como señal de datos corruptos).

**Manejo de errores y casos borde:**

- Si la BD tiene un `estado` fuera de los 4 valores, la serialización falla con error 500. Esto es intencional: fuerza a que los datos estén limpios.

**Criterios de aceptación:**

- [ ] `from typing import Literal` importado sin errores
- [ ] `CitaResponse.estado` es `Literal["pendiente", "confirmada", "cancelada", "terminada"]`
- [ ] `CitaCreate.origen` es `str | None`
- [ ] El módulo importa sin errores: `uv run --frozen python -c "from primer_proyecto import schemas; print('OK')"`
- **RF cubiertos:** RF-3 (parcial: tipado en respuesta)

---

## T2 — Funciones auxiliares de solapamiento (`main.py`)

**Estado:** ✅ Completada (commit `77c944b`) — 17/17 pruebas

**Dependencias:** T1 (usa `schemas.CitaResponse` indirectamente, pero principalmente necesita `models` y `selectinload` que ya existen).

**Descripción detallada:**
Añadir dos funciones auxiliares en `src/primer_proyecto/main.py`: `_calcular_duracion_total` y `_hay_solapamiento`. Estas funciones encapsulan la lógica de detección de solapamiento por intervalos.

**Archivos a modificar:** `src/primer_proyecto/main.py`

**Cambios a realizar:**

1. Añadir import: `from datetime import timedelta` (junto al import existente de `datetime`)
2. Añadir `_calcular_duracion_total(servicios)`:
   - Suma `duracion_minutos` de todos los servicios de la lista
   - Devuelve `int`
3. Añadir `_hay_solapamiento(db, inicio, duracion_minutos, excluir_id=None)`:
   - Calcula `fin = inicio + timedelta(minutes=duracion_minutos)`
   - Consulta todas las citas con `estado IN ('pendiente', 'confirmada')` usando `selectinload(models.Cita.servicios)`
   - Para cada cita (excluyendo `excluir_id` si se proporciona):
     - Calcula `inicio_existente = cita.fecha_hora`
     - Calcula `fin_existente = inicio_existente + timedelta(minutes=_calcular_duracion_total(cita.servicios))`
     - Si `inicio < fin_existente AND inicio_existente < fin` → devuelve `True`
   - Devuelve `False` si no hay solapamiento

**Validaciones de entrada/salida:**

- `inicio` debe ser naive (sin tzinfo). Si viene aware, normalizar antes de llamar.
- `duracion_minutos` debe ser > 0 (los servicios tienen duración positiva por validación del schema).
- `excluir_id` es opcional; si se proporciona, se excluye esa cita de la comprobación (necesario para PATCH).

**Manejo de errores y casos borde:**

- Si `servicios` está vacío, `_calcular_duracion_total` devuelve 0 → `_hay_solapamiento` con duración 0: `fin == inicio`, el intervalo es vacío, no se solapa con nada (correcto).
- Si la BD no tiene citas activas, devuelve `False` (no hay solapamiento).
- Citas `cancelada` y `terminada` se filtran en la query (no bloquean).

**Criterios de aceptación:**

- [ ] `_calcular_duracion_total([servicio_30min, servicio_20min])` devuelve `50`
- [ ] `_calcular_duracion_total([])` devuelve `0`
- [ ] `_hay_solapamiento` devuelve `True` cuando dos intervalos se solapan
- [ ] `_hay_solapamiento` devuelve `False` cuando los intervalos no se tocan
- [ ] `_hay_solapamiento` con `excluir_id` ignora la cita con ese ID
- [ ] `_hay_solapamiento` ignora citas con estado `cancelada` o `terminada`
- **RF cubiertos:** RF-4 (parcial: helpers de solapamiento)

---

## T3 — Ampliar `listar_citas` con filtros, orden y paginación (`main.py`)

**Estado:** ✅ Completada (commit `a7157bc`) — 27/27 pruebas

**Dependencias:** T1 (usa `schemas.CitaResponse` como response_model, ya presente).

**Descripción detallada:**
Modificar el endpoint `GET /citas/` para aceptar los nuevos query params: `fecha_desde`, `fecha_hasta`, `estado`, `usuario_id`, `limit`, `offset`. Combinarlos con AND, ordenar por `fecha_hora ASC, id ASC`, y aplicar paginación.

**Archivos a modificar:** `src/primer_proyecto/main.py`

**Cambios a realizar:**

1. Añadir parámetros a `listar_citas`:

   ```python
   fecha_desde: datetime | date | None = Query(None)
   fecha_hasta: datetime | date | None = Query(None)
   estado: str | None = Query(None)
   usuario_id: str | None = Query(None)
   limit: int = Query(100, ge=1, le=500)
   offset: int = Query(0, ge=0)
   ```

   (el parámetro `origen` ya existe)

2. Validar `origen` (ya existente): si no es None y no está en ("usuario", "barbero") → 400.

3. Validar `estado`: si no es None y no está en ("pendiente", "confirmada", "cancelada", "terminada") → 400 con mensaje "El estado debe ser uno de: pendiente, confirmada, cancelada, terminada."

4. Validar `usuario_id`: si no es None, verificar que el usuario existe en BD. Si no existe → 400 "El usuario no está registrado."

5. Procesar fechas:
   - Si `fecha_desde` es `date` (sin hora) → convertir a `datetime.combine(fecha, time.min)` (00:00:00)
   - Si `fecha_desde` es `datetime` con tzinfo → normalizar a naive: `.astimezone().replace(tzinfo=None)`
   - Igual para `fecha_hasta` pero con `time.max` (23:59:59) si es `date`
   - Si ambas presentes y `fecha_desde > fecha_hasta` → 400 "El rango de fechas es inválido: la fecha inicial no puede ser posterior a la final."

6. Construir consulta:

   ```python
   consulta = db.query(models.Cita).options(selectinload(models.Cita.servicios))
   if origen is not None: consulta = consulta.filter(models.Cita.origen == origen)
   if estado is not None: consulta = consulta.filter(models.Cita.estado == estado)
   if usuario_id is not None: consulta = consulta.filter(models.Cita.usuario_id == usuario_id)
   if fecha_desde is not None: consulta = consulta.filter(models.Cita.fecha_hora >= fecha_desde_naive)
   if fecha_hasta is not None: consulta = consulta.filter(models.Cita.fecha_hora <= fecha_hasta_naive)
   consulta = consulta.order_by(models.Cita.fecha_hora.asc(), models.Cita.id.asc())
   consulta = consulta.offset(offset).limit(limit)
   return consulta.all()
   ```

7. Mantener `response_model=list[schemas.CitaResponse]` (ya presente).

**Validaciones de entrada/salida:**

- `limit` fuera de [1, 500] → 422 (Pydantic/Query lo valida automáticamente)
- `offset` < 0 → 422
- `estado` inválido → 400
- `origen` inválido → 400
- `usuario_id` inexistente → 400
- Rango de fechas invertido → 400
- Fecha mal formada → 422 (Pydantic)
- Fecha con tz → se normaliza a naive (no error)

**Manejo de errores y casos borde:**

- Sin filtros → devuelve todas las citas (comportamiento actual)
- Filtro sin resultados → `200` con `[]`
- `usuario_id` válido sin citas → `200` con `[]`
- Combinación de varios filtros → intersección (AND)
- Paginación con empates → tiebreaker por `id` evita duplicados/saltos

**Criterios de aceptación:**

- [ ] `GET /citas/` sin params devuelve todas las citas ordenadas por fecha ascendente
- [ ] `GET /citas/?fecha_desde=2026-12-01` devuelve solo las del 1 de diciembre (día completo)
- [ ] `GET /citas/?fecha_desde=2026-12-01&fecha_hasta=2026-12-15` devuelve el rango
- [ ] `GET /citas/?estado=pendiente` devuelve solo pendientes
- [ ] `GET /citas/?usuario_id=<id>` devuelve solo las de ese usuario
- [ ] `GET /citas/?usuario_id=<id_valido_sin_citas>` devuelve `200` con `[]`
- [ ] Combinación de varios filtros devuelve la intersección
- [ ] `GET /citas/?origen=barbero` sigue funcionando (regresión)
- [ ] `GET /citas/?estado=xyz` devuelve `400`
- [ ] `GET /citas/?fecha_desde=2026-12-15&fecha_hasta=2026-12-01` devuelve `400`
- [ ] `GET /citas/?fecha_desde=2026-12-01&fecha_hasta=2026-12-01` devuelve las citas de ese día
- [ ] `GET /citas/?limit=0` devuelve `422`
- [ ] `GET /citas/?offset=-1` devuelve `422`
- [ ] Al filtrar por un solo día con varias citas, ordenadas por hora ascendente
- [ ] Paginación con `limit`/`offset` devuelve resultados consistentes
- **RF cubiertos:** RF-1, RF-2, RF-3

---

## T4 — Validación de solapamiento en `crear_cita` (`main.py`)

**Estado:** ✅ Completada (commit `1f1452f`) — 14/14 pruebas

**Dependencias:** T2 (usa `_calcular_duracion_total` y `_hay_solapamiento`).

**Descripción detallada:**
Añadir la validación de solapamiento en el endpoint `POST /citas/`. Después de validar usuario, servicios y duplicados, calcular la duración total de la nueva cita y verificar que no se solapa con ninguna cita activa existente.

**Archivos a modificar:** `src/primer_proyecto/main.py`

**Cambios a realizar:**

1. Después de `_obtener_servicios(db, cita.servicios_ids)` y la verificación de duplicados, añadir:

    ```python
   duracion_total = _calcular_duracion_total(servicios)
   fecha_hora = cita.fecha_hora
   if fecha_hora.tzinfo is not None:
       fecha_hora = fecha_hora.astimezone().replace(tzinfo=None)
   if _hay_solapamiento(db, fecha_hora, duracion_total):
       raise HTTPException(status_code=400, detail="La cita se solapa con otra cita existente.")
    ```

2. Usar `fecha_hora` normalizada al crear la `Cita` (en vez de `cita.fecha_hora` directamente).

**Validaciones de entrada/salida:**

- Si la nueva cita se solapa con alguna cita activa existente → 400.
- Citas canceladas/terminadas no bloquean.
- Toque exacto (fin de A = inicio de B) no se considera solapamiento.

**Manejo de errores y casos borde:**

- Cita con un solo servicio: duración = duración de ese servicio.
- Cita con varios servicios: duración = suma.
- Cita cancelada en el hueco: no bloquea la creación.
- Cita terminada en el pasado: no bloquea.

**Criterios de aceptación:**

- [ ] `POST /citas/` con solapamiento devuelve `400`
- [ ] `POST /citas/` sin solapamiento se crea correctamente
- [ ] Una cita cancelada no bloquea la creación de otra en el mismo hueco
- [ ] Una cita terminada no bloquea la creación de otra en el mismo hueco
- [ ] Toque exacto (fin A = inicio B) permite crear la cita B
- **RF cubiertos:** RF-4

---

## T5 — Validación de solapamiento y `estado` en `actualizar_cita` (`main.py`)

**Estado:** ✅ Completada (commit `245a533`) — 19/19 pruebas

**Dependencias:** T2 (usa `_calcular_duracion_total` y `_hay_solapamiento`), T4 (patrón de normalización de fecha).

**Descripción detallada:**
Modificar `PATCH /citas/{cita_id}` para:

1. Validar `estado` si se envía (4 valores → 400 si inválido).
2. Validar solapamiento si se envía `fecha_hora` o `servicios_ids`.
3. Normalizar fecha a naive si tiene tzinfo.

**Archivos a modificar:** `src/primer_proyecto/main.py`

**Cambios a realizar:**

1. Validar `estado`:

```python
if cita.estado is not None:
    if cita.estado not in ("pendiente", "confirmada", "cancelada", "terminada"):
        raise HTTPException(status_code=400, detail="El estado debe ser uno de: pendiente, confirmada, cancelada, terminada.")
```

2. Reestructurar la validación de fecha y servicios para calcular la combinación final:

```python
# Determinar fecha final
fecha_final = existing_cita.fecha_hora
if cita.fecha_hora is not None:
    fecha_hora = cita.fecha_hora
    if fecha_hora.tzinfo is not None:
        fecha_hora = fecha_hora.astimezone().replace(tzinfo=None)
    # validaciones existentes (ocupada por otra cita, por mismo usuario, anterior a ahora)
    ...
    fecha_final = fecha_hora

# Determinar servicios finales
servicios_finales = existing_cita.servicios
if cita.servicios_ids is not None:
    servicios = _obtener_servicios(db, cita.servicios_ids)
    servicios_finales = servicios
    existing_cita.servicios = servicios
    existing_cita.precio_total = _calcular_precio_total(servicios)

# Validar solapamiento si cambió fecha o servicios
if cita.fecha_hora is not None or cita.servicios_ids is not None:
    duracion_total = _calcular_duracion_total(servicios_finales)
    if _hay_solapamiento(db, fecha_final, duracion_total, excluir_id=cita_id):
        raise HTTPException(status_code=400, detail="La cita se solapa con otra cita existente.")
```

3. Mantener las validaciones existentes de fecha (ocupada por otra cita, por mismo usuario, anterior a ahora).

4. Asignar `existing_cita.fecha_hora = fecha_final` si cambió.

5. Asignar `existing_cita.estado = cita.estado` si se envió.

**Validaciones de entrada/salida:**

- `estado` inválido → 400
- Solapamiento → 400
- Fecha pasada → 400 (validación existente)
- Fecha ocupada por otra cita → 400 (validación existente)

**Manejo de errores y casos borde:**

- Si solo se envía `estado` (sin fecha ni servicios) → no se valida solapamiento
- Si se envía fecha y servicios simultáneamente → validar con la combinación final
- Toque exacto no se considera solapamiento
- Citas canceladas/terminadas no bloquean

**Criterios de aceptación:**

- [ ] `PATCH /citas/{id}` con cambio de fecha valida solapamiento
- [ ] `PATCH /citas/{id}` con cambio de servicios valida solapamiento
- [ ] `PATCH /citas/{id}` con cambio de fecha y servicios valida solapamiento con la combinación final
- [ ] `PATCH /citas/{id}` con solo cambio de estado no valida solapamiento
- [ ] `PATCH /citas/{id}` con `estado` inválido devuelve `400`
- [ ] `PATCH /citas/{id}` que se solapa con otra cita devuelve `400`
- [ ] `PATCH /citas/{id}` que no se solapa se actualiza correctamente
- **RF cubiertos:** RF-3, RF-4, RF-5

---

## T6 — Actualizar documentación (`AGENTS.md` y `memory.md`)

**Estado:** ✅ Completada

**Dependencias:** T3, T4, T5 (se ejecuta después de la implementación).

**Descripción detallada:**
Actualizar `AGENTS.md` y `memory.md` para reflejar los cambios en el contrato de la API y las nuevas validaciones.

**Archivos a modificar:** `AGENTS.md`, `memory.md`

**Cambios a realizar en `AGENTS.md`:**

1. Actualizar la sección de rutas: `GET /citas/` ahora acepta query params `fecha_desde`, `fecha_hasta`, `estado`, `usuario_id`, `origen`, `limit`, `offset`.
2. Añadir sección de solapamiento de horarios: validación por intervalos, citas canceladas/terminadas no bloquean, toque exacto no es solapamiento.
3. Actualizar la sección de bugs vivos: el bug `email`/`correo` ya está corregido. Añadir la aceptación de riesgo (precio retroactivo, solapamiento no retroactivo).
4. Actualizar `memory.md` con las decisiones de esta spec.

**Cambios a realizar en `memory.md`:**

- Añadir en "Decisiones de arquitectura": solapamiento por intervalos, filtros combinables, paginación.
- Añadir en "Próximos pasos": (ninguno nuevo, todos los RF cubiertos).
- Respetar máximo 50 líneas.

**Criterios de aceptación:**

- [ ] `AGENTS.md` documenta el nuevo contrato de `GET /citas/`
- [ ] `AGENTS.md` documenta la validación de solapamiento
- [ ] `memory.md` tiene ≤ 50 líneas
- **RF cubiertos:** Todos (documentación)

---

## T7 — Verificación por HTTP real

**Dependencias:** T1, T2, T3, T4, T5 (se ejecuta después de toda la implementación).

**Descripción detallada:**
Levantar uvicorn y ejecutar una suite de pruebas HTTP que verifique todos los criterios de aceptación de la spec (sección 5). Se usa `urllib` (no `TestClient`, que no funciona).

**Archivos a modificar:** Ninguno (solo verificación).

**Pasos:**

1. Eliminar la base de datos de prueba (si existe).
2. Levantar uvicorn en un puerto libre (ej. 8200).
3. Crear datos de prueba: al menos 2 usuarios, 3 servicios, 4 citas (con y sin solapamiento).
4. Ejecutar los 19 criterios de aceptación de la spec.
5. Detener uvicorn.
6. Eliminar la base de datos de prueba.

**Criterios de aceptación:**

- [ ] Todos los 19 criterios de aceptación de la spec se cumplen (sección 5).
- [ ] No hay errores 500 en ninguna petición.
- [ ] El solapamiento se detecta correctamente.
- [ ] Los filtros combinados funcionan.
- [ ] La paginación devuelve resultados consistentes.
- **RF cubiertos:** Todos

---

## Diagrama de dependencias

```text
T1 (schemas) ──┐
               ├──► T3 (listar_citas) ──► T7 (verificación HTTP)
T2 (helpers) ──┤
               ├──► T4 (crear_cita solapamiento) ──► T7
               └──► T5 (actualizar_cita solapamiento + estado) ──► T7
T6 (docs) ──────────────────────────────────────────────► (independiente)
```

## Notas

- **No se crean archivos nuevos** (respeta la regla de AGENTS.md sobre creación de archivos).
- **No se modifican `models.py` ni `database.py`** (decisión #2 de la spec).
- **No se añaden dependencias** (constitución VII: simplicidad).
- Cada tarea es **atómica y secuencial**: se puede implementar y verificar de forma independiente.
- Las tareas T3, T4, T5 dependen de T1 y T2 pero son independientes entre sí.
