# Plan: 001 — Filtrar y listar citas

## 1. Cambios de código previstos

### Archivos modificados

| Archivo | Responsabilidad | Cambio |
| --- | --- | --- |
| `src/primer_proyecto/schemas.py` | Validación Pydantic | `Literal` para `estado` en `CitaResponse`. Normalizar `CitaCreate.origen` (quitar `Optional[str] \| None` redundante). |
| `src/primer_proyecto/main.py` | Rutas y lógica de negocio | Ampliar `listar_citas` (filtros, orden, paginación). Añadir `_calcular_duracion_total` y `_hay_solapamiento`. Validar `estado` en `crear_cita`/`actualizar_cita`. Validar solapamiento en create/update. |
| `AGENTS.md` | Reglas del repo | Documentar nuevo contrato, validación de intervalos, aceptación de riesgo. |
| `memory.md` | Bitácora | Registrar decisión. |

### Archivos NO modificados (decisión explícita)

- `models.py`: sin cambios estructurales (decisión #2 de la spec: solo validación Pydantic).
- `database.py`: sin cambios.

### Dependencias

Ninguna nueva. Se usan `datetime`, `typing.Literal` (stdlib) y `Query` (ya importado en main.py).

### Estructura de archivos

Sin archivos nuevos. Todo el cambio es incremental sobre `main.py` y `schemas.py`.

## 2. Lógica de negocio, funciones, interfaces y validaciones

### Funciones auxiliares nuevas en `main.py`

```python
def _calcular_duracion_total(servicios: list[models.Servicio]) -> int:
    """Suma duracion_minutos de todos los servicios de una cita."""
    return sum(s.duracion_minutos for s in servicios)

def _hay_solapamiento(
    db: Session,
    inicio: datetime,
    duracion_minutos: int,
    excluir_id: str | None = None,
) -> bool:
    """Devuelve True si existe una cita activa cuyo intervalo se solapa."""
    fin = inicio + timedelta(minutes=duracion_minutos)
    candidatas = db.query(models.Cita).options(
        selectinload(models.Cita.servicios)
    ).filter(models.Cita.estado.in_(("pendiente", "confirmada"))).all()
    for cita in candidatas:
        if excluir_id is not None and cita.id == excluir_id:
            continue
        inicio_existente = cita.fecha_hora
        fin_existente = inicio_existente + timedelta(
            minutes=_calcular_duracion_total(cita.servicios)
        )
        if inicio < fin_existente and inicio_existente < fin:
            return True
    return False
```

### Validaciones a implementar

**En `listar_citas` (RF-1, RF-2, RF-3):**

1. `origen` ya validado (existente).
2. `estado` → si no es None y no está en {pendiente, confirmada, cancelada, terminada} → 400.
3. `usuario_id` → si no es None y no existe en BD → 400 "El usuario no está registrado."
4. `fecha_desde`/`fecha_hasta`:
   - Si es `date` (sin hora) → expandir a 00:00:00 / 23:59:59 del día.
   - Si es `datetime` con tzinfo → normalizar a naive.
   - Si `fecha_desde > fecha_hasta` → 400.
5. `limit` ∈ [1, 500], `offset` ≥ 0 → 422 si fuera de rango (Pydantic/Query).
6. Filtros combinados con AND.
7. Orden: `fecha_hora ASC, id ASC` (tiebreaker).
8. Aplicar `limit`/`offset` al final.

**En `crear_cita` (RF-4):**

1. Validaciones existentes (usuario, servicios, duplicado, origen, precio).
2. Calcular duración total de la nueva cita.
3. Llamar `_hay_solapamiento(db, fecha_hora, duracion_total)`. Si True → 400 "La cita se solapa con otra cita existente."

**En `actualizar_cita` (RF-4, RF-3):**

1. Validar `estado` si viene (4 valores) → 400.
2. Si viene `servicios_ids` o `fecha_hora`:
   - Determinar fecha final (existente o nueva, normalizada a naive).
   - Determinar servicios finales (existentes o nuevos).
   - Calcular duración total.
   - Llamar `_hay_solapamiento(db, fecha_final, duracion, excluir_id=cita_id)`. Si True → 400.
3. Si solo cambia `estado` → no validar solapamiento.

**En `actualizar_servicio` (RF-5 + solapamiento):**

- Ya recalcula `precio_total`. No se revalida solapamiento retroactivamente (decisión aprobada).

### Interfaces (firmas)

```python
# main.py
def listar_citas(
    fecha_desde: datetime | date | None = Query(None),
    fecha_hasta: datetime | date | None = Query(None),
    estado: str | None = Query(None),
    usuario_id: str | None = Query(None),
    origen: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> list[schemas.CitaResponse]: ...

# schemas.py
class CitaUpdate(BaseModel):
    servicios_ids: list[str] | None = Field(None, min_length=1)
    fecha_hora: datetime | None = None
    estado: str | None = None  # validado manualmente en endpoint

class CitaResponse(BaseModel):
    ...
    estado: Literal["pendiente", "confirmada", "cancelada", "terminada"]
    ...
```

### Validaciones a implementar (resumen por RF)

| RF | Dónde | Validación |
| --- | --- | --- |
| RF-1 | `listar_citas` | Filtros opcionales combinados con AND. |
| RF-2 | `listar_citas` | Expansión de fecha a día completo. |
| RF-3 | `listar_citas`, `crear_cita`, `actualizar_cita` | `estado` ∈ 4 valores → 400. |
| RF-4 | `crear_cita`, `actualizar_cita` | Solapamiento por intervalos. |
| RF-5 | `crear_cita`, `actualizar_cita`, `actualizar_servicio` | Recálculo de precio_total. |

## 3. Casos límite a considerar

1. **Cita con un solo servicio**: duración = duración de ese servicio. Solapamiento se calcula correctamente.
2. **Cita con varios servicios**: duración = suma. El intervalo puede ser largo.
3. **Toque exacto** (fin de A = inicio de B): NO se solapan (intervalo abierto por la derecha).
4. **Cita cancelada en el hueco**: no bloquea la creación de otra cita.
5. **Cita terminada en el pasado**: no bloquea (no es "activa").
6. **Mismo día con varias citas**: orden por hora ascendente.
7. **Paginación con empates**: tiebreaker por `id` evita duplicados/saltos.
8. **PATCH con fecha y servicios simultáneos**: validar con la combinación final.
9. **PATCH con fecha pasada**: rechazar con 400 (validación existente).
10. **Servicio inexistente en servicios_ids**: 400 con lista de faltantes.
11. **IDs duplicados en servicios_ids**: 400.
12. **`limit=0` o `limit=999999`**: 422.
13. **`offset` negativo**: 422.
14. **`fecha_desde` > `fecha_hasta`**: 400.
15. **Fecha con tz**: normalizar a naive.
16. **`usuario_id` válido sin citas**: 200 con `[]`.
17. **`estado` inválido en filtro**: 400.
18. **`origen` inválido en filtro**: 400.

## 4. Posibles riesgos de implementación

| Riesgo | Mitigación |
| --- | --- |
| N+1 al cargar servicios en `_hay_solapamiento` | Usar `selectinload(models.Cita.servicios)`. |
| Comparación de datetimes naive vs aware | Normalizar todo a naive antes de comparar. |
| `cita.servicios` lazy loading fuera de sesión | Usar `selectinload` en la query de candidatas. |
| `db.rollback()` olvidado en excepción | Envolver en try/except con rollback. |
| `estado` en `CitaUpdate` acepta cualquier string | Validar manualmente en endpoint → 400. |
| `CitaResponse.estado` como `Literal` pero BD tiene string libre | Pydantic validará al serializar; si hay valor inválido en BD, 500. Mitigación: validar en escritura. |
| `limit` default 100 oculta citas | Documentado; frontend debe paginar. |

## 5. Decisiones técnicas justificadas

1. **Ampliar `GET /citas/` en vez de crear endpoint nuevo**: ya tiene `origen` filter; sin filtros devuelve todo (backward compatible). Evita proliferación de rutas (constitución IV).
2. **No almacenar duración total en BD**: se calcula en memoria. Evita regeneración de base (decisión #2 de la spec).
3. **`Query` en main.py en vez de schema nuevo**: más simple, FastAPI valida automáticamente `limit`/`offset`.
4. **Validación manual de `estado` (400) en vez de `Literal` (422)**: consistente con `origen` que ya usa 400.
5. **`Literal` en `CitaResponse.estado`**: consistencia en serialización sin tocar models.
6. **No revalidar solapamiento retroactivamente al cambiar duración de servicio**: aceptación de riesgo documentada. El precio sí se recalcula (valor derivado).
7. **Intervalo abierto por la derecha `[inicio, fin)`**: una cita que termina a las 10:30 no bloquea otra que empiece a las 10:30.
8. **Citas canceladas/terminadas no bloquean**: liberan el hueco (tiene sentido de negocio).
9. **Tiebreaker por `id`**: garantiza orden estable al paginar.
10. **No añadir `CHECK` constraint en BD**: sin regeneración de base (decisión #2).

## 6. Cobertura de RF

| RF | Parte del plan que lo cubre |
| --- | --- |
| RF-1 (filtros combinables) | Sección 2, `listar_citas` |
| RF-2 (día completo) | Sección 2, `listar_citas` (expansión de fecha) |
| RF-3 (validación estado) | Sección 2, `listar_citas`, `crear_cita`, `actualizar_cita` |
| RF-4 (solapamiento) | Sección 2, `_hay_solapamiento`, `crear_cita`, `actualizar_cita` |
| RF-5 (recálculo) | Sección 2, `crear_cita`, `actualizar_cita`, `actualizar_servicio` |

## 7. Orden de implementación

1. `schemas.py`: `Literal` en `CitaResponse.estado`; normalizar `CitaCreate.origen`.
2. `main.py`: añadir `_calcular_duracion_total` y `_hay_solapamiento`.
3. `main.py`: ampliar `listar_citas` con filtros, orden, paginación.
4. `main.py`: añadir validación de solapamiento en `crear_cita`.
5. `main.py`: añadir validación de solapamiento y `estado` en `actualizar_cita`.
6. `AGENTS.md` y `memory.md`: actualizar.
7. Verificar por HTTP real (constitución VI).

## 8. Contradicciones, ambigüedades y lagunas encontradas

**Ninguna contradicción nueva** respecto a la spec aprobada. Las siguientes son clarificaciones
que la spec ya resolvió en la revisión QA (sección 8 del spec):

1. `terminada` se marca manualmente vía PATCH (no automático).
2. `origen` inválido → mensaje exacto "El origen debe ser 'usuario' o 'barbero'."
3. `Query` en main.py (no schema nuevo).
4. Aceptación de riesgo: precio retroactivo, solapamiento no retroactivo.

**Laguna menor detectada (no bloqueante):**

- El spec no define qué pasa si `fecha_desde` y `fecha_hasta` se envían como `datetime` con tz
  distinta. Se normaliza a naive en ambos. Documentado en F9 del QA.

**No se encontraron contradicciones con la constitución.** Todos los principios se respetan:

- I.4 (precio_total recalculado): cubierto.
- I.5 (no solapamiento): cubierto por RF-4.
- I.13 (intervalo): cubierto.
- II (capas separadas): funciones auxiliares en main.py, no se mezclan models/schemas.
- III (aprobación): no se modifica models.py ni se añaden dependencias.
- IV (contrato explícito): response_model y HTTPException con códigos.
- VI (verificado por HTTP): criterios de aceptación.
- VII (simplicidad): sin nuevas abstracciones ni dependencias.
