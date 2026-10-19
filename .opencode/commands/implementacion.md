---
description: Implementar tareas de la funcionalidad
agent: build
---

# Implementacion de la caracteristica

Lee `docs/constitution.md`, `specs/$ARGUMENTS/spec.md`, `specs/$ARGUMENTS/plan.md` y `specs/$ARGUMENTS/tasks.md` y genera el código necesario para implementar la nueva funcionalidad en el proyecto, siguiendo las tareas de desarrollo planificadas.

## Pasos a seguir

- Manten el codigo modular y adherido a las convenciones del repositorio, siguiendo los principios de la constitución del proyecto.
- Implementar tareas de desarrollo en el orden secuencial definido en `specs/$ARGUMENTS/tasks.md`, respetando las dependencias entre ellas.
- Cada tarea debe implementarse en un commit independiente, con un mensaje de commit que describa la tarea y el RF que cubre.
- Una vez que se termine de implementar una tarea, realiza pruebas unitarias y de integración para verificar que la funcionalidad cumple con los criterios de aceptación definidos en la especificación técnica.
- Marca cada tarea como completada en `specs/$ARGUMENTS/tasks.md` una vez que haya sido implementada y probada y actualiza la memoria persistente en `memory.md`.
