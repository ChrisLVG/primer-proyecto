# Plan — Spec 004: Refactorización interna del backend

## Alcance

Aplicar las fases 1 y 2 del plan aprobado por el usuario. La fase opcional de modelos `response_model` queda fuera de esta spec. No se modificarán `models.py`, `schemas.py`, `database.py`, `pyproject.toml` ni `uv.lock`.

## Archivos y responsabilidades

### Archivos existentes que se modifican

- `src/primer_proyecto/autenticador.py`: constantes de autenticación, hash/verificación de contraseñas, sesión, dependencia y endpoints `/auth`.
- `src/primer_proyecto/main.py`: en la fase 1, delegación a utilidades de autenticación; al final, composición de la aplicación y ruta raíz.
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

## Casos límite y riesgos

- Evitar que los aliases `Annotated` creen errores de sintaxis en endpoints con parámetros `Query` por defecto; `listar_citas` será keyword-only.
- Conservar `datetime` antes de `date` al detectar el tipo en el helper de fechas.
- Ejecutar la validación del propietario y la resolución del rango en el mismo orden que actualmente tiene `listar_citas`.
- Conservar los mensajes particulares de cada endpoint al extraer `_obtener_o_404` y `_exigir_propietario`.
- Las operaciones de borrado permanecen atómicas: el `try/commit/except IntegrityError` continúa dentro de cada endpoint.
- Importar todos los modelos requeridos antes de `metadata.create_all` y evitar ciclos entre utilidades, autenticador y routers.
- La base de datos de pruebas es solo `sqlite://` en memoria; nunca apuntar el servidor de prueba al archivo local.

## Estrategia de validación

- No hay archivos `*test*.py` en el repositorio y `TestClient` no es compatible con el entorno actual.
- Usar scripts de verificación HTTP reproducibles con Uvicorn en loopback y SQLite `:memory:`/`StaticPool`, sin crear artefactos de prueba ni tocar la base local.
- Cubrir registro/login/logout/expiración, acceso público/protegido, usuario y barbero, CRUD relevante, filtros, solapamiento, recalculo de precio y eliminaciones.
- Verificar sintaxis/importación con `uv run --no-sync python -m compileall src/primer_proyecto`; no ejecutar instalaciones.
- La guía SDD recomienda `uv run pytest`, pero no se añadirá un framework ni archivos de prueba fuera del alcance aprobado.

## Cobertura de requisitos

- RF-1 y RF-2: regresión HTTP completa del contrato y de autenticación.
- RF-3: revisión de constantes y comprobaciones de roles/estados.
- RF-4: casos HTTP de rangos de fecha como fecha completa, instante y extremo único.
- RF-5: inspección de dependencias y reglas extraídas sin duplicación.
- RF-6: comprobaciones de credenciales, sesiones, expiración y autorización.
- RF-7: comparación de paths y métodos registrados antes y después.
- RF-8: diff limitado a los archivos permitidos y a los nuevos módulos indicados.
