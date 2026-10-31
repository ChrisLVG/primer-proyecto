# Especificación: 002 — Autenticación

**Versión:** 1.0.0 (aprobada)
**Estado:** Aprobada

## 1. Objetivo y contexto

Permitir el registro, el inicio y el cierre de sesión de usuarios y barberos, y proteger los endpoints de la API mediante autenticación y control de acceso por rol (`usuario` | `barbero`).

### Contexto

- La API no tiene autenticación todavía: los endpoints de citas aceptan `usuario_id` como query param (patrón "honor system" de la spec 001). La constitución del proyecto (V.4) ya prevé que la autenticación y las sesiones tienen su propia especificación.
- Los roles `usuario` y `barbero` ya existen en `usuarios.rol`, con validación manual (400) y valor por defecto `usuario`.
- El modelo `Usuario` no tiene campo para contraseña ni mecanismo de sesión. Su incorporación es un cambio estructural de base de datos que requiere aprobación previa (constitución III) y, en la práctica, regeneración o migración manual del archivo de base de datos.
- El frontend no existe: la API define el contrato de sesión; el transporte del token ya está fijado como Bearer en header `Authorization: Bearer <token>` (decisión técnica §8, decisión 3; la alternativa cookie HttpOnly quedó descartada).

### Relación con la especificación 001

La spec 001 (versión 1.1.0, **Aprobada**) declaraba en su sección 3 que no incluía autenticación y que el filtro por `usuario_id` era de tipo "honor system". Dicha declaración queda **enmendada por la presente spec 002** para el alcance de protección de endpoints: los endpoints de citas, usuarios y servicios descritos en las RFs se protegen por autenticación y control de acceso por rol según esta spec. La presente spec prevalece sobre la declaración de la 001 mientras ambas estén vigentes; al ser aprobada, se recomienda actualizar la sección 3 de la spec 001 para reflejar la protección.

## 2. Requisitos funcionales

Formato EARS: cada requisito expresa una afirmación atómica ("El sistema debe ...") sin ambigüedades, con un único criterio de éxito.

### RF-1 — Registro de usuarios

- **RF-1.1** El sistema debe permitir el registro de un nuevo usuario con nombre, correo electrónico, número de teléfono y contraseña.
- **RF-1.2** El sistema debe almacenar la contraseña hasheada con la librería segura `bcrypt` (dependencia nueva aprobada por el usuario; la constitución III queda satisfecha al contar con esa aprobación previa), nunca en texto plano.
- **RF-1.3** El sistema debe validar que el correo no esté registrado previamente; si ya está registrado, debe devolver el error "El correo ya está registrado." con código 400.
- **RF-1.4a** El sistema debe validar el formato del correo electrónico y debe devolver 422 si es inválido.
- **RF-1.4b** El sistema debe validar la longitud mínima de la contraseña (8 caracteres, máximo 72 bytes) y debe devolver 422 si no se cumple.
- **RF-1.4c** El sistema debe validar el nombre (longitud 2–100) y debe devolver 422 si no se cumple.
- **RF-1.4d** El sistema debe validar el número de teléfono (longitud 7–20) y debe devolver 422 si no se cumple.
- **RF-1.5** El sistema debe asignar el rol por defecto `usuario` al registrarse.

### RF-2 — Inicio de sesión

- **RF-2.1** El sistema debe autenticar a un usuario mediante su correo electrónico y su contraseña.
- **RF-2.2** El sistema debe emitir un token de sesión opaco (generado con `secrets.token_urlsafe(32)`, que aporta 256 bits de entropía) que se almacena en la tabla `sesiones` como hash SHA-256, con fecha de expiración (TTL) de 24 horas.
- **RF-2.3** El sistema debe rechazar el inicio de sesión con credenciales inválidas, devolviendo el error "Credenciales inválidas." con código 401.

### RF-3 — Cierre de sesión

- **RF-3.1** El sistema debe permitir cerrar la sesión del usuario autenticado.
- **RF-3.2** El sistema debe invalidar la sesión/token emitido (eliminando su registro en la tabla `sesiones`); un token invalidado no admite peticiones autenticadas.

### RF-4 — Protección de endpoints por rol

