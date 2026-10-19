## Memoria del proyecto
**Instrucción para el Agente:** Mantén este archivo comprimido en un máximo de 50 líneas. Resume o elimina tareas pasadas que ya estén integradas en la V1 del código

## Estado actual
CRUD completo de usuarios, servicios y citas operativa. Feature 001 (filtrar y listar citas) implementada y verificada por HTTP real. Pendiente: autenticación y frontend.

## Aprendizajes y hallazgos
- La relación cita-servicios es **N:M**: tabla intermedia `cita_servicio` con clave primaria compuesta. El modelo 1:N anterior obligaba a duplicar citas.
- `create_all()` solo crea tablas faltantes: **no altera ni renombra las existentes**. Sin Alembic, cambiar el esquema obliga a regenerar la base (con pérdida de datos) o migrar a mano por SQL.
- Un `AttributeError` en un join (`models.cita_servicio` en vez de `models.CitaServicio`) pasó inadvertido porque estaba fuera del bloque `try/except`. **Verificar siempre el `status_code` en las pruebas**, no solo el cuerpo de la respuesta.
- `TestClient` no sirve: starlette 1.6.0 exige `httpx2`. Las pruebas se hacen levantando uvicorn y consultando por HTTP.
- **Pydantic parsea `"2026-12-01"` como `datetime` a medianoche si la unión es `datetime | date`.** Para distinguir "fecha sin hora" de "instante exacto" en query params hay que anotar `date | datetime` (en ese orden).
- Los tests de solapamiento fallan si no se cuida el "toque exacto": dos citas que se tocan (fin A = inicio B) **no** se solapan. Varios casos fallaron por esperar 400 donde la respuesta correcta era 200.

## Decisiones de arquitectura y tecnología
- Backend primero con FastAPI; frontend en React.js con Axios, Tailwind y React Router.
- `Cliente` se renombró a `Usuario` con campo `rol` (`'usuario'` | `'barbero'`), unificando al cliente que agenda y al barbero. Evita un sistema de cuentas paralelo.
- `Cita.origen` es un **snapshot** del rol al crear la cita, no un campo derivado.
- `Cita.precio_total` está desnormalizado y se recalcula en cada escritura, incluido el cambio del precio de un servicio.
- Se optó por regenerar la base en lugar de migrar: el proyecto está en fase temprana y no había datos valiosos.
- El script de consola `primer-proyecto` apuntaba a un módulo y no a una función; se creó `__init__.py` con `main()` que lanza uvicorn.
- Convenciones: Type Hints, docstrings y comentarios en español, `ConfigDict(from_attributes=True)`, `Depends(get_db)` y `db.rollback()` en `try/except`.

## Feature 001 — filtrar y listar citas (implementada)
- `GET /citas/` acepta filtros combinables (AND) por `fecha_desde`, `fecha_hasta`, `estado`, `usuario_id`, `origen`, `limit`, `offset`. Orden `fecha_hora ASC, id ASC`.
- El **solapamiento de horarios** se valida por intervalos `[inicio, inicio + suma de duraciones)`. La duración se calcula en memoria, no se almacena.
- Solo bloquean las citas activas (`pendiente`, `confirmada`); `cancelada` y `terminada` liberan el hueco. Intervalo abierto por la derecha.
- `estado` tiene 4 valores (`pendiente`, `confirmada`, `cancelada`, `terminada`) validados manualmente para devolver `400` (un `Literal` daría `422`).
- **Aceptación de riesgo:** cambiar la duración de un servicio no revalida las citas existentes (el precio sí se recalcula).
- Especificación, plan y tareas en `specs/001_filtrar_citas/`.

## Próximos pasos
- [ ] Sistema de autenticación y sesiones (LocalStorage / Cookies HttpOnly). Requiere especificación propia.
- [ ] Endpoint de contacto vía WhatsApp para agendar cita.
- [ ] Frontend React consumiendo la API (ojo: `servicio_id` → `servicios_ids` y `/clientes/` → `/usuarios/` son cambios de contrato).
- [ ] Evaluar Alembic antes del primer despliegue con datos reales.