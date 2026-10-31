# Tareas de desarrollo: 002 — Autenticación

**Estado:** ⏳ Pendiente de implementación (spec 002 aprobada, versión 1.0.0). Ninguna tarea completada todavía.

## Resumen de dependencias

```text
T1 (schemas) ──┐
               ├──► T3 (auth/register) ──┐
T2 (models) ──┼──► T4 (auth/login) ──► T5 (auth/logout) ──┼──► T7 (proteger /citas/) ──► T10 (verificación HTTP)
               ├──► T6 (deps get_current_user / require_rol) ──┼──► T8 (proteger /usuarios/) ──► T10
               │                                             ├──► T9 (proteger /servicios/) ──► T10
               │                                             └──► T7 (consume CitaCreate + helpers de T2)
T11 (docs) ───────────────────────────────────────────────────────────────────────────► (independiente, post-implementación)
```

---

## T1 — Actualizar esquemas Pydantic (`schemas.py`)

**Estado:** ✅ Completada

**Dependencias:** Ninguna (primera tarea).

**Descripción detallada:**
Añadir el campo de contraseña a los schemas de entrada, crear los schemas de autenticación (`LoginRequest`, `AuthResponse`, `LogoutResponse`) y asegurar que `UsuarioResponse` no exponga la contraseña. Ajustar `CitaCreate` para el origen.

**Archivos a modificar:** `src/primer_proyecto/schemas.py`

**Cambios a realizar:**

1. Añadir `contrasena` a los schemas de entrada (Registro / `UsuarioCreate`) con `min_length=8` y máximo 72 bytes (límite bcrypt).
2. Añadir validación de `nombre` (longitud 2–100) y `numero` (longitud 7–20); formato de `correo`.
3. Crear `LoginRequest` (`correo`, `contrasena`).
4. Crear `AuthResponse` (`token`, `usuario: UsuarioResponse`).
5. Crear `LogoutResponse` (`message`).
6. Asegurar que `UsuarioResponse` no incluye `contrasena`.
7. Ajustar `CitaCreate` (origen opcional).

**Criterios de aceptación:**

- [ ] El schema de entrada de registro acepta `contrasena` con `min_length=8` y máximo 72 bytes.
- [ ] El schema de respuesta de usuario no incluye la contraseña.
- [ ] Existen `LoginRequest`, `AuthResponse` y `LogoutResponse` con los campos definidos en la spec.
- [ ] `CitaCreate` admite origen opcional (`usuario` | `barbero`).
- **RF cubiertos:** RF-1 (RF-1.1 a RF-1.5), RF-4.4 / RF-4.5.

---

## T2 — Añadir modelos ORM de contraseña y sesión (`models.py`)

**Estado:** ✅ Completada

**Dependencias:** Ninguna.

**Archivos a modificar:** `src/primer_proyecto/models.py`

**Cambios a realizar:**

1. Añadir `contrasena_hash` a la clase `Usuario`.
2. Crear la clase `Sesion` (tabla `sesiones`) con `token_hash`, `usuario_id`, `created_at` y `expires_at`.

**Criterios de aceptación:**

- [ ] `Usuario` tiene el campo `contrasena_hash`.
- [ ] Existe el modelo `Sesion` mapeado a la tabla `sesiones`.
- **RF cubiertos:** RF-1.2, RF-2.2.

---

## T3 — Implementar `POST /auth/register` (`main.py`)

**Estado:** ✅ Completada

**Dependencias:** T1, T2.

**Archivos a modificar:** `src/primer_proyecto/main.py`

**Cambios a realizar:**

1. Añadir endpoint público `POST /auth/register` con `response_model=schemas.UsuarioResponse`.
2. Validar correo duplicado → `400` "El correo ya está registrado."; delegar validaciones de formato/largores a Pydantic → `422`.
3. Hashear contraseña con bcrypt y persistir con rol por defecto `usuario`.
4. Responder `201` sin token.

**Criterios de aceptación:**

- [ ] Registro con datos válidos → `201` y rol `usuario`.
- [ ] Registro con correo duplicado → `400`.
- [ ] Registro con datos inválidos → `422`.
- [ ] Registro sin `contrasena` → `422`.
- **RF cubiertos:** RF-1.