- **RF-4.1** El sistema debe exigir un token de sesión válido (formato `Authorization: Bearer <token>`) para acceder a los endpoints protegidos; sin token, con token inválido o con token expirado, debe devolver 401.
- **RF-4.2** El sistema debe permitir que un barbero autenticado consulte todas las citas.
- **RF-4.3** El sistema debe permitir que un usuario autenticado consulte solo sus propias citas.
- **RF-4.4** El sistema debe permitir que un barbero autenticado cree citas con origen `barbero`, señalando al cliente mediante el campo `usuario_id` del body. El origen por defecto para un barbero es `barbero`; si el solicitante envía un `origen` que no corresponde a su rol, debe devolver `400`.
- **RF-4.5** El sistema debe permitir que un usuario autenticado cree citas con origen `usuario`, siempre asociadas a su propio identificador. El origen por defecto para un usuario es `usuario`; si el solicitante envía un `origen` que no corresponde a su rol, debe devolver `400`.
- **RF-4.6** El sistema debe restringir el filtro `usuario_id` de `GET /citas/` a las citas del propio usuario cuando el solicitante tiene rol `usuario`.
- **RF-4.7** El sistema debe permitir que un usuario autenticado consulte y modifique únicamente su propio registro; el barbero puede gestionar cualquier registro.

### RF-5 — Gestión de servicios restringida a barbero

- **RF-5.1** El sistema debe permitir que solo un usuario autenticado con rol `barbero` pueda crear, modificar o eliminar servicios.

### Reglas de acceso por endpoint

| Endpoint | Método | Rol requerido | Alcance | Notas |
| --- | --- | --- | --- | --- |
| `POST /auth/register` | POST | Público | — | RF-1. Crea usuario con rol `usuario`. No emite token. |
| `POST /auth/login` | POST | Público | — | RF-2. Emite token. |
| `POST /auth/logout` | POST | Autenticado | propio | RF-3. Invalida la sesión. |
| `GET /servicios/` | GET | Público | — | RF-5.1 (solo lectura pública). |
| `POST /servicios/` | POST | Barbero | — | RF-5.1. |
| `PATCH /servicios/{servicio_id}` | PATCH | Barbero | — | RF-5.1. |
| `DELETE /servicios/{servicio_id}` | DELETE | Barbero | — | RF-5.1. Elimina las citas que quedarían sin servicios y recalcula el precio de las citas restantes. |
| `GET /citas/` | GET | Autenticado | Barbero → todas; Usuario → solo las propias | RF-4.2, RF-4.3, RF-4.6. |
| `POST /citas/` | POST | Autenticado | Barbero → cliente señalado vía `usuario_id`; Usuario → propio | RF-4.4, RF-4.5. Contrato body en §3.3. |
| `PATCH /citas/{cita_id}` | PATCH | Autenticado | Barbero → cualquier; Usuario → solo las propias | RF-4.3. |
| `DELETE /citas/{cita_id}` | DELETE | Autenticado | Barbero → cualquier; Usuario → solo las propias | RF-4.3. |
| `GET /usuarios/` | GET | Autenticado | Barbero → todos; Usuario → solo el propio | RF-4.7. |
| `POST /usuarios/` | POST | Barbero | — | Alta de usuario con rol `usuario`; el registro público de clientes se centraliza en `POST /auth/register` (RF-1). |
| `PATCH /usuarios/{usuario_id}` | PATCH | Autenticado | Barbero → cualquier; Usuario → solo el propio (sin gestión de rol) | RF-4.7. |
| `DELETE /usuarios/{usuario_id}` | DELETE | Barbero | — | Baja; elimina también las citas y sesiones asociadas. Solo barbero; el auto-borrado no está contemplado. |

## 3. Contrato de API (Constitución IV)

Cada endpoint declara su request, response, `response_model` y status codes. Los errores se devuelven con `HTTPException` y mensajes en español.

### 3.1 Endpoints de autenticación

#### `POST /auth/register`

- **Autenticación:** pública (sin token).
- **Request:** JSON `RegisterRequest` — schema de **entrada** que incluye `contrasena` (con hash bcrypt, RF-1.2).
  - `nombre`: string, obligatorio, longitud 2–100.
  - `numero`: string, obligatorio, longitud 7–20.
  - `correo`: string, obligatorio, formato email.
  - `contrasena`: string, obligatorio, longitud mínima 8 y máxima 72 bytes.
