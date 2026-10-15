# Memoria del proyecto

> Instrucción para el Agente: Mantén este archivo comprimido en un máximo de 50 líneas. Resume o elimina tareas pasadas que ya estén integradas en la V1 del código.

## Estado actual

CRUD completo de usuarios, servicios y citas, verificado con 34/34 pruebas. Pendiente: solapamiento de horarios y autenticación.

## Aprendizajes y hallazgos

- `.pyc` y la base SQLite se desversionaron pese a `.gitignore`; se conservaron localmente.
- La relación cita-servicios es N:M con `cita_servicio` y PK compuesta; el modelo 1:N duplicaba citas.
- `create_all()` solo crea tablas faltantes; sin Alembic, los cambios de esquema requieren regenerar la BD o migrar SQL a mano.
- Un `AttributeError` en un join pasó inadvertido fuera del `try/except`; comprobar `status_code` en pruebas, no solo los datos.
- `TestClient` no sirve con Starlette 1.6.0; las pruebas se ejecutan levantando uvicorn y llamando por HTTP.

## Decisiones de arquitectura

- Backend en FastAPI; frontend en React.js con Axios, Tailwind y React Router.
- `Cliente` pasó a `Usuario` con `rol` (`'usuario'` | `'barbero'`), unificando cliente y barbero.
- `Cita.origen` es un snapshot al crear la cita; no se reescribe con cambios posteriores.
- `Cita.precio_total` se recalcula en cada escritura para evitar valores obsoletos.
- Se optó por regenerar la BD en fase temprana y sin datos valiosos.
- `primer-proyecto` apuntaba a un módulo y no a una función; se agregó `__init__.py` con `main()` que lanza uvicorn.
- Convenciones: Type Hints, docstrings en español, `ConfigDict(from_attributes=True)`, `Depends(get_db)` y `db.rollback()` en `try/except`.

## Próximos pasos

- [ ] Solapamiento de horarios: comparar intervalos `[inicio, inicio + duración_total)`.
- [ ] Autenticación y sesiones (LocalStorage/Cookies HttpOnly).
- [ ] Endpoint de contacto por WhatsApp.
- [ ] Frontend React adaptado al contrato nuevo (`servicio_id` → `servicios_ids`, `/clientes/` → `/usuarios/`).
- [ ] Evaluar Alembic antes del primer despliegue con datos reales.
