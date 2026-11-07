# Plan — Spec 004: Refactorización interna del backend

## Alcance

T1-T10 completaron la extracción de utilidades y routers de dominio. La extensión aprobada completa la separación modular de autenticación y ejecuta una regresión HTTP para todos los endpoints. La fase opcional de modelos `response_model` queda fuera de esta spec. No se modificarán `models.py`, `schemas.py`, `database.py`, `pyproject.toml` ni `uv.lock`.

## Archivos y responsabilidades

### Archivos existentes que se modifican

- `src/primer_proyecto/autenticador.py`: constantes de autenticación, hash/verificación de contraseñas, sesión, dependencia y endpoints `/auth`.
- `src/primer_proyecto/auth/seguridad.py`: hash/verificación bcrypt, hash SHA-256 de tokens y comprobación de credenciales.
- `src/primer_proyecto/auth/sesiones.py`: creación, validación, expiración y cierre de sesiones; TTL y reloj común.
- `src/primer_proyecto/auth/dependencias.py`: `HTTPBearer`, usuario actual, autorización por rol y aliases de dependencias.
- `src/primer_proyecto/auth/routers.py`: endpoints de registro, login y logout en el router `/auth`.
- `src/primer_proyecto/auth/__init__.py`: interfaz pública para el router y dependencias que consumen `main.py` y los routers de dominio.
- `src/primer_proyecto/main.py`: en la fase 1, delegación a utilidades de autenticación; al final, composición de la aplicación y ruta raíz.
- `src/primer_proyecto/routers/{usuarios,servicios,citas}.py`: actualizar imports de aliases para consumir el paquete `auth`.
- `docs/constitution.md`: enmienda a la sección II para permitir que `main.py` componga routers de dominio separados.
- `AGENTS.md`: actualizar la estructura del backend y las responsabilidades de los módulos nuevos.
- `memory.md`: registrar avances y decisiones sin superar 50 líneas.

### Archivos nuevos autorizados

- `src/primer_proyecto/utilidades.py`: constantes de dominio y reglas compartidas de citas, fechas, búsqueda y propiedad.
- `src/primer_proyecto/routers/__init__.py`: paquete de routers.
- `src/primer_proyecto/routers/usuarios.py`: rutas del dominio de usuarios.
- `src/primer_proyecto/routers/servicios.py`: rutas del dominio de servicios.
- `src/primer_proyecto/routers/citas.py`: rutas del dominio de citas.

### Estructura objetivo

```text
src/primer_proyecto/
├── autenticador.py
├── main.py
├── utilidades.py
├── auth/
│   ├── __init__.py
│   ├── seguridad.py
│   ├── sesiones.py
│   ├── dependencias.py
│   └── routers.py
└── routers/
    ├── __init__.py
    ├── usuarios.py
    ├── servicios.py
    └── citas.py
```

`main.py` conservará `create_all`, la instancia `FastAPI`, el endpoint raíz y la inclusión de los cuatro routers: autenticación, usuarios, servicios y citas.

## Lógica y dependencias

- En la fase 1, introducir constantes de rol en `autenticador.py` y constantes de estados/orígenes en `main.py`; consolidar autenticación, resolución de fechas, búsquedas, permisos y fragmentos de endpoints sin cambiar su orden.
- En la fase 2, mover constantes de dominio y auxiliares a `utilidades.py`. `utilidades.py` no importará `autenticador.py`; `autenticador.py` podrá importar las constantes de rol desde `utilidades.py` sin crear un ciclo.
- En la extensión T11, completar el paquete `auth` existente y sustituir las referencias internas a `autenticador.py`. Las dependencias siguen esta dirección: `routers.py` → `dependencias.py`/`sesiones.py`/`seguridad.py`; `dependencias.py` → `sesiones.py`; `sesiones.py` → `seguridad.py`. `seguridad.py` no importa routers ni dependencias. El `__init__.py` exporta únicamente la interfaz necesaria y no crea otra aplicación.
- Mantener una sola definición de `DURACION_SESION`, `security` y router de autenticación; colocar el reloj de sesiones en `sesiones.py` para evitar ciclos.
- Cada módulo de rutas creará un `APIRouter` con prefijo y etiquetas de su dominio. Sus paths relativos conservarán los paths públicos existentes.
- `main.py` importará los routers y los registrará con `app.include_router(...)`.
- Las dependencias se seguirán inyectando con `Depends(get_db)` o aliases `Annotated` en los endpoints.

