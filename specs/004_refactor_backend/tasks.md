# Tareas — Spec 004: Refactorización interna del backend

**Estado:** Aprobada; implementación incremental, una tarea por iteración.

## T1 — Centralizar constantes y operaciones de autenticación

**Estado:** ✅ Completada

**Archivos:** `src/primer_proyecto/autenticador.py`, `src/primer_proyecto/main.py`.

**Cambios:** añadir las constantes de rol y duración de sesión; extraer hash/verificación de contraseña, reloj actual y autenticación por correo/contraseña; usar las funciones desde registro, login y rutas de usuario; quitar bcrypt directo de `main.py`; reemplazar literales de rol y dependencias `require_rol` por constantes.

**Validación:** antes y después, HTTP real para registro, credenciales correctas/incorrectas, logout, token expirado, permisos usuario/barbero, y status de los endpoints tocados.

**Aceptación:** se mantienen hashes bcrypt, token SHA-256, TTL de 24 horas, mensajes/status y flujo HTTP; no se introduce dependencia circular.

## T2 — Consolidar helpers de fecha y filtros

**Estado:** ✅ Completada

**Archivos:** `src/primer_proyecto/main.py`.

**Cambios:** declarar constantes de estados/orígenes/mensaje; sustituir los cuatro helpers de límite por `_limite_de_fecha`; extraer `_resolver_rango_fechas` y `_validar_filtros_citas`; preservar el orden de filtros y autorización.

**Validación:** HTTP real para fecha exacta, día completo, extremo único, rango invertido, estado/origen inválidos, usuario desconocido, paginación y combinación AND.

**Aceptación:** respuestas idénticas a la línea base y distinción `date | datetime` conservada.

## T3 — Extraer búsqueda y control de propiedad

**Estado:** ✅ Completada

**Archivos:** `src/primer_proyecto/main.py`.

**Cambios:** añadir `_obtener_o_404` y `_exigir_propietario`; aplicarlos a las rutas de usuario/cita indicadas, conservando el mensaje específico y el orden 404→403.

**Validación:** HTTP real para IDs inexistentes, propietario y usuario ajeno en PATCH/DELETE/POST.

**Aceptación:** mismos códigos, textos de error y precedencia que antes.

## T4 — Extraer reglas internas de endpoints largos

**Estado:** ✅ Completada

**Archivos:** `src/primer_proyecto/main.py`.

**Cambios:** extraer validación de filtros, duplicidad de cita, origen de cita, validación de nueva fecha, dependencias de usuario y retirada de servicio. Mantener el `try/commit/except IntegrityError` de ambas eliminaciones dentro de su endpoint.

**Validación:** HTTP real para duplicados, origen, fechas ocupadas/pasadas, solapamientos, borrado de usuario/servicio y recálculo de precios.

**Aceptación:** reglas y transacciones conservan resultados y mensajes.

## T5 — Tipar dependencias con aliases Annotated

**Estado:** ✅ Completada

**Archivos:** `src/primer_proyecto/autenticador.py`, `src/primer_proyecto/main.py`.

**Cambios:** definir `SesionDB`, `UsuarioActual` y `SoloBarbero`; migrar parámetros de rutas, dejando `listar_citas` keyword-only; usar `_barbero` donde el valor solo fuerza la autorización.

**Validación:** importar/compilar la aplicación y consultar por HTTP rutas públicas, autenticadas y exclusivas de barbero.

**Aceptación:** FastAPI resuelve correctamente todas las dependencias y no cambia la matriz de permisos.

## T6 — Extraer utilidades compartidas

**Estado:** ✅ Completada

**Archivos:** crear `src/primer_proyecto/utilidades.py`; modificar `main.py` y `autenticador.py`.

**Cambios:** mover constantes de dominio y helpers de fechas/citas/búsqueda/propiedad; hacer públicos los nombres necesarios entre módulos; mover constantes de rol desde `autenticador.py` a `utilidades.py` e importarlas allí.

**Validación:** importación de módulos y rutas con SQLite en memoria; regresión HTTP con 12/12 verificaciones aprobadas (roles, permisos, servicio, cita, precio, lectura, filtro de fecha y estado inválido); `git diff --check` sin errores.

**Aceptación:** `utilidades.py` no importa autenticación ni routers; no hay ciclos ni reglas duplicadas.

## T7 — Crear routers de usuarios y servicios

**Estado:** ✅ Completada

**Archivos:** enmendar `docs/constitution.md` a versión 1.3.0; crear `routers/__init__.py`, `routers/usuarios.py`, `routers/servicios.py`; modificar `main.py`.

**Cambios:** antes de mover las rutas, actualizar la sección II para permitir routers de dominio. Mover cada endpoint con paths relativos y prefijos `/usuarios` y `/servicios`; montar ambos routers desde `main.py` y retirar de allí las rutas movidas.

