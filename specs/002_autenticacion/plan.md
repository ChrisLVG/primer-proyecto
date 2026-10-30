# Plan: 002 — Autenticación

## 1. Cambios de código previstos

### Archivos modificados

| Archivo | Responsabilidad | Cambio |
| --- | --- | --- |
| `src/primer_proyecto/schemas.py` | Validación Pydantic | Añadir `contrasena` a los schemas de entrada (Registro / `UsuarioCreate`); crear `LoginRequest`, `AuthResponse`, `LogoutResponse`; redefinir `UsuarioResponse` sin contraseña; ajustar `CitaCreate` (origen opcional). |
| `src/primer_proyecto/models.py` | Modelos ORM | Añadir `contrasena_hash` a `Usuario` y crear tabla `sesiones` (`token_hash`, `usuario_id`, `created_at`, `expires_at`). |
| `src/primer_proyecto/main.py` | Rutas y lógica de negocio | Añadir `POST /auth/register`, `POST /auth/login`, `POST /auth/logout`; añadir dependencias `get_current_user` y control de rol; aplicar protección en citas, usuarios y servicios según la matriz; registrar seguridad Bearer en OpenAPI. |
| `pyproject.toml` / `uv.lock` | Dependencias | Añadir dependencia `bcrypt` (aprobada por el usuario). |
| `AGENTS.md` / `memory.md` | Reglas y bitácora | Actualizar tras la implementación. |

### Archivos NO modificados (decisión explícita)

- `src/primer_proyecto/database.py`: sin cambios.
- Tabla intermedia `cita_servicio` / clase `CitaServicio`: sin cambios.

### Dependencias

- Nueva: `bcrypt` (`hashpw` / `checkpw`), con instalación vía `uv add bcrypt` pendiente de aprobación explícita del usuario. La dependencia **está ya aprobada por el usuario** (constitución III satisfecha con esa aprobación previa); el plan la registra como aprobada y no ejecuta el comando hasta obtener confirmación explícita.

### Estructura de archivos

- Sin archivos nuevos. Cambios incrementales sobre `schemas.py`, `models.py`, `main.py` y `pyproject.toml`.

## 2. Lógica de negocio, funciones, interfaces y validaciones

### Funciones auxiliares nuevas en `main.py`

- `_hash_token(token)`: devuelve el SHA-256 del token opaco (para almacenamiento en `sesiones`).
- `_crear_sesion(db, usuario_id)`: genera el token con `secrets.token_urlsafe(32)`, persiste `token_hash`, `usuario_id`, `created_at` y `expires_at` (ahora + 24 h), y devuelve el token.
- `_obtener_usuario_por_token(db, token)`: localiza la sesión por `token_hash`, comprueba `expires_at` y devuelve el `Usuario` o lanza el error 401 correspondiente.

### Interfaces

- Dependencia `get_current_user`: recibe el token del header `Authorization: Bearer <token>` (con `HTTPBearer(auto_error=False)` para responder 401 y no 403 cuando falta la cabecera) junto a la sesión de BD (`Depends(get_db)`); devuelve el usuario autenticado o lanza 401 con el mensaje según el fallo ("No autenticado." / "Sesión no válida." / "La sesión ha expirado.").
- Control de rol: verificación de `usuario.rol` contra el rol requerido, lanzando 403 cuando el rol es insuficiente.

### Validaciones a implementar (resumen por RF)