- **Response:** `201 Created` — `UsuarioResponse` — schema de **salida** que **no incluye la contraseña** (no hereda de un schema que la contenga; campos: `id`, `nombre`, `numero`, `correo`, `rol` = `usuario`). Sin token en la respuesta.
- **Errores:** `400` "El correo ya está registrado."; `422` validación Pydantic fallida.
- **Contrato request/response:** el request de `POST /auth/register` es `RegisterRequest` (con `contrasena`); el response es `UsuarioResponse` (sin `contrasena`).

#### `POST /auth/login`

- **Autenticación:** pública (sin token).
- **Request:** JSON `LoginRequest`: `correo` (email), `contrasena` (string, obligatoria, mínima 1).
- **Response:** `200 OK` — `AuthResponse`: `{ "token": "<token opaco>", "usuario": <UsuarioResponse> }`.
- **Errores:** `401` "Credenciales inválidas."; `422` validación Pydantic fallida.

#### `POST /auth/logout`

- **Autenticación:** Bearer (`Authorization: Bearer <token>`).
- **Request:** body vacío.
- **Response:** `200 OK` — `LogoutResponse`: `{ "message": "Sesión cerrada correctamente" }`.
- **Errores:** `401` token ausente/inválido/expirado.

### 3.2 Endpoints protegidos

Resumen de response y status codes:

| Endpoint | Response principal | Status codes |
| --- | --- | --- |
| `GET /servicios/` | `200` — list `ServicioResponse` | `200` |
| `POST /servicios/` | `201` — `ServicioResponse` | `201`, `400`, `401`, `403`, `422` |
| `PATCH /servicios/{servicio_id}` | `200` — `ServicioResponse` | `200`, `400`, `401`, `403`, `404`, `422` |
| `DELETE /servicios/{servicio_id}` | `200` — `{message}` | `200`, `400`, `401`, `403`, `404`, `409` |
| `GET /citas/` | `200` — list `CitaResponse` | `200`, `400`, `401`, `422` |
| `POST /citas/` | `201` — `CitaResponse` | `201`, `400`, `401`, `403`, `422` |
| `PATCH /citas/{cita_id}` | `200` — `CitaResponse` | `200`, `400`, `401`, `403`, `404`, `422` |
| `DELETE /citas/{cita_id}` | `200` — `{message}` | `200`, `401`, `403`, `404` |
| `GET /usuarios/` | `200` — list `UsuarioResponse` | `200`, `401` |
| `POST /usuarios/` | `201` — `UsuarioResponse` | `201`, `400`, `401`, `403`, `422` |
| `PATCH /usuarios/{usuario_id}` | `200` — `UsuarioResponse` | `200`, `400`, `401`, `403`, `404`, `422` |
| `DELETE /usuarios/{usuario_id}` | `200` — `{message}` | `200`, `401`, `403`, `404`, `409` |

#### Contrato de `POST /citas/` bajo autenticación (RF-4.4 / RF-4.5)

- **Body:** `CitaCreate` autenticado.
  - `usuario_id`: string (UUID), obligatorio — identificador del cliente de la cita.
  - `servicios_ids`: list[str], obligatorio, `min_length=1`.
  - `fecha_hora`: datetime, obligatorio.
  - `origen`: opcional (`usuario` | `barbero`).
- **Semántica por rol:**
  - **Regla explícita de origen por rol:** el origen por defecto de una cita creada por el solicitante se determina por el rol del usuario autenticado (rol `barbero` → origen por defecto `barbero`; rol `usuario` → origen por defecto `usuario`). Si el solicitante envía un `origen` que no corresponde a su rol (p. ej., un usuario autenticado envía `origen: "barbero"`), el sistema debe devolver `400`.
  - Rol `barbero`: `usuario_id` es el cliente al que se señala la cita; debe existir (si no, `400` "El usuario no está registrado."); el origen por defecto es `barbero`.
  - Rol `usuario`: `usuario_id` debe coincidir con el propio del token (si no, `403`); el origen por defecto es `usuario`.
- **Response:** `201` — `CitaResponse`.
- **Errores:** `400` (usuario no registrado, servicios no registrados/duplicados, solapamiento, cita duplicada, origen inválido); `401`; `403`; `422`.

#### `GET /citas/`

- **Auth:** Bearer. **Rol:** autenticado.
- **Query params:** los definidos en la spec 001 (`fecha_desde`, `fecha_hasta`, `estado`, `usuario_id`, `origen`, `limit`, `offset`).
- **Comportamiento:** barbero → todas las citas (con validación de `usuario_id` inexistente → `400`); usuario → solo las propias; el filtro `usuario_id` se restringe al propio usuario (RF-4.6).
- **Response:** `200` — list `CitaResponse`.

