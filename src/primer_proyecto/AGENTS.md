# AGENTS.md

API con FastAPI + SQLAlchemy 2.0 + SQLite para un sistema de citas de salón de uñas ("Angi Nails").
Código pequeño, plano y de un solo servicio. La mayor parte de la fricción está en el cableado, no en
la lógica de negocio.

## Estructura: la app real está en la raíz del repo, no en `src/`

- Los módulos que funcionan son **en la raíz**: `main.py`, `models.py`, `database.py`, `shcemas.py`,
  importados como **nombres de primer nivel** (`import main`, `import shcemas`), no como paquete.
- `src/primer_proyecto/` es andamiaje de `uv init` sin tocar: `__init__.py` es un stub de ejemplo.
  `.venv\Lib\site-packages\primer_proyecto.pth` agrega `src` al `sys.path`, así que
  `import primer_proyecto` siempre resuelve al stub y nunca a la app.
- Por eso `[project.scripts] primer-proyecto = "primer_proyecto:main"` solo imprime
  "Hello from primer-proyecto!". **No** es una forma de ejecutar la app. No lo sugieras.

## Ejecutar

```bash
uv run --frozen uvicorn main:app --reload --port 8000
```

- El **CWD debe ser la raíz del repo**. Tanto la resolución de módulos como la ruta de SQLite son
  relativas al CWD.
- Documentación interactiva en `/docs`.

## Crítico: SQLAlchemy está instalado pero NO declarado

`pyproject.toml` solo lista `fastapi` y `uvicorn`. `sqlalchemy==2.0.52` y `greenlet` están presentes
en `.venv` pero ausentes de `pyproject.toml` **y** de `uv.lock`.

`uv sync` los desinstala y rompe todos los imports:

```
$ uv sync --dry-run
Would uninstall 3 packages
 - greenlet==3.5.5
 - pip==26.2.1
 - sqlalchemy==2.0.52
```

Prefiere `uv run --frozen`. Si el sync es inevitable, declara la dependencia primero:
`uv add "sqlalchemy>=2.0"`.

## Base de datos

- `database.py:5` tiene hardcodeado `sqlite:///./citas_uñas.db`, relativo al CWD y sin carga de
  variables de entorno. Arrancar desde otro directorio crea en silencio una segunda base vacía.
- El nombre del archivo contiene `ñ`, que se muestra como caracteres rotos en la consola de Windows.
  Está versionado en git bajo una ruta no ASCII (`citas_u\303\261as.db`): evita renombrarlo a la
  ligera.
- `main.py:8` llama a `models.Base.metadata.create_all(bind=engine)` **en tiempo de importación**.
  Importar `main` crea/abre la base y las tablas como efecto secundario. No hay Alembic; los cambios
  de esquema requieren borrar el archivo de la base o escribir migraciones a mano.
- Las PK son strings UUID (`models.py`), no enteros. Los parámetros de ruta en `main.py` están
  tipados como `str` para coincidir — manténlos en `str`.

## Trampas de nombres (renombrar es breaking)

- `shcemas.py` está mal escrito (le falta la `c` de `schemas`). Se importa como `shcemas`.
  Renombra el archivo y todos los imports juntos, o déjalo como está.
- Los nombres de las clases de schema son inconsistentes en idioma *y* en mayúsculas: `User`,
  `userresponse`, `service`, `serviceResponse`, `date` (Cita), `dateupdate`, `dateResponse`. Extiende
  los nombres existentes; no "corrijas" las mayúsculas como parte de un cambio de comportamiento.
- Pydantic v2 (2.13.4) está instalado, pero todos los modelos usan el estilo v1
  `class Config: from_attributes = True`. Funciona (deprecado). Usa
  `model_config = ConfigDict(...)` en cualquier modelo nuevo.

## Bugs vivos conocidos — verificados, no los redescubras

- **`POST /clientes/` devuelve 500.** `main.py:25` y `main.py:30-32` leen `cliente.email`, pero
  `shcemas.User` declara `correo`.
  `AttributeError: 'User' object has no attribute 'email'`
- **`PATCH /citas/{cita_id}` devuelve 500 con cualquier `fecha_hora` con zona horaria.** Pydantic
  produce un datetime aware, que se compara contra el `datetime.now()` naive de `main.py:158`:
  `TypeError: can't compare offset-naive and offset-aware datetimes`
  Los clientes deben enviar timestamps locales naive (`2026-12-01T10:00:00`, sin `Z`).
- Verifica los nombres de campo contra el modelo Pydantic en lugar de asumir: `main.py` mezcla
  `correo` (ruta de update, correcta) y `email` (ruta de create, rota).
- `models.py:1` importa `Column`, `Float` y `DateTime` dos veces cada uno. Inofensivo; no lo
  propagues.

## Endpoints

Todas las rutas llevan **barra final**; omitirla produce un redirect 307. No hay autenticación en
ningún lado. **No existen rutas DELETE.**

- `GET /`
- `GET|POST /clientes/`, `PATCH /clientes/{cliente_id}`
- `GET|POST /servicios/`, `PATCH /servicios/{servicio_id}`
- `GET|POST /citas/`, `PATCH /citas/{cita_id}`

Los handlers `GET` de listado no declaran `response_model`, así que las respuestas son objetos ORM
sin validar. `POST /citas/` usa `shcemas.date`, que no tiene campo `estado` — las citas nuevas siempre
se crean como `"pendiente"`.

## Tooling: no hay ninguno

Sin tests, sin linter, sin formateador, sin type checker, sin CI, sin config de pre-commit, sin
ejemplo de `.env`.

- `fastapi.testclient.TestClient` **no se puede usar** — starlette 1.6.0 requiere `httpx2`, que no
  está instalado. Verifica los cambios levantando uvicorn y consultando los endpoints.
- No hay `.gitignore`, así que `__pycache__/*.pyc` y la base SQLite ya están versionados. Agrega un
  `.gitignore` antes de introducir nuevos artefactos de build.

## Git

Rama única `main` con remote `origin`. Los mensajes de commit son prosa en español en minúsculas, sin
prefijo de conventional-commit (`"agregando funcionalidad para modificar informacion de clientes y
servicios"`). Sigue ese estilo en lugar de introducir prefijos `feat:`/`fix:`.