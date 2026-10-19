# Sitio web para una barberia

- Sitio web para la gestion de informacion de clientes, servicios y citas para una barberia, muestra al usuario informacion de todos los servicios, permite al usuario gestionar sus citas agenciadas, permite al usuario contactar al barbero via whatsapp para la cita y permite al barbero visualizar todas las citas registradas en el sistema.

## Stack Tecnologico

**Backend:** Lenguaje Principal: Python 3.12, Framework Web (API REST): FastAPI, Validación de Datos y Serialización: Pydantic (v2), ORM (Object-Relational Mapping): SQLAlchemy (v2), Base de Datos Relacional: SQLite (`citas_barberia.db`, en `src/primer_proyecto/`), Servidor ASGI: Uvicorn, Identificadores Únicos: UUID (Universally Unique Identifier - uuid4), Documentación Automática e Interactiva: OpenAPI / Swagger UI.

**Frontend:** Lenguaje Base: JavaScript (ES6+), Librería / Framework de Interfaz (UI): React.js, Cliente HTTP (Consumo de la API): Axios, Framework de Estilos (Diseño UI/UX): Tailwind CSS, Enrutamiento del Cliente: React Router, Manejo de Sesión y Autenticación: LocalStorage / Cookies HttpOnly.

## Estructura del proyecto

- `pyproject.toml`: Configuración del proyecto Python y dependencias de uv (FastAPI, Uvicorn).
- `README.md`: Documentación general del proyecto.
- `.python-version`: Versión de Python especificada para el entorno.
- `.gitignore`: Archivos excluidos de Git (`.venv/`, `__pycache__/`, `*.db`).
- `src/primer_proyecto/`: Código fuente de la aplicación.
- `AGENTS.md`: Reglas y guardarraíles del repositorio para el agente de IA.
- `main.py`: Punto de entrada principal e itineración de rutas de la API FastAPI.
- `database.py`: Configuración de SQLAlchemy y gestión de sesiones de base de datos.
- `models.py`: Modelos ORM de la base de datos.
- `schemas.py`: Esquemas Pydantic para validación de datos de entrada y salida.
- `memory.md`: Bitácora de decisiones y estado del proyecto (máx. 50 líneas).

## Comandos principales

- `uv run uvicorn src.primer_proyecto.main:app --reload --no-access-log`: Iniciar el servidor de desarrollo. Requiere CWD en la raíz del repo (la ruta de SQLite es relativa).
- `uv run primer-proyecto`: Alternativa al anterior, definida en `[project.scripts]`; usa `primer_proyecto.main` (el atributo `main` de `__init__.py`). Si mueves `main()`, actualiza `pyproject.toml`.

## Modelo de datos

- `usuarios`: antes era `clientes`. Unifica al cliente que agenda y al barbero. Campo `rol` (`'usuario'` | `'barbero'`) con default `'usuario'`.
- `servicios`: nombre, precio, duracion_minutos.
- `citas`: `usuario_id` (antes `cliente_id`), `fecha_hora`, `estado`, `origen` (`'usuario'` | `'barbero'`), `precio_total`.
- `cita_servicio`: **tabla intermedia** N:M entre citas y servicios, con clave primaria compuesta `(cita_id, servicio_id)` que impide repetir el mismo servicio en una cita. Una cita puede incluir varios servicios.
- `Cita.origen` es un **snapshot**, no un campo derivado: se escribe al crear la cita y nunca se recalcula a partir del `rol` actual del usuario.
- `Cita.precio_total` está **desnormalizado** y se recalcula en cada escritura: al crear cita, al cambiar sus servicios, y al cambiar el precio de un servicio.
- En los modelos, la clase de la tabla intermedia es `CitaServicio`; `models.cita_servicio` NO existe (el nombre de la tabla no es un atributo del módulo). Usa `models.CitaServicio` en las consultas.

## Rutas de la API

- `GET /`, `GET|POST /usuarios/`, `PATCH|DELETE /usuarios/{usuario_id}`
- `GET|POST /servicios/`, `PATCH|DELETE /servicios/{servicio_id}`
- `GET|POST /citas/`, `PATCH|DELETE /citas/{cita_id}`
- `GET /citas/?origen=usuario|barbero`: filtra las citas por origen. Sin el parámetro devuelve todas. Un valor distinto de esos dos da `400`.
- `GET /citas/?fecha_desde=&fecha_hasta=`: filtra por rango de fechas. Se aceptan `YYYY-MM-DD` (cubre el día completo) o `YYYY-MM-DDTHH:MM:SS` (instante exacto). Si solo se envía uno de los dos, se filtra ese día completo. Rango invertido da `400`.
- `GET /citas/?estado=pendiente|confirmada|cancelada|terminada`: filtra por estado. Cualquier otro valor da `400`.
- `GET /citas/?usuario_id=<id>`: filtra por usuario. Un usuario inexistente da `400`; uno válido sin citas devuelve `[]`.
- `GET /citas/?limit=&offset=`: paginación (`limit` 1-500, default 100; `offset` ≥ 0, default 0). Fuera de rango da `422`.
- Todos los filtros de `GET /citas/` son opcionales y se combinan con AND. El orden es `fecha_hora ASC, id ASC` (el `id` desempata para que la paginación sea estable).
- Los borrados de usuario/servicio con citas asociadas devuelven `409`.