## Algoritmo de extracción

1. Fijar una línea base de respuestas y permisos mediante HTTP real y SQLite en memoria.
2. Refactorizar autenticación y helpers dentro de los dos módulos actuales; validar los mismos flujos.
3. Extraer helpers de citas y fechas a un módulo sin dependencias de routers.
4. Enmendar la constitución antes de distribuir las rutas del dominio.
5. Mover cada grupo de rutas a su `APIRouter`, conservando dependencias, orden de validaciones y transacciones.
6. Reducir `main.py` a composición y ruta raíz.
7. Repetir la regresión HTTP y comparar rutas, códigos, JSON, errores y permisos con la línea base.
8. Reubicar la autenticación en `auth/`, actualizar consumidores y verificar imports/ciclos.
9. Ejecutar por HTTP cada endpoint del proyecto, incluidos los tres endpoints `/auth`, sobre SQLite en memoria; comprobar OpenAPI, respuestas, permisos y ausencia de HTTP 500.

## Casos límite y riesgos

- Evitar que los aliases `Annotated` creen errores de sintaxis en endpoints con parámetros `Query` por defecto; `listar_citas` será keyword-only.
- Conservar `datetime` antes de `date` al detectar el tipo en el helper de fechas.
- Ejecutar la validación del propietario y la resolución del rango en el mismo orden que actualmente tiene `listar_citas`.
- Conservar los mensajes particulares de cada endpoint al extraer `_obtener_o_404` y `_exigir_propietario`.
- Las operaciones de borrado permanecen atómicas: el `try/commit/except IntegrityError` continúa dentro de cada endpoint.
- Importar todos los modelos requeridos antes de `metadata.create_all` y evitar ciclos entre utilidades, autenticador y routers.
- Evitar que `auth.__init__` cause importación circular entre routers y dependencias; los routers de dominio importan aliases desde el paquete solo después de definir sus exports de forma segura.
- No conservar lógica duplicada ni router paralelo al sustituir `autenticador.py`; el router de auth debe montarse una vez.
- La base de datos de pruebas es solo `sqlite://` en memoria; nunca apuntar el servidor de prueba al archivo local.

## Estrategia de validación

- No hay archivos `*test*.py` en el repositorio y `TestClient` no es compatible con el entorno actual.
- Usar scripts de verificación HTTP reproducibles con Uvicorn en loopback y SQLite `:memory:`/`StaticPool`, sin crear artefactos de prueba ni tocar la base local.
- Cubrir registro/login/logout/expiración, acceso público/protegido, usuario y barbero, CRUD relevante, filtros, solapamiento, recalculo de precio y eliminaciones.
- Verificar sintaxis/importación con `uv run --no-sync python -m compileall src/primer_proyecto`; no ejecutar instalaciones.
- Para T12, levantar Uvicorn apuntando al engine SQLite en memoria reemplazado antes de importar `main`; probar cada path/método listado en OpenAPI y casos relevantes de registro/login/logout, roles, CRUD, filtros, solapamiento, precios y cascadas.
- La guía SDD recomienda `uv run pytest`, pero no se añadirá un framework ni archivos de prueba fuera del alcance aprobado.

## Cobertura de requisitos

- RF-1 y RF-2: regresión HTTP completa del contrato y de autenticación.
- RF-3: revisión de constantes y comprobaciones de roles/estados.
- RF-4: casos HTTP de rangos de fecha como fecha completa, instante y extremo único.
- RF-5: inspección de dependencias y reglas extraídas sin duplicación.
- RF-6: comprobaciones de credenciales, sesiones, expiración y autorización.
- RF-7: comparación de paths y métodos registrados antes y después.
- RF-8: diff limitado a los archivos permitidos y a los nuevos módulos indicados.
- RF-9 y RF-10: inspección de la dirección de imports y regresión HTTP de todos los endpoints con status/cuerpos, permisos y sesiones.
