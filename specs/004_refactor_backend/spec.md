# Spec 004 — Refactorización interna del backend

Estado: implementada

## Contexto y objetivo

Preparar el backend para el desarrollo del frontend mediante una organización más legible y modular de la autenticación y las rutas de usuarios, servicios y citas, sin cambiar el comportamiento observable de la API.

## Usuarios

- Personas que consumen la API desde el frontend.
- Barberos que administran usuarios, servicios y citas.
- Desarrolladores que mantienen el backend.

## Historias de usuario

- HU-1. Como consumidor de la API, quiero conservar las rutas, respuestas, errores y permisos actuales para que la reorganización interna no rompa el frontend.
- HU-2. Como desarrollador, quiero localizar con claridad las reglas de autenticación, fechas y citas para mantenerlas sin duplicación.
- HU-3. Como desarrollador, quiero que cada grupo de rutas tenga una responsabilidad definida para facilitar su evolución.

## Requisitos funcionales

- RF-1: CUANDO se refactorice un módulo, EL SISTEMA conserva rutas, métodos HTTP, campos JSON, códigos de éxito y error, mensajes y reglas de autorización vigentes.
- RF-2: CUANDO se valide una petición con más de un error posible, EL SISTEMA conserva el orden actual de validación y el error que prevalece.
- RF-3: EL SISTEMA centraliza nombres de roles, estados, orígenes, duración de sesión y mensajes repetidos en constantes apropiadas.
- RF-4: CUANDO se resuelva un filtro de fechas, EL SISTEMA conserva la distinción entre fecha de día completo e instante exacto, incluida la normalización actual de zonas horarias.
- RF-5: CUANDO una regla de dominio sea reutilizada por varias rutas, EL SISTEMA la implementa una sola vez y permite que las rutas deleguen en ella.
- RF-6: EL SISTEMA conserva los mecanismos actuales de autenticación, contraseñas, sesiones y autorización por rol.
- RF-7: CUANDO se separen las rutas, EL SISTEMA conserva sus URLs públicas e incluye los routers desde una única aplicación FastAPI.
- RF-8: Durante esta refactorización, EL SISTEMA no modifica modelos, tablas, esquemas Pydantic, dependencias ni configuración del paquete.

## Requisitos no funcionales

- La base de datos local y sus datos no se reinician ni se modifican durante la verificación.
- La validación de regresión utiliza HTTP real con Uvicorn y una base SQLite temporal en memoria.
- Los módulos mantienen tipado explícito, nombres y docstrings en español, y dependencias sin ciclos.

## Casos límite

- Una fecha enviada sin hora cubre el día completo; un datetime enviado con ambos extremos conserva el instante exacto.
- Si solo se envía un extremo del rango, se cubre el día completo de ese extremo.
- Los errores 401/403/404/400 conservan el orden y los mensajes actuales.
- La eliminación de usuarios o servicios mantiene la atomicidad existente y no mueve el `try/commit/except IntegrityError` fuera de su endpoint.
- El parámetro de la dependencia de barbero puede no usarse en la función de ruta, pero la dependencia debe seguir ejecutándose.
- El filtro de citas conserva el límite de paginación, el orden cronológico y el desempate por identificador.

## Fuera de alcance

- Cambios funcionales o de contrato HTTP.
- Modificaciones de `models.py`, `schemas.py`, `database.py`, `pyproject.toml` o `uv.lock`.
- Migraciones de base de datos.
- La fase opcional de añadir modelos de respuesta explícitos a endpoints existentes; podrá tratarse como una tarea separada.

## Criterios de finalización

- Los grupos de rutas de usuarios, servicios y citas se encuentran en routers independientes y mantienen las URLs actuales.
- `main.py` compone la aplicación, registra la creación actual de tablas e incluye los routers.
- `autenticador.py` centraliza las rutas y dependencias de autenticación, constantes de rol y operaciones comunes de credenciales/sesión.
- Las funciones auxiliares consolidadas mantienen los errores y el orden de validación definidos en la implementación anterior.
- La regresión HTTP confirma status codes, contratos, permisos y reglas principales sin errores HTTP 500.

## Dudas abiertas

- Ninguna para el alcance aprobado.