---

## T4 — Implementar `POST /auth/login` (`main.py`)

**Estado:** ⏳ Pendiente

**Dependencias:** T1, T2.

**Archivos a modificar:** `src/primer_proyecto/main.py`

**Cambios a realizar:**

1. Añadir endpoint público `POST /auth/login` recibiendo `LoginRequest`.
2. Buscar usuario por correo, verificar contraseña con `checkpw`.
3. Generar token opaco con `secrets.token_urlsafe(32)` y persistir SHA-256 + TTL 24 h en `sesiones`.
4. Responder `200` con `AuthResponse` (token + usuario); credenciales inválidas → `401` "Credenciales inválidas.".

**Criterios de aceptación:**

- [ ] Login con credenciales válidas → `200` con token y datos del usuario.
- [ ] Login con credenciales inválidas → `401`.
- [ ] Login con datos inválidos → `422`.
- **RF cubiertos:** RF-2.

---

## T5 — Implementar `POST /auth/logout` (`main.py`)

**Estado:** ⏳ Pendiente

**Dependencias:** T4, T6.

**Archivos a modificar:** `src/primer_proyecto/main.py`

**Cambios a realizar:**

1. Añadir endpoint `POST /auth/logout` con Bearer.
2. Sin token / token inválido / token expirado → `401`; con token válido → eliminar sesión y responder `200` con `LogoutResponse`.

**Criterios de aceptación:**

- [ ] Logout con token válido → `200`; token queda invalidado.
- [ ] Logout con token inválido o expirado → `401`.
- **RF cubiertos:** RF-3.

---

## T6 — Añadir dependencias de autenticación y control de rol (`main.py`)

**Estado:** ⏳ Pendiente

**Dependencias:** T2.

**Archivos a modificar:** `src/primer_proyecto/main.py`

**Cambios a realizar:**

1. Añadir `HTTPBearer(auto_error=False)` y dependencia `get_current_user`.
2. Localizar sesión por hash SHA-256 y comprobar expiración (TTL 24 h).
3. Añadir control de rol (p. ej. `require_rol`) que devuelve 403 si el rol es insuficiente.

**Criterios de aceptación:**

- [ ] Acceso a endpoint protegido sin token → `401`.
- [ ] Token expirado → `401` "La sesión ha expirado.".
- [ ] Token revocado → `401` "Sesión no válida.".
- [ ] Rol insuficiente → `403`.
- **RF cubiertos:** RF-4.1, RF-4.7, RF-5.1.

---

## T7 — Proteger endpoints de citas (`main.py`)

**Estado:** ⏳ Pendiente

**Dependencias:** T6, T1, T2.

**Archivos a modificar:** `src/primer_proyecto/main.py`

**Cambios a realizar:**

1. Añadir autenticación (`get_current_user`) a `GET /citas/`, `POST /citas/`, `PATCH /citas/{cita_id}` y `DELETE /citas/{cita_id}`.
2. Aplicar control por rol y alcance: barbero → todas; usuario → solo las propias; creación con origen por rol; `usuario_id` ajeno en creación por usuario → `403`.

**Criterios de aceptación:**

- [ ] Barbero autenticado `GET /citas/` → `200` con todas.
- [ ] Usuario autenticado `GET /citas/` → `200` con solo las suyas.
- [ ] Usuario autenticado con `usuario_id` ajeno → `403`.
- [ ] Barbero autenticado `POST /citas/` → `201` con origen `barbero`.
- [ ] Usuario autenticado `POST /citas/` → `201` con origen `usuario` y su propio `usuario_id`.
- [ ] `PATCH /citas/{id}` con rol `usuario` sobre cita ajena → `403`.
- **RF cubiertos:** RF-4.2 a RF-4.6.

---

## T8 — Proteger endpoints de usuarios (`main.py`)

**Estado:** ⏳ Pendiente

**Dependencias:** T6.

**Archivos a modificar:** `src/primer_proyecto/main.py`

**Cambios a realizar:**

