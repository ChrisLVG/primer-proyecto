from typing import Annotated
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from primer_proyecto.database import get_db
from primer_proyecto import models
from primer_proyecto.utilidades import ROL_BARBERO, ROL_USUARIO
from . import sesiones

DURACION_SESION = timedelta(hours=24)

security = HTTPBearer(auto_error=False)
SesionDB = Annotated[Session, Depends(get_db)]

def get_current_user(
    *,
    token: Annotated[HTTPAuthorizationCredentials | None, Depends(security)] = None,
    db: SesionDB,
) -> models.Usuario: #funcion verifica si el usuario esta autenticado y lo devuelve, usa el metodo para verificar si la sesion no ha expirado
    """Devuelve el usuario autenticado a partir del token Bearer.

    Si no se envía token, lanza 401 "No autenticado.". Si la sesión no existe
    o ha expirado, `_obtener_sesion_valida` lanza el 401 correspondiente.
    Devuelve el modelo `Usuario` asociado a la sesión válida.
    """
    if token is None:
        raise HTTPException(status_code=401, detail="No autenticado.")

    sesion = sesiones._obtener_sesion_valida(db, token.credentials)
    return sesion.usuario

UsuarioActual = Annotated[models.Usuario, Depends(get_current_user)]

def require_rol(rol_requerido: str): # funcion que recibe como parametro un rol, usa la funcion para verificar si el usuario esta autenticado, cuenta con un metodo que extrae el rol de ese usuario y verifica si es el rol requerido
    """Devuelve una dependencia que exige que el usuario autenticado tenga el rol indicado.

    Si el rol del usuario no coincide, responde con 403. Si el usuario no está
    autenticado, `get_current_user` ya responde con 401.
    """

    def _verificar_rol(current_user: UsuarioActual) -> models.Usuario:
        if current_user.rol != rol_requerido:
            raise HTTPException(
                status_code=403,
                detail=f"Se requiere rol '{rol_requerido}'.",
            )
        return current_user

    return _verificar_rol

def _ahora() -> datetime:
    """Devuelve la fecha y hora local actual."""
    return datetime.now()

