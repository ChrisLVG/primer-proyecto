# Constitución del Proyecto: Sitio web de citas para barbería

**Versión:** 1.0.0 (borrador)

Principios innegociables del proyecto. Toda especificación, plan, tarea y cambio de código debe respetarlos. Si una especificación los contradice, se corrige la especificación o se enmienda esta constitución; nunca se ignora.

## I. El backend protege la integridad de los datos

- Las reglas de negocio se validan siempre en la API; el frontend nunca es la única barrera.
- Se respetan las claves foráneas: borrar un usuario o servicio con citas asociadas devuelve `409`.
- `Cita.origen` es un snapshot: se escribe al crear la cita y no se recalcula después.
- `Cita.precio_total` se recalcula en toda escritura que pueda dejarlo obsoleto (crear cita, cambiar sus servicios, cambiar el precio de un servicio).
- Una cita ocupa el intervalo `[inicio, inicio + suma de duraciones)`, y dos citas no pueden solaparse.

## II. Capas separadas y sin duplicación

- `models.py` (SQLAlchemy), `schemas.py` (Pydantic) y `main.py` (rutas) nunca se mezclan.
- La sesión de BD se inyecta solo con `Depends(get_db)`.
- La lógica de negocio reutilizable vive en funciones auxiliares; no se copia entre endpoints.
- El frontend consume la API y no reimplementa reglas de negocio (por ejemplo, no calcula precios).

## III. Todo cambio estructural requiere aprobación

- Se necesita aprobación previa del usuario para: modificar `models.py` o las tablas, añadir dependencias o tocar `pyproject.toml`, y crear o eliminar archivos.
- No hay migraciones automáticas (`create_all()` no altera tablas existentes); todo cambio de esquema se planifica antes de ejecutarse.
- Ningún comando destructivo ni reinicio de la BD sin petición explícita.
- Los cambios son incrementales: no se reescriben funciones operativas sin necesidad demostrada.

## IV. Contrato de API explícito

- Cada endpoint declara `response_model` y esquemas de entrada.
- Los errores de negocio usan `HTTPException` con `400`, `404`, `409` o `422`, y mensajes en español.
- Un cambio que rompa el contrato (rutas, campos, formas de respuesta) se documenta en la especificación antes de implementarse.

## V. Seguridad y privacidad por diseño

- Los identificadores son UUID v4 para que no puedan adivinarse desde las URLs.
- Los datos personales (nombre, teléfono, correo) solo se exponen a quien corresponde: el usuario ve lo suyo y el barbero ve todas las citas.
- Los roles válidos son únicamente `usuario` y `barbero`.
- La autenticación y las sesiones tienen su propia especificación; hasta entonces la API no se expone públicamente.

## VI. Verificado por HTTP real antes de dar algo por terminado

- Se levanta uvicorn y se consultan los endpoints (`TestClient` no funciona con la versión actual de Starlette).
- Las pruebas comprueban el `status_code`, incluidos los casos de error, y no solo el cuerpo de la respuesta.

## VII. Simplicidad y trazabilidad

- El stack es fijo: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, SQLite local, uv; React, Axios, Tailwind y React Router en el frontend.
- No se añade código, abstracciones ni dependencias "por si acaso"; todo responde a una especificación.
- Antes de cada tarea se lee `memory.md`; al terminarla se actualiza (máximo 50 líneas), y también `AGENTS.md` si cambiaron las reglas.

## Gobernanza

Una enmienda se propone con su motivo, la aprueba explícitamente el usuario y se registra subiendo la versión. Esta constitución prevalece sobre `AGENTS.md` en caso de conflicto.
