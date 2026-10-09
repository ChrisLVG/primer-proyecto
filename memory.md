## Memoria del proyecto
**Instrucción para el Agente:** Mantén este archivo comprimido en un máximo de 50 líneas. Resume o elimina tareas pasadas que ya estén integradas en la V1 del código
## Estado actual
- Implementando el CRUD para gestionar informacion de clientes, citas y servicios
## Aprendizajes y hallazgos
- Se ha aprendido a utilizar FastAPI para crear una API RESTful, Pydantic para la validación de datos y SQLAlchemy para la gestión de la base de datos.
## Decisiones de arquitectura y tecnología
- Se decidió empezar por el backend para establecer la estructura de la API y la base de datos antes de desarrollar el frontend. Se optó por FastAPI debido a su rendimiento y facilidad de uso, y React.js para el frontend por su popularidad y capacidad de crear interfaces de usuario interactivas.
- Se optó por Pydantic para la validación de datos y SQLAlchemy como ORM. Se establecieron convenciones de código y estilo, incluyendo el uso de Type Hints y docstrings en español.
## Próximos pasos
- [ ] Terminar de definir modelos ORM (SQLAlchemy) y esquemas (Pydantic) para Clientes. 
- [ ] Terminar de definir modelos ORM y esquemas para Servicios. 
- [ ] Terminar de definir modelos ORM y esquemas para Citas. 
- [ ] Terminar de crear los endpoints de la API en main.py e inyectar la sesión de BD.