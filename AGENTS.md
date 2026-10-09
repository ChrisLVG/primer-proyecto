# Sitio web para una barberia
- Sitio web para la gestion de informacion de clientes, servicios y citas para una barberia, muestra al usuario informacion de todos los servicios, permite al usuario gestionar sus citas agenciadas,permite al usuario contactar al barbero via whatsapp para la cita y permite al barbero visualizar todas las citas registradas en el sistema.
## Stack Tecnologico
**Backend:** Lenguaje Principal:Python 3.12,Framework Web (API REST):FastAPI,Validación de Datos y Serialización:** **Pydantic (v2),ORM (Object-Relational Mapping):SQLAlchemy (v2),Base de Datos Relacional: SQLite(`citas_unas.db`),Servidor ASGI:Uvicorn,Identificadores Únicos:UUID (Universally Unique Identifier -uuid4),Documentación Automática e Interactiva:OpenAPI / Swagger UI
**Frontend:** Lenguaje Base: JavaScript (ES6+),Librería / Framework de Interfaz (UI):React.js,Cliente HTTP (Consumo de la API):Axios,Framework de Estilos (Diseño UI/UX):Tailwind CSS,Enrutamiento del Cliente:React Router,Manejo de Sesión y Autenticación:LocalStorage / Cookies HttpOnly
## Estructura del proyecto
- pyproject.toml: Configuración del proyecto Python y dependencias de uv (FastAPI, Uvicorn). 
- README.md: Documentación general del proyecto. 
- .python-version: Versión de Python especificada para el entorno. 
- .gitignore: Archivos excluidos de Git (excluye .venv/, __pycache__). 
- src/primerproyecto/: Código fuente de la aplicación.
- AGENTS.md: Reglas y guardarraíles del repositorio para el agente de IA.
- main.py: Punto de entrada principal e itineración de rutas de la API FastAPI.
- database.py: Configuración de SQLAlchemy y gestión de sesiones de base de datos.
- models.py: Modelos ORM de la base de datos.
- schemas.py: Esquemas Pydantic para validación de datos de entrada y salida.
## Comandos principales
- uv run uvicorn src.primer_proyecto.main:app --reload --no-access-log: Para iniciar el servidor de desarrollo de FastAPI con recarga automática.
## Convenciones de codigo y estilo
- Seguir convención PEP 8: snake_case` para funciones/rutas y `PascalCase` para clases. 
- Usar Type Hints explícitos de Python 3.12+ (ej. list[str], str | None). 
- Redactar comentarios y docstrings en español.
- Usar ConfigDict(from_attributes=True) en los esquemas Pydantic de respuesta.
- NUNCA mezcles modelos de SQLAlchemy (models.py) con esquemas de validación Pydantic (schemas.py).
- Inyectar la sesión de base de datos en los endpoints de `main.py` usando únicamente `Depends(get_db)`.
- Retornar errores de negocio mediante `HTTPException` de FastAPI (`400`, `404`, `422`).
- Ejecutar `db.rollback()` explícito en bloques `try/except` ante fallos de escritura en SQLite.
## Limites y prohibiciones(Lo que NO debes hacer)
- NUNCA crees ni elimines archivos o carpetas nuevas sin proponérselo al usuario y obtener confirmación explícita.
- NUNCA intentes leer, inspeccionar o modificar directorios o archivos ignorados (`.venv/`, `__pycache__/`, archivos `.db` o `.lock`).
- NUNCA ejecutes comandos para instalar librerías (`uv add`, `pip install`) ni modifiques `pyproject.toml` sin aprobación previa del usuario.
- NUNCA alteres los modelos ORM de SQLAlchemy (`models.py`) ni cambies la estructura de las tablas sin la aprobacion previa del usuario y confirmando los requerimientos de la base de datos
- NUNCA ejecutes scripts o comandos que borren o reinicien los datos de la base de datos local (`citas_uñas.db`) a menos que el usuario lo solicite explícitamente.
- NUNCA reescribas o elimines funciones existentes que estén operativas; realiza únicamente cambios incrementales y modularizados
- NUNCA dupliques lógica de negocio o utilidades que ya existan en otros archivos del proyecto
- NUNCA ejecutes comandos destructivos en la terminal (ej. `rm`, `del`, detención de procesos globales) sin la aprobacion previa del usuario
# Flujo de trabajo y memoria
- Antes de iniciar una tarea, lee `memory.md` para conocer el estado actual y las decisiones previas
- Al finalizar cada tarea, actualiza `memory.md` resumiendo las modificaciones realizadas, aprendizajes y próximos pasos