#### `PATCH /usuarios/{usuario_id}`

- **Auth:** Bearer. **Alcance:** barbero → cualquier; usuario → solo el propio (sin gestión de rol).
- **Orden de validaciones:**
  1. `401` sin token.
  2. `404` si el usuario no existe.
  3. `403` si el solicitante con rol `usuario` intenta sobre un registro ajeno o gestionar roles.
  4. `400` si el `rol` enviado no es `usuario`/`barbero` ("El rol debe ser 'usuario' o 'barbero'.") o si el `correo` está en uso.
  5. `200` con `UsuarioResponse`.

## 4. Restricciones y lo que no incluye

- **No incluye** frontend: la gestión de la sesión en localStorage/cookies es responsabilidad del frontend; la API define el contrato.
- **No incluye** reseteo de contraseña ni recuperación de cuenta.
- **No incluye** refresh tokens ni JWT en esta fase (la estrategia elegida es token opaco).
- **No incluye** rate limiting (decisión: fuera de alcance en esta fase).
- Cambios en `models.py` y dependencias requieren aprobación (constitución III); en esta feature el usuario ya aprobó modificar `models.py` y añadir dependencias.
- No cambia los estados de cita ni el solapamiento de horarios (features 001).
- No hay migraciones automáticas: el cambio de esquema exige regenerar la base o migración manual SQL.

## 5. Casos borde y manejo de errores

| Caso | Comportamiento |
| --- | --- |
| Registro con correo duplicado | `400` "El correo ya está registrado." |
| Registro con datos inválidos | `422` (formato correo, contraseña < 8 o > 72 bytes, nombre/número) |
| Registro con datos válidos | `201`, rol `usuario`, response `UsuarioResponse` sin contraseña |
| Login con credenciales inválidas (correo no registrado o contraseña incorrecta) | `401` "Credenciales inválidas." |
| Login con datos inválidos | `422` |
| Login con credenciales válidas | `200` con `AuthResponse` (token + usuario) |
| Logout sin token | `401` |
| Logout con token inválido | `401` "Sesión no válida." |
| Logout con token expirado | `401` "La sesión ha expirado." |
| Logout con token válido | `200` con `LogoutResponse` |
| Acceso a endpoint protegido sin token | `401` "No autenticado." |
| Token expirado al usarlo | `401` "La sesión ha expirado." |
| Token revocado (logout) | `401` "Sesión no válida." |
| Rol insuficiente | `403` |
| Borrado de servicio asociado | `200`; elimina las citas que quedarían sin servicios y actualiza las restantes |
| Borrado de usuario con citas o sesiones | `200`; elimina también sus citas y sesiones asociadas |
| `PATCH /usuarios/{id}` con rol inválido | `400` "El rol debe ser 'usuario' o 'barbero'." |
| Crear cita con `usuario_id` inexistente | `400` "El usuario no está registrado." |
| Crear cita con origen inválido | `400` "El origen debe ser 'usuario' o 'barbero'." |
| Crear cita con solapamiento / duplicada / servicios inválidos | `400` (mensajes existentes de la spec 001) |

## 6. Criterios de aceptación y verificación

Se verifica levantando uvicorn y consultando los endpoints por HTTP real (constitución VI).

### Criterios asociados a RF-1 (registro)

1. `POST /auth/register` con datos válidos → `201` y el usuario queda con rol `usuario`.
2. `POST /auth/register` con correo duplicado → `400`.
3. `POST /auth/register` con datos inválidos → `422`.
4. `POST /auth/register` sin `contrasena` → `422`.

### Criterios asociados a RF-2 (login)

5. `POST /auth/login` con credenciales válidas → `200` con token y datos del usuario.
6. `POST /auth/login` con credenciales inválidas → `401` "Credenciales inválidas."
7. Token con `expires_at` anterior a la hora actual (simulación de la expiración, sin esperar las 24 h): el acceso a un endpoint protegido con ese token → `401`.

### Criterios asociados a RF-3 (logout)

8. `POST /auth/logout` con token válido → `200`; el token queda invalidado.
9. `POST /auth/logout` con token inválido o expirado → `401`.

### Criterios asociados a RF-4 (protección por rol)