**Validación:** 28 verificaciones HTTP aprobadas para usuarios y servicios con Uvicorn y SQLite en memoria; OpenAPI confirma los mismos métodos y URLs; AST de los módulos modificados/nuevos válido; `git diff --check` limpio.

**Aceptación:** los paths públicos se mantienen exactamente; cada router tiene su prefijo y etiquetas.

## T8 — Crear router de citas

**Estado:** ✅ Completada

**Archivos:** crear `routers/citas.py`; modificar `main.py`.

**Cambios:** mover las rutas de citas y usar los helpers/aliases ya definidos; registrar el router desde `main.py` y retirar las rutas inline para evitar duplicados; preservar orden de filtros y controles de propietario.

**Validación:** regresión HTTP con SQLite en memoria para autenticación, permisos por rol/propietario, filtros de citas y fechas, paginación, creación, duplicados, actualización de estado/fecha/servicios, rollback por solapamiento y eliminación; OpenAPI conserva rutas y métodos.

**Aceptación:** el contrato y comportamiento de todas las rutas de citas coincide con la línea base.

## T9 — Componer la aplicación y actualizar documentación

**Estado:** ✅ Completada

**Archivos:** modificar `main.py`, `AGENTS.md`, `memory.md`.

**Cambios:** `main.py` conservará creación de tablas, app FastAPI, endpoint raíz e inclusiones de auth/usuarios/servicios/citas; actualizar la estructura documentada y decisiones de memoria.

**Validación:** carga del entry point `src.primer_proyecto.main:app` y `GET /` por HTTP (200); OpenAPI conserva los 10 paths y métodos esperados; memoria en 31/50 líneas. La regresión HTTP integral queda para T10.

**Aceptación:** no se cambia el comando de Uvicorn ni se toca configuración del paquete.

## T10 — Ejecutar regresión HTTP final

**Estado:** ✅ Completada

**Archivos:** ninguno.

**Cambios:** ninguno; ejecutar validación de extremo a extremo con Uvicorn y SQLite en memoria.

**Validación:** 32 grupos de verificaciones HTTP/OpenAPI aprobaron auth, permisos, status y JSON, CRUD de usuarios/servicios/citas, filtros, fechas, solapamientos, recálculo de precios, eliminaciones y conservación de sesiones; además se verificaron logout y expiración de sesión. No hubo HTTP 500; todas las pruebas utilizaron SQLite en memoria.

**Aceptación:** todos los casos aprobados pasan y el archivo SQLite local no se utiliza.

## Extensión aprobada — Modularización de autenticación

**Aprobada:** 2026-11-02. Mantiene T1-T10 como trabajo histórico completado y agrega las tareas siguientes.

## T11 — Separar autenticación por responsabilidad

**Estado:** ⏳ Pendiente

**Archivos:** completar `src/primer_proyecto/auth/{__init__,seguridad,sesiones,dependencias,routers}.py`; actualizar `src/primer_proyecto/main.py`, `src/primer_proyecto/routers/{usuarios,servicios,citas}.py`, `AGENTS.md` y `memory.md`; retirar el antiguo `src/primer_proyecto/autenticador.py` ya eliminado en el WIP.

**Cambios:** dejar seguridad de contraseñas/tokens en `seguridad.py`, ciclo de sesiones en `sesiones.py`, dependencias/aliases en `dependencias.py` y endpoints en `routers.py`. Publicar desde `auth` los nombres que necesita la app y migrar todas las importaciones internas. Mantener un solo router `/auth`, mismos mensajes/status, hash bcrypt/SHA-256 y TTL de 24 h; no introducir ciclos ni una app FastAPI paralela.

**Validación:** análisis de sintaxis/imports; cargar `src.primer_proyecto.main:app`; confirmar por OpenAPI que cada endpoint `/auth` se registra exactamente una vez y que usuarios/servicios/citas siguen importando sus dependencias.

**Aceptación:** cada módulo tiene una responsabilidad, no queda referencia interna a `autenticador.py` y no se cambia el contrato HTTP.

## T12 — Regresión HTTP de todos los endpoints

**Estado:** ⏳ Pendiente

**Archivos:** ninguno; actualizar `tasks.md`, `spec.md` y `memory.md` con los resultados.

**Cambios:** ninguno; validar la app completa mediante Uvicorn y SQLite en memoria sin tocar la base local.

**Validación:** recorrer todos los paths/métodos de OpenAPI y probar autenticación/sesiones, permisos por rol/propietario, CRUD de usuarios/servicios/citas, filtros y fechas, solapamiento, precio, borrado de dependencias, status codes, JSON y mensajes representativos; confirmar ausencia de HTTP 500.

**Aceptación:** todos los endpoints del proyecto responden con el contrato esperado; el spec queda implementado solo tras superar regresión y análisis de imports.