| RF | Área | Validación |
| --- | --- | --- |
| RF-1.1 a RF-1.5 | `POST /auth/register` | Validar formato de correo, longitud mínima de contraseña (8), máxima (72 bytes), nombre (2–100) y número (7–20); devolver 422 si falla. 400 "El correo ya está registrado." si el correo ya existe. Persistir contraseña hasheada con bcrypt y asignar rol por defecto `usuario`. Responder 201 con `UsuarioResponse` sin contraseña y sin token. |
| RF-2.1 a RF-2.3 | `POST /auth/login` | Autenticar con correo y contraseña. Emitir token opaco (`secrets.token_urlsafe(32)`) con hash SHA-256 en tabla `sesiones` y TTL de 24 h. Rechazar credenciales inválidas con 401 "Credenciales inválidas.". |
| RF-3.1 a RF-3.2 | `POST /auth/logout` | Con token Bearer válido eliminar la sesión del token; sin token, inválido o expirado responder 401. |
| RF-4.1 | Dependencias de auth | Sin token → 401 "No autenticado."; token inválido → 401 "Sesión no válida."; expirado → 401 "La sesión ha expirado."; rol insuficiente → 403. |
| RF-4.2 a RF-4.6 | Endpoints de citas protegidos | Barbero autenticado → todas las citas; usuario autenticado → solo las propias (filtro `usuario_id` restringido al propio); barbero crea cita con origen por defecto `barbero` y `usuario_id` de cliente señalado; usuario crea cita con origen por defecto `usuario` y `usuario_id` propio (ajeno → 403); origen enviado que no corresponda al rol → 400. |
| RF-4.7 | Endpoints de usuarios protegidos | Barbero → cualquier registro; usuario autenticado → solo el propio (sin gestión de rol); validaciones en orden 401 → 404 → 403 → 400 → 200. |
| RF-5.1 | Endpoints de servicios | Solo rol `barbero` puede crear, modificar o eliminar; el `GET` se mantiene público. |

## 3. Casos límite a considerar

1. Registro con correo duplicado → `400` "El correo ya está registrado.".
2. Registro con datos inválidos (correo, contraseña < 8 o > 72 bytes, nombre, número) → `422`.
3. Registro con datos válidos → `201`, rol `usuario`, `UsuarioResponse` sin contraseña, sin token.
4. Login con credenciales inválidas → `401` "Credenciales inválidas.".
5. Login con datos inválidos → `422`.
6. Login con credenciales válidas → `200` con `AuthResponse` (token + usuario).
7. Logout sin token / con token inválido / con token expirado / con token válido → `401` / `401` / `401` / `200`.
8. Acceso a endpoint protegido sin token → `401` "No autenticado.".
9. Token expirado al usarlo → `401` "La sesión ha expirado.".
10. Token revocado (logout) → `401` "Sesión no válida.".
11. Rol insuficiente → `403`.
12. Borrado de usuario/servicio con citas → `409` (constitución I).
13. `PATCH /usuarios/{id}` con rol inválido → `400` "El rol debe ser 'usuario' o 'barbero'.".
14. Crear cita con `usuario_id` inexistente → `400` "El usuario no está registrado.".
15. Crear cita con origen inválido → `400` "El origen debe ser 'usuario' o 'barbero'.".
16. Usuario autenticado con origen que no corresponda a su rol → `400`.
17. Usuario autenticado con `usuario_id` ajeno en `POST /citas/` → `403`.
18. Token expirado simulado (sin esperar las 24 h) → `401` en endpoint protegido.
19. Solapamiento / cita duplicada / servicios no registrados → `400` (spec 001).

## 4. Posibles riesgos de implementación

| Riesgo | Mitigación |
| --- | --- |
| `HTTPBearer` con `auto_error=True` responde `403` en lugar de `401` cuando falta el header | Configurar `HTTPBearer(auto_error=False)` y responder `401` manualmente. |
| bcrypt trunca hashes a 72 bytes | Validar contraseña con máximo 72 bytes en el schema (RF-1.4b). |
| `create_all()` no migra esquema existente | La tabla `sesiones` se crea en base nueva; `usuarios.contrasena_hash` requiere regeneración o migración manual SQL. |
| Almacenar token opaco en texto plano | Almacenar solo SHA-256 (`token_hash`) + TTL 24 h en `sesiones`. |

## 5. Decisiones técnicas justificadas

