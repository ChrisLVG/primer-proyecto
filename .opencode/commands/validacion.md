---
description: Fase de validacion de funcionalidad
agent: build
---

# Validacion de la caracteristica

Ejecuta la fase de validacion para la especificacion `specs/$ARGUMENTS/spec.md`

## Pasos a seguir

- Comprueba la aplicacion para verificar tecnicamente que no existan errores en consola ni en la API.
- Comprueba punto por punto que cada requisito funcional de `specs/$ARGUMENTS/spec.md` se cumple totalmente.
- realiza pruebas con - `uv run uvicorn src.primer_proyecto.main:app --reload --no-access-log` o `uv run primer-proyecto`: Alternativa al anterior, definida en `[project.scripts]`; usa `primer_proyecto.main` (el atributo `main` de `__init__.py`). Si mueves `main()`.
- Comprueba los criterios de finalización y los principios inviolables de docs/constitution.md.
- Muestra un resumen del estado de validacion.
