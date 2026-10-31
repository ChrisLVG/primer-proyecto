# Tareas de desarrollo: 003 — Eliminación de usuarios y servicios asociados

**Estado:** ✅ Todas las tareas completadas. Regresión final HTTP: 12/12.

## Resumen de dependencias

```text
T1 (borrado de servicios) ──┐
                            ├──► T3 (documentación y regresión HTTP)
T2 (borrado de usuarios) ───┘
```

## T1 — Eliminar servicio y procesar las citas asociadas

**Estado:** ✅ Completada. Prueba HTTP roja antes del cambio; 7/7 criterios verdes después.

**Dependencias:** Ninguna.

**Descripción detallada:** Actualizar `DELETE /servicios/{servicio_id}` para retirar el servicio de las citas, eliminar las citas que perderían su último servicio y recalcular el total de las restantes, todo dentro de una transacción.

**Archivos a modificar:** `src/primer_proyecto/main.py`.

**Cambios y validaciones:**

1. Escribir y ejecutar primero pruebas HTTP (rojo) en SQLite en memoria:
   - Servicio sin citas: `200` y servicio eliminado.
   - Cita con solo ese servicio: `200`, servicio y cita eliminados.
   - Cita con ese servicio y otros: `200`, cita conservada, asociación eliminada y precio igual a la suma de los servicios restantes.
   - Mezcla de ambas clases de citas: eliminar únicamente las citas que quedan vacías; conservar y recalcular las otras.
   - Cita no relacionada: permanece sin cambios.
   - Servicio inexistente: `404`.
2. Implementar la carga de citas asociadas y sus servicios.
3. Eliminar las citas que quedarían sin servicios; para las otras, quitar la relación y recalcular `precio_total`.
4. Borrar el servicio y confirmar todo en una sola transacción.
5. Ante `IntegrityError`, hacer `rollback()` y devolver error HTTP, nunca una respuesta de éxito.
6. Repetir las pruebas y verificar status y estado persistido (verde).

**Casos borde y aceptación:**

- Los estados de cita no cambian qué citas afectadas se procesan.
- Ninguna cita conservada termina sin servicios.
- Un fallo de escritura no deja asociaciones ni precios parcialmente modificados.
- **RF cubiertos:** RF-3, RF-4, RF-5, RF-6, RF-7, RF-8.

## T2 — Eliminar usuario con citas y sesiones

**Estado:** ✅ Completada. Prueba HTTP roja antes del cambio; 5/5 criterios verdes después.

**Dependencias:** Ninguna.

**Descripción detallada:** Actualizar `DELETE /usuarios/{usuario_id}` para borrar las citas y sesiones del usuario junto con el usuario, sin cambiar el contrato de éxito.

**Archivos a modificar:** `src/primer_proyecto/main.py`.

**Cambios y validaciones:**

1. Escribir y ejecutar primero pruebas HTTP (rojo) en SQLite en memoria:
   - Usuario con citas y sesión: borrar con `200`; usuario, citas, asociaciones y sesiones dejan de existir.
   - Usuario sin datos dependientes: borrar con `200`.
   - Usuario inexistente: `404`.
   - Otro usuario y sus datos permanecen intactos.
2. Eliminar primero citas y sesiones asociadas en la misma transacción; luego eliminar el usuario.
3. Ante `IntegrityError`, hacer `rollback()` y devolver error HTTP explícito.
4. Repetir las pruebas y verificar los registros relacionados (verde).

**Casos borde y aceptación:**

- El borrado no depende de las cascadas de claves foráneas de SQLite.
- Una operación fallida no deja un usuario parcialmente borrado.
- Se mantiene el mensaje de éxito existente.
- **RF cubiertos:** RF-1, RF-2, RF-8.

## T3 — Sincronizar documentación y ejecutar regresión HTTP

**Estado:** ✅ Completada. Documentación sincronizada; regresión HTTP 12/12.

**Dependencias:** T1 y T2.

**Descripción detallada:** Actualizar la documentación existente que aún describe los borrados relacionados como conflictos, y verificar ambos endpoints en conjunto.

**Archivos a modificar:** `AGENTS.md`, `specs/002_autenticacion/spec.md`, `specs/002_autenticacion/plan.md`, `memory.md`.

**Cambios y validaciones:**

1. Actualizar en `AGENTS.md` la política de borrado de usuarios y servicios.
2. Actualizar `specs/002_autenticacion/spec.md` y `specs/002_autenticacion/plan.md` para que no contradigan esta spec.
3. Ejecutar Uvicorn con SQLite en memoria y repetir los escenarios principales de T1 y T2, validando códigos HTTP, relaciones, precios y aislamiento de registros no afectados.
4. Ejecutar `git diff --check` y comprobar que `memory.md` no supera 50 líneas.
5. Actualizar esta tarea y la memoria con el resultado verificado.

**Criterios de aceptación:**

- No quedan documentos vigentes que indiquen que cualquier cita asociada bloquea el borrado de usuarios o servicios.
- La regresión HTTP cumple RF-1 a RF-8.
- La base de datos local no se modifica.
