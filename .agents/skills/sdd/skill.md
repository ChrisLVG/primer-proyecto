--- 
name: sdd 
description: Úsala siempre que trabajes con Spec-Driven Development en este proyecto (docs/constitution.md o cualquier archivo dentro de specs/) - redactar, revisar o cambiar specs, planes y tareas, o implementar y validar tareas de una spec. 
--- 

# Spec-Driven Development (SDD) 
## Flujo 
Constitución → Spec → Clarificación → Plan → Tareas → Implementación → Validación → Cambio. 

- Nunca pases a la siguiente fase sin la aprobación explícita del usuario. 
- La spec manda: si algo no está en la spec, no se implementa. Si falta una decisión, para y pregunta. 
- Un cambio de requisitos se hace primero en la spec, luego en el plan y las tareas, y por último en el código. 
- Cada spec vive en su carpeta: `specs/NNN-nombre/` con `spec.md`, `plan.md` y `tasks.md`. 
- Al terminar cada fase, actualiza `MEMORY.md`. 

## Plantilla de spec (spec.md) 
``` 
# Spec NNN — <Nombre> 
Estado: borrador | aprobada | implementada 
## Contexto y objetivo 
## Usuarios 
## Historias de usuario - HU-1. Como <rol>, quiero <acción> para <beneficio>. 
## Definiciones (solo si hay términos que puedan interpretarse de varias formas) 
## Requisitos funcionales 
## Requisitos no funcionales 
## Casos límite 
## Fuera de alcance 
## Criterios de finalización 
## Dudas abiertas - [NECESITA ACLARACIÓN] <duda> 
``` 
La spec describe el QUÉ y el POR QUÉ. Nada de stack, arquitectura ni nombres de archivos.

## Requisitos en EARS (en español) 
- RF-x: CUANDO <evento>, EL SISTEMA <respuesta>. 
- RF-x: SI <condición no deseada>, ENTONCES EL SISTEMA <respuesta>. 
- RF-x: MIENTRAS <estado>, EL SISTEMA <respuesta>. 
- RF-x: EL SISTEMA <comportamiento permanente>. 
Cada RF debe ser verificable: nada de "rápido", "intenso" o "bonito" sin un criterio medible.

##  plantilla de Plan (plan.md) 
- Cambios de código previstos, que archivos se modifican y que resposabilidad tiene cada uno, las dependencias y la estructura de archivos 
- Logica de negocio, funciones, interfaces y validaciones a implementar  
- Algoritmo en pseudocódigo  
- Casos limite a considerar, posibles riesgos de implementacion y decisiones tecnicas justificadas 
- Estrategia de tests con `uv run pytest`. Indica qué RF cubre cada parte.

## pasos a seguir en la clarificacion
- Identifica ambiguedades, inconsistencias o contradicciones en la especificación, lagunas logicas o requisitos poco claros o imcompletos, casos limites no cubiertos y conflictos con docs/constitution.md.
- Enumera los hallazgos encontrados y propon como corregirlos o aclararlos.
- Tras la confirmacion, redacta la versión final de la especificación técnica en `specs/$ARGUMENTS/spec.md` incorporando las correcciones y aclaraciones acordadas.

## plantilla de Tareas (tasks.md) 

**cada tarea debe contener:**

1. Descripción detallada de la tarea
2. Que ademas, cubran todos los RF y validaciones, incluyendo:
    - archivos a crear o modificar y cambios a realizar
    - Validaciones de entrada y salida
    - Manejo de errores y casos borde
    - Criterios de aceptación y verificación

Máximo 20-30 min por tarea, en orden de dependencia. Si salen más de 10, propón dividir la spec.


##  Implementación 
Una sola tarea cada vez: tests primero (en rojo), después el código, `uv run pytest` en verde, marcar la tarea y para.

## Revision
- Comprueba la aplicacion para verificar tecnicamente que no existan errores en consola ni en la API.
- Comprueba punto por punto que cada requisito funcional de `specs/$ARGUMENTS/spec.md` se cumple totalmente.
- Muestra un resumen del estado de validacion.