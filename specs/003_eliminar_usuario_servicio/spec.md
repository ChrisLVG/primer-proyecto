# Spec 003 — Eliminación de usuarios y servicios asociados
Estado: aprobada

## Contexto y objetivo

Permitir la eliminación de usuarios y servicios aunque estén relacionados con citas, eliminando las citas que queden sin servicios y manteniendo actualizados los precios de las restantes.

## Usuarios

- Barbero que administra usuarios, servicios y citas.

## Historias de usuario

- HU-1. Como barbero, quiero eliminar un usuario y sus datos dependientes para retirar completamente su cuenta del sistema.
- HU-2. Como barbero, quiero eliminar un servicio junto con las citas que se queden sin servicios y mantener actualizadas las citas restantes.

## Definiciones

- Una cita afectada por la eliminación de un servicio es una cita que incluye ese servicio.
- Una cita quedaría vacía si el servicio eliminado es el único servicio que tiene asociado.
- La eliminación es atómica: si la operación se rechaza o falla, no quedan cambios parciales.

## Requisitos funcionales

- RF-1: CUANDO se solicita eliminar un usuario existente, EL SISTEMA elimina el usuario, todas sus citas y todas sus sesiones asociadas.
- RF-2: SI el usuario solicitado no existe, ENTONCES EL SISTEMA responde `404` y no modifica datos.
- RF-3: CUANDO se solicita eliminar un servicio existente que no está asociado a citas, EL SISTEMA lo elimina y responde `200`.
- RF-4: CUANDO se solicita eliminar un servicio asociado a citas, EL SISTEMA elimina las citas que tengan únicamente ese servicio.
- RF-5: CUANDO se elimina un servicio asociado, EL SISTEMA elimina sus asociaciones con las citas que conservan otros servicios, mantiene esas citas y sus demás servicios, y recalcula `precio_total` como la suma de los precios actuales de los servicios restantes.
- RF-6: CUANDO se elimina un servicio y sus citas afectadas, EL SISTEMA realiza todos los cambios como una operación atómica.
- RF-7: SI el servicio solicitado no existe, ENTONCES EL SISTEMA responde `404` y no modifica datos.
- RF-8: CUANDO ocurre un error durante una eliminación, EL SISTEMA revierte la operación completa y no deja modificaciones parciales.

## Requisitos no funcionales

- El contrato de rutas y las respuestas de éxito existentes se mantienen.
- Los errores de negocio usan respuestas HTTP y mensajes en español.
- La eliminación y sus cambios relacionados se verifican por HTTP real.

## Casos límite

- Si una cita afectada solo tiene el servicio eliminado, se elimina esa cita.
- Si otras citas afectadas conservan otros servicios, esas citas permanecen, pierden únicamente la asociación al servicio eliminado y recalculan su precio.
- Una eliminación que afecta varias citas combina ambas acciones en la misma operación; no deja cambios parciales.
- El precio recalculado refleja los precios vigentes de los servicios restantes.
- Las citas del usuario se eliminan independientemente de su estado.
- El borrado del usuario también elimina las sesiones que de otro modo impedirían eliminarlo.
- Las citas que no incluyen el servicio eliminado no deben cambiar.

## Fuera de alcance

- Cambios a los modelos o al esquema de la base de datos.
- Revalidar solapamientos horarios existentes.
- Cambios a rutas, autenticación, permisos o formatos de respuesta.

## Criterios de finalización

- El borrado del usuario elimina al usuario, todas sus citas y sus sesiones; un ID desconocido responde `404`.
- Un servicio libre se elimina con `200`; un ID desconocido responde `404`.
- Un servicio asociado se elimina con `200`; las citas cuyo único servicio era ese se eliminan, y las otras citas conservan sus servicios restantes con el precio recalculado.
- Una falla durante cualquier cambio relacionado revierte la operación completa.
- Los errores durante las escrituras revierten todos los cambios.
- Las pruebas HTTP cubren códigos de respuesta, datos relacionados, recálculo y atomicidad.

## Dudas abiertas

- Ninguna.