## Solapamiento de horarios (implementado)

- Una cita ocupa el intervalo `[inicio, inicio + suma de duraciones)`. Dos citas se solapan si `(inicio_nuevo < fin_existente) Y (inicio_existente < fin_nuevo)`.
- Se valida al **crear** y al **actualizar** una cita. Al actualizar, la propia cita se excluye de la comparación.
- La duración total se **calcula en memoria** sumando `duracion_minutos` de los servicios; no se almacena en la tabla `citas`.
- Solo bloquean las citas **activas** (`pendiente` o `confirmada`). Las `cancelada` y `terminada` liberan el hueco.
- El intervalo es **abierto por la derecha**: una cita que termina a las 10:30 no bloquea otra que empiece a las 10:30.
- Solo se valida si la cita cambia de **fecha** o de **servicios**. Un cambio de `estado` no altera su intervalo, así que no se comprueba.
- **Aceptación de riesgo:** si cambia la duración de un servicio, las citas existentes **no** se revalidan (el precio sí se recalcula). Las citas ya creadas conservan su validez; solo las nuevas usan la nueva duración.

## Estados de cita

Los cuatro valores válidos son `pendiente`, `confirmada`, `cancelada` y `terminada`. Se validan **manualmente en el endpoint** para devolver `400` (un `Literal` de Pydantic devolvería `422`). `terminada` se marca manualmente vía `PATCH /citas/{id}`; no hay automatismo por fecha.

## Base de datos y esquema

- **No hay Alembic ni migraciones.** `main.py` ejecuta `models.Base.metadata.create_all(bind=engine)` al importar, y eso **solo crea tablas faltantes: no altera las existentes ni las renombra**. Para cambiar el esquema hay dos caminos: regenerar la base (borrar el `.db` y arrancar, **perdiendo todos los datos**) o migrar a mano con SQL.
- `database.py` define la URL como `sqlite:///./src/primer_proyecto/citas_barberia.db`, **relativa al CWD**: arrancar desde otro directorio crea una segunda base vacía.
- Los `ondelete="CASCADE"` no surten efecto en SQLite salvo que se active `PRAGMA foreign_keys=ON`, que SQLAlchemy no emite por defecto.
- `fastapi.testclient.TestClient` no funciona (starlette 1.6.0 exige `httpx2`, no instalado). Verifica los cambios arrancando uvicorn y consultando los endpoints.
- **Gotcha de Pydantic en los query params de fecha:** la anotación debe ser `date | datetime` (en ese orden). Con `datetime | date`, Pydantic parsea `"2026-12-01"` como `datetime` a medianoche y se pierde la distinción entre "fecha sin hora" (día completo) e "instante exacto" que exige la API.

## Convenciones de codigo y estilo

- Seguir convención PEP 8: `snake_case` para funciones/rutas y `PascalCase` para clases.
- Usar Type Hints explícitos de Python 3.12+ (ej. `list[str]`, `str | None`).
- Redactar comentarios y docstrings en español.
- Usar `ConfigDict(from_attributes=True)` en los esquemas Pydantic de respuesta.
- NUNCA mezcles modelos de SQLAlchemy (`models.py`) con esquemas de validación Pydantic (`schemas.py`).
- Inyectar la sesión de base de datos en los endpoints de `main.py` usando únicamente `Depends(get_db)`.
- Retornar errores de negocio mediante `HTTPException` de FastAPI (`400`, `404`, `422`).
- Ejecutar `db.rollback()` explícito en bloques `try/except` ante fallos de escritura en SQLite.

## Limites y prohibiciones (Lo que NO debes hacer)

- NUNCA crees ni elimines archivos o carpetas nuevas sin proponérselo al usuario y obtener confirmación explícita.
- NUNCA intentes leer, inspeccionar o modificar directorios o archivos ignorados (`.venv/`, `__pycache__/`, archivos `.db` o `.lock`).
- NUNCA ejecutes comandos para instalar librerías (`uv add`, `pip install`) ni modifiques `pyproject.toml` sin aprobación previa del usuario.
- NUNCA alteres los modelos ORM de SQLAlchemy (`models.py`) ni cambies la estructura de las tablas sin la aprobación previa del usuario y confirmando los requerimientos de la base de datos.
- NUNCA ejecutes scripts o comandos que borren o reinicien los datos de la base de datos local (`citas_barberia.db`) a menos que el usuario lo solicite explícitamente.
- NUNCA reescribas o elimines funciones existentes que estén operativas; realiza únicamente cambios incrementales y modularizados.
- NUNCA dupliques lógica de negocio o utilidades que ya existan en otros archivos del proyecto.
- NUNCA ejecutes comandos destructivos en la terminal (ej. `rm`, `del`, detención de procesos globales) sin la aprobación previa del usuario.

## Flujo de trabajo, memoria y SDD

- Al planificar o especificar nuevas funcionalidades, consulta obligatoriamente `docs/constitution.md`
- Antes de iniciar una tarea, lee `memory.md` para conocer el estado actual y las decisiones previas.
- Al finalizar cada tarea, actualiza `memory.md` resumiendo las modificaciones realizadas, aprendizajes y próximos pasos.
