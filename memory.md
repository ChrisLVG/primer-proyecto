## Memoria del proyecto
Mantén este archivo en máx. 50 líneas. Resume o elimina tareas pasadas integradas en V1.

## Estado actual
CRUD completo de usuarios, servicios y citas. Feature 001 verificada por HTTP real.
Feature 002: T1-T11 completadas y validadas por el revisor RF por RF (veredicto: SIN CAMBIOS NECESARIOS). Fix Decisi�n 8 �8: contrasena opcional en PATCH /usuarios/{id} para establecer hash bcrypt al promover a barbero.
Nota: T10 verificada por HTTP real (0 errores 500); caminos positivos de barbero ahora ejecutables en principio tras el fix.

## T8 — Proteger endpoints de usuarios (main.py)
- `GET /usuarios/`: `get_current_user`; barbero→todos; usuario→solo propio. `response_model=list[UsuarioResponse]` para no exponer `contrasena_hash`.
- `POST /usuarios/`: `require_rol("barbero")`; rol por defecto `"usuario"`; bcrypt si `contrasena` viene, si no `contrasena_hash=None`.
- `PATCH /usuarios/{id}`: `get_current_user`; orden 401→404→403→400→200. Usuario solo propio, sin gestión de rol (403 si intenta rol ajeno o cambiar rol). Barbero edita cualquier usuario, incluido rol.
- `DELETE /usuarios/{id}`: `require_rol("barbero")`; borra citas, cita_servicio, sesiones y usuario; 404 si no existe; 409 IntegrityError.

## Aprendizajes y hallazgos
- `get_current_user` y `require_rol` viven en `autenticador.py`; se importan como `autenticador.get_current_user` / `autenticador.require_rol`.
- `autenticador.py` expone el router `/auth`, montado desde `main.py`; tokens opacos Bearer se guardan como SHA-256 y expiran en 24 h.
- `create_all()` solo crea tablas faltantes: no altera ni renombra las existentes. Sin Alembic, cambiar esquema exige regenerar BD o migrar a mano por SQL.
- `TestClient` no sirve (starlette 1.6.0 exige `httpx2`). Verificar levantando uvicorn y consultando HTTP.
- Pydantic anota `date | datetime` (en ese orden) para distinguir fecha sin hora de instante exacto.

## Decisiones de arquitectura
- Backend FastAPI; frontend React.js con Axios, Tailwind, React Router.
- `Usuario` unifica cliente y barbero con `rol` (`usuario` | `barbero`). `Cita.origen` es snapshot al crear. `Cita.precio_total` desnormalizado, se recalcula en escritura.
- Sesión: token opaco SHA-256 en tabla `sesiones`, TTL 24 h. Contraseña con bcrypt, columna `contrasena_hash`.
- Convenciones: type hints 3.12+, docstrings/comentarios en español, `ConfigDict(from_attributes=True)`, `Depends(get_db)`, `db.rollback()` en try/except.

## Próximos pasos
- [x] T9: proteger servicios (GET público; escritura solo barbero).
- [x] T9: proteger servicios (GET p�blico; escritura solo barbero).
- [x] T10: verificar por HTTP real, incluida la cuenta barbero autenticada con contrase�a.
