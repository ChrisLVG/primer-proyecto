---
description: Fase de validacion de funcionalidad
agent: build
---

# Validacion de la caracteristica

Ejecuta la fase de validacion para la especificacion `specs/$ARGUMENTS/spec.md`

## Pasos a seguir

- Comprueba la aplicacion para verificar tecnicamente que no existan errores en consola ni en la API.
- Comprueba punto por punto que cada requisito funcional de `specs/$ARGUMENTS/spec.md` se cumple totalmente.
- Ejecuta `uv run pytest`.
- Comprueba los criterios de finalización y los principios inviolables de docs/constitution.md.
- Muestra un resumen del estado de validacion.
