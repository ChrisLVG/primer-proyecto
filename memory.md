## Memoria del proyecto
**Instrucción para el Agente:** Mantén este archivo comprimido en un máximo de 50 líneas. Resume o elimina tareas pasadas que ya estén integradas en la V1 del código

## Estado actual
CRUD completo de usuarios, servicios y citas operativa y verificada (34/34 casos de prueba).
Pendiente: solapamiento de horarios y sistema de autenticación.

## Aprendizajes y hallazgos
- Se desversionaron los `.pyc` y la base SQLite que estaban en Git pese a estar cubiertos por `.gitignore`; sus copias locales se conservaron.
- La relación cita-servicios es **N:M**: se resolvió con la tabla intermedia `cita_servicio` y clave primaria compuesta. El modelo 1:N anterior obligaba a duplicar citas.
- `create_all()` solo crea tablas faltantes: **no altera ni renombra las existentes**. Sin Alembic, cambiar el esquema obliga a regenerar la base (con pérdida de datos) o migrar a mano por SQL.
- Un `AttributeError` en un join (`models.cita_servicio` en vez de `models.CitaServicio`) pasó inadvertido porque estaba fuera del bloque `try/except`. Verificar el status code en las pruebas, no solo los datos.
- `TestClient` no sirve: starlette 1.6.0 exige `httpx2`. Las pruebas se hacen levantando uvicorn y consultando por HTTP.

## Decisiones de arquitectura y tecnología
- Backend primero con FastAPI; frontend en React.js con Axios, Tailwind y React Router.
- `Cliente` se renombró a `Usuario` con campo `rol` (`'usuario'` | `'barbero'`), unificando al cliente que agenda y al barbero. Evita un sistema de cuentas paralelo.
- `Cita.origen` es un **snapshot** del rol al crear la cita, no un campo derivado: un cambio de rol posterior no reescribe el historial.
- `Cita.precio_total` está desnormalizado y se recalcula en cada escritura, incluido el cambio del precio de un servicio, para que no arrastre valores obsoletos.
- Se opted por regenerar la base en lugar de migrar: el proyecto está en fase temprana y no había datos valiosos.
- El script de consola `primer-proyecto` apuntaba a un módulo y no a una función; se creó `__init__.py` con `main()` que lanza uvicorn.
- Convenciones: Type Hints, docstrings y comentarios en español, `ConfigDict(from_attributes=True)`, `Depends(get_db)` y `db.rollback()` en `try/except`.

## Próximos pasos
- [ ] **Solapamiento de horarios**: comparar intervalos `[inicio, inicio + duración_total)` en vez de igualdad exacta de `fecha_hora`.
- [ ] Sistema de autenticación y sesiones (LocalStorage / Cookies HttpOnly).
- [ ] Endpoint de contacto vía WhatsApp para agendar cita.
- [ ] Frontend React consumiendo la nueva API (ojo: `servicio_id` → `servicios_ids` y `/clientes/` → `/usuarios/` son cambios de contrato).
- [ ] Evaluar Alembic antes del primer despliegue con datos reales.