1. **Token opaco con tabla `sesiones`** (RF-2, spec §8 decisión 1): `secrets.token_urlsafe(32)` (256 bits), hash SHA-256 almacenado, TTL 24 h, logout elimina la fila.
2. **Hash de contraseña con `bcrypt`** (RF-1.2, spec §8 decisión 2): `hashpw` / `checkpw`, columna `usuarios.contrasena_hash`, máximo 72 bytes.
3. **Transporte del token**: Bearer en header `Authorization: Bearer <token>` (spec §8, decisión 3).
4. **TTL de la sesión**: 24 horas (spec §8, decisión 4).
5. **Alta de barberos**: vía `PATCH /usuarios/{usuario_id}` con `rol: "barbero"` (escala existente); opcionalmente aceptar `contrasena` para establecer el hash al promover (Opción A, spec §8.8).
6. **Rate limiting**: fuera de alcance en esta fase (spec §8.6).
7. **JWT / refresh tokens**: fuera de alcance; la estrategia elegida es token opaco (spec §4).

## 6. Cobertura de RF

| RF | Sección del plan / tarea que lo cubre |
| --- | --- |
| RF-1 (registro) | Sección 2, `POST /auth/register`; tareas T1, T3. |
| RF-2 (login) | Sección 2, `POST /auth/login`; tareas T1, T2, T4. |
| RF-3 (logout) | Sección 2, `POST /auth/logout`; tareas T4, T5, T6. |
| RF-4 (protección por rol) | Sección 2, dependencias y endpoints de citas; tareas T6, T7, T8. |
| RF-5 (servicios) | Sección 2, endpoints de servicios; tarea T9. |

## 7. Orden de implementación

1. `schemas.py`: añadir `contrasena` a entrada, crear `LoginRequest`, `AuthResponse`, `LogoutResponse`, redefinir `UsuarioResponse` sin contraseña, ajustar `CitaCreate`.
2. `models.py`: añadir `contrasena_hash` a `Usuario` y crear tabla `sesiones`.
3. `main.py`: añadir helpers de token/sesión y dependencias `get_current_user` / control de rol.
4. `main.py`: implementar `POST /auth/register`, `POST /auth/login`, `POST /auth/logout`.
5. `main.py`: aplicar protección en `/citas/`, `/usuarios/` y `/servicios/` según la matriz.
6. `pyproject.toml` / `uv.lock`: añadir `bcrypt` (con aprobación previa del usuario).
7. `AGENTS.md` / `memory.md`: actualizar.
8. Verificar por HTTP real (uvicorn) todos los criterios de aceptación de la spec.

## 8. Contradicciones, ambigüedades y lagunas encontradas

- **Ambigüedad menor resuelta por convención:** el spec nombra el response del login `AuthResponse` (con `token` y `usuario`); la tarea sugerida hablaba de `LoginResponse`. Se adopta el nombre del spec: `AuthResponse`.
- **Ambigüedad menor:** el contrato de `POST /usuarios/` (alta de usuario con rol `usuario`, o alta de barbero vía `rol`) frente al registro público centralizado en `POST /auth/register`. El plan asume que `POST /usuarios/` pasa a estar protegido por rol `barbero`.
- **Laguna:** no incluye reseteo de contraseña ni recuperación de cuenta (fuera de alcance, spec §9).
- **Laguna:** no incluye rate limiting (decisión: fuera de alcance, spec §8.6).

**No se encontraron contradicciones con la constitución.** Se respetan los principios I (integridad, 409, solapamiento), II (capas separadas, `Depends(get_db)`), III (aprobación previa para models/dependencias), IV (contrato explícito), V (seguridad), VI (verificación por HTTP) y VII (simplicidad).

## 9. Estado de la base de datos

- **Cambio de esquema previsto:** añadir `usuarios.contrasena_hash` y crear tabla `sesiones`.
- **Estado:** pendiente de ejecución. `create_all()` solo crea tablas faltantes y no altera las existentes; por tanto aplicar el cambio exige **regenerar la base** (borrar el `.db` y arrancar, con pérdida de datos) o **migración manual con SQL**.
- **Nota:** no ejecutar regeneración ni migración manual sin la aprobación explícita del usuario para borrar datos (AGENTS.md / constitución III).