1. Añadir autenticación (`get_current_user`) y control por rol a `GET /usuarios/`, `POST /usuarios/`, `PATCH /usuarios/{usuario_id}` y `DELETE /usuarios/{usuario_id}`.
2. GET: barbero → todos; usuario → solo el propio.
3. POST: solo barbero.
4. PATCH: barbero → cualquier; usuario → solo el propio (sin gestión de rol); validaciones en orden 401 → 404 → 403 → 400 → 200.

**Criterios de aceptación:**

- [ ] `GET /usuarios/` con rol `barbero` → todos; con rol `usuario` → solo el propio.
- [ ] `PATCH /usuarios/{usuario_id}`: usuario autenticado solo puede modificar su propio registro sin gestión de rol → `200`; sobre registro ajeno → `403`.
- [ ] Endpoints de usuarios con rol no apropiado → `403`.
- **RF cubiertos:** RF-4.7.

---

## T9 — Proteger endpoints de servicios (`main.py`)

**Estado:** ⏳ Pendiente

**Dependencias:** T6.

**Archivos a modificar:** `src/primer_proyecto/main.py`

**Cambios a realizar:**

1. Dejar `GET /servicios/` público.
2. Añadir control por rol `barbero` a `POST /servicios/`, `PATCH /servicios/{servicio_id}` y `DELETE /servicios/{servicio_id}` → `403` si el solicitante no es barbero.

**Criterios de aceptación:**

- [ ] `POST`/`PATCH`/`DELETE /servicios/` con rol no `barbero` → `403`.
- **RF cubiertos:** RF-5.1.

---

## T10 — Verificación por HTTP real

**Estado:** ⏳ Pendiente

**Dependencias:** T1 a T9.

**Archivos a modificar:** Ninguno (solo verificación).

**Pasos:**

1. Levantar uvicorn en puerto libre.
2. Ejecutar los criterios de aceptación de la spec (sección 6) por HTTP real.
3. Detener uvicorn.

**Criterios de aceptación:**

- [ ] Todos los criterios de aceptación de la spec se cumplen.
- [ ] No hay errores 500 en ninguna petición.
- [ ] Los flujos de auth (register → login → logout → acceso protegido) funcionan end to end.
- **RF cubiertos:** Todos.

---

## T11 — Actualizar documentación

**Estado:** ⏳ Pendiente

**Dependencias:** T3 a T10 (post-implementación).

**Archivos a modificar:** `AGENTS.md`, `memory.md`.

**Cambios a realizar:**

1. Actualizar rutas de la API con los nuevos endpoints `/auth/*` y la matriz de protección.
2. Actualizar modelo de datos (contrasena_hash, tabla sesiones).
3. Actualizar `memory.md` con decisiones y estado (máx. 50 líneas).

**Criterios de aceptación:**

- [ ] `AGENTS.md` refleja el nuevo contrato de autenticación.
- [ ] `memory.md` tiene ≤ 50 líneas.
- **RF cubiertos:** Todos (documentación).

---

## Diagrama de dependencias

```text
T1 (schemas) ──┐
               ├──► T3 (auth/register) ──┐
T2 (models) ──┼──► T4 (auth/login) ──► T5 (auth/logout) ──┼──► T7 (proteger /citas/) ──► T10 (verificación HTTP)
               ├──► T6 (deps get_current_user / require_rol) ──┼──► T8 (proteger /usuarios/) ──► T10
               │                                             ├──► T9 (proteger /servicios/) ──► T10
               │                                             └──► T7 (consume CitaCreate + helpers de T2)
T11 (docs) ───────────────────────────────────────────────────────────────────────────► (independiente, post-implementación)
```

## Notas

- No se crean archivos nuevos (respeta la regla de AGENTS.md sobre creación de archivos).
- `bcrypt` está aprobada por el usuario; no ejecutar `uv add` sin aprobación explícita.
- No se modifican `database.py` ni `CitaServicio`.
- Cada tarea es atómica y secuencial: se puede implementar y verificar de forma independiente.
- Las tareas NO están completadas: es fase de plan y tareas (SDD fase 3).
