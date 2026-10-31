# Plan: 003 — Eliminación de usuarios y servicios asociados

## 1. Cambios previstos

| Archivo | Responsabilidad | Cambio |
| --- | --- | --- |
| `src/primer_proyecto/main.py` | Endpoints y escrituras transaccionales | Eliminar las citas y sesiones del usuario; al eliminar un servicio, eliminar las citas que perderían su único servicio, actualizar el resto y recalcular sus precios. |
| `AGENTS.md` | Reglas operativas del repositorio | Sustituir la regla anterior de `409` para borrados asociados por el comportamiento aprobado. |
| `specs/002_autenticacion/spec.md` | Contrato documentado de rutas | Actualizar las descripciones de los DELETE que aún indican que los registros asociados bloquean el borrado. |
| `memory.md` | Estado y decisiones | Registrar implementación y validación al completar las tareas. |

`models.py`, `schemas.py`, `database.py` y el esquema de SQLite no se modifican. No se añaden dependencias ni archivos de prueba permanentes.

## 2. Lógica e interfaces

Se conservan las rutas y las respuestas de éxito actuales. Las rutas siguen inyectando la sesión únicamente con `Depends(get_db)`.

### `DELETE /servicios/{servicio_id}`

1. Buscar el servicio; si no existe, responder `404`.
2. Cargar todas las citas relacionadas y sus servicios.
3. Para cada cita relacionada:
   - Si el servicio es el único, eliminar la cita.
   - Si quedan otros servicios, quitar solo el servicio seleccionado y recalcular `precio_total` sumando los precios actuales restantes.
4. Eliminar el servicio y confirmar todos los cambios en un único commit.
5. Si ocurre un `IntegrityError`, ejecutar `rollback()` y responder con un error HTTP explícito; nunca devolver éxito si el commit falló.

El procesamiento incluye citas de cualquier estado. Las citas no asociadas al servicio no se modifican.

### `DELETE /usuarios/{usuario_id}`

1. Buscar el usuario; si no existe, responder `404`.
2. Eliminar todas sus citas y sesiones antes de eliminar el usuario, manteniendo las operaciones dentro de una única transacción.
3. Confirmar una sola vez; ante `IntegrityError`, ejecutar `rollback()` y responder con un error HTTP explícito.
4. Mantener el cuerpo de éxito existente.

La eliminación no depende de `ON DELETE CASCADE` de SQLite ni requiere cambios de esquema.

## 3. Algoritmo resumido

```text
eliminar_servicio(id):
    servicio = buscar(id) o 404
    citas = cargar citas que incluyen servicio y sus servicios
    para cada cita:
        si cantidad(servicios) == 1:
            eliminar cita
        si no:
            quitar servicio de cita
            cita.precio_total = suma(precios restantes)
    eliminar servicio
    commit
    si IntegrityError: rollback y error HTTP

eliminar_usuario(id):
    usuario = buscar(id) o 404
    eliminar citas del usuario
    eliminar sesiones del usuario
    eliminar usuario
    commit
    si IntegrityError: rollback y error HTTP
```

## 4. Casos límite y riesgos

- Un servicio puede afectar citas de varios usuarios y estados; todas se procesan en la misma transacción.
- Una mezcla de citas que perderían su único servicio y citas con servicios restantes debe eliminar las primeras y conservar/actualizar las segundas.
- Si falla el commit, no debe quedar borrado el servicio con asociaciones o precios a medio actualizar.
- La eliminación ORM de citas debe retirar sus filas de `cita_servicio`; se comprobará por HTTP y verificando las citas/servicios resultantes.
- La eliminación del usuario incluye sus sesiones para evitar que la FK obligatoria impida el borrado.
- Los errores capturados no deben convertirse en respuestas de éxito.

## 5. Estrategia de pruebas

No hay suite de pruebas automatizadas en el repositorio y `TestClient` no es compatible con las versiones instaladas. Para respetar la constitución, cada tarea ejecutará pruebas HTTP reales con Uvicorn en loopback y SQLite en memoria, sin tocar la base local ni guardar scripts temporales en el repositorio.

- Antes de implementar cada tarea, ejecutar el escenario correspondiente y comprobar que falla en el comportamiento requerido (rojo).
- Después de implementar, repetir exactamente la petición y verificar status code y estado persistido (verde).
- Comprobar la operación mezclada de eliminación de un servicio sobre una cita que queda vacía y otra que conserva servicios.
- Comprobar que eliminar un usuario borra sus citas y sesiones, sin afectar a otros usuarios.
- Al final, ejecutar una regresión HTTP focalizada de ambos endpoints, incluidos IDs inexistentes y confirmación de que no hay cambios parciales en los casos cubiertos.

## 6. Dependencias

T1 y T2 modifican bloques distintos de `main.py` y son conceptualmente independientes, pero se ejecutarán en secuencia para aislar las pruebas y preservar el flujo de una tarea cada vez. T3 actualiza documentación y ejecuta la regresión final después de T1 y T2.