10. Acceso a endpoint protegido sin token → `401`.
11. Barbero autenticado `GET /citas/` → `200` con todas las citas.
12. Usuario autenticado `GET /citas/` → `200` con solo sus citas.
13. Usuario autenticado `GET /citas/?usuario_id=<ajeno>` → solo sus citas.
14. Usuario autenticado `POST /citas/` con `usuario_id` ajeno → `403`.
15. Barbero autenticado `POST /citas/` → `201` con origen `barbero`.
16. Usuario autenticado `POST /citas/` → `201` con origen `usuario` y su propio `usuario_id`.
17. `PATCH /citas/{id}` con rol `usuario` sobre una cita ajena → `403`.
18. Endpoints de usuarios con rol no apropiado → `403`: un usuario autenticado con rol `usuario` que acceda a un endpoint reservado a barbero (p. ej. `POST /servicios/`) o gestione el rol de otro usuario en `PATCH /usuarios/{usuario_id}` debe recibir `403`.
19. `GET /usuarios/` con rol `barbero` → todos; con rol `usuario` → solo el propio.
20. `PATCH /usuarios/{usuario_id}`: un usuario autenticado con rol `usuario` solo puede modificar su propio registro, sin gestión de rol → `200`; sobre un registro ajeno → `403`.
21. Barbero autenticado con contraseña puede acceder a endpoints protegidos.

### Criterios asociados a RF-5 (gestión de servicios)

22. `POST`/`PATCH`/`DELETE /servicios/` con rol no `barbero` → `403`.

### Regresiones de la spec 001

23. Los endpoints protegidos mantienen las validaciones de la spec 001 (filtros combinables, orden, solapamiento, estados).

## 7. Cambios de código previstos

| Archivo | Cambio |
| --- | --- |
| `schemas.py` | Añadir `contrasena` a `UsuarioCreate` (schema de entrada); nuevos schemas `LoginRequest`, `AuthResponse`, `LogoutResponse`; ajustar `CitaCreate` si aplica. Nota: `UsuarioCreate` es de entrada y `UsuarioResponse` es de salida sin contraseña. |
| `main.py` | Añadir `POST /auth/register`, `POST /auth/login`, `POST /auth/logout`; dependencias `get_current_user` / control de rol; aplicar protección en citas, usuarios y servicios según la matriz; registrar seguridad Bearer en OpenAPI. |
| `models.py` | **Modificación aprobada por el usuario** (constitución III): añadir `contrasena_hash` a `Usuario` y crear tabla `sesiones`. |
| `pyproject.toml` / `uv.lock` | Añadir dependencia `bcrypt` (aprobada por el usuario). |
| `AGENTS.md` / `memory.md` | Actualizar tras aprobación. |

## 8. Decisiones aprobadas y técnicas

1. **Estrategia de sesión:** token opaco con tabla de sesiones. Se genera con `secrets.token_urlsafe` (256 bits), se almacena como hash SHA-256 en la tabla `sesiones` (`token_hash`, `usuario_id`, `created_at`, `expires_at`) y el logout elimina la fila. TTL: 24 horas. Alternativa descartada: JWT (librería nueva + revocación). Decidida por simplicidad (constitución VII) y por invalidación inmediata.
2. **Hash de contraseña:** `bcrypt` (dependencia aprobada) con `hashpw`/`checkpw`; columna `usuarios.contrasena_hash`. Longitud máxima de contraseña: 72 bytes (límite de bcrypt).
3. **Transporte del token:** Bearer en header `Authorization: Bearer <token>`.
4. **TTL de la sesión:** 24 horas.
5. **Alta de barberos:** vía `PATCH /usuarios/{usuario_id}` con `rol: "barbero"` (soporte existente); no hay alta pública directa.
6. **Rate limiting:** fuera de alcance en esta fase.
7. **Registro y login:** `POST /auth/register` es público y no emite token; `POST /auth/login` emite token.
8. **Asignación de contraseña a barberos:** se elige la Opción A — el `PATCH /usuarios/{usuario_id}` acepta opcionalmente `contrasena` para establecer el hash bcrypt (RF-1.2) al promover a `rol: "barbero"`; sin el campo, la contraseña no se modifica. El barbero con contraseña establecida puede autenticarse en `POST /auth/login` (RF-2) y acceder a endpoints protegidos por rol (RF-4 / RF-5).

## 9. Preguntas abiertas

1. Reseteo de contraseña: fuera de alcance de esta spec.
2. Frontend: manejo del token (memoria/localStorage) — responsabilidad del frontend; la API define el contrato.
