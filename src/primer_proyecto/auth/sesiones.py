import secrets
from typing import Annotated
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from datetime import timedelta

from primer_proyecto.database import get_db
from primer_proyecto import models
from primer_proyecto import schemas
from . import seguridad
from .dependencias import _ahora
from primer_proyecto.auth import dependencias

DURACION_SESION = timedelta(hours=24)

security = HTTPBearer(auto_error=False)
SesionDB = Annotated[Session, Depends(get_db)]

def _crear_sesion(db: Session, usuario_id: str) -> str: #se ejecuta cuando el usuario hace un login, usa el metodo para encriptar el token, lo guarda en la base de datos y devuelve el token en texto plano
    """Genera un token opaco, persiste su hash SHA-256 con TTL de 24 h y devuelve el token.

    El token se entrega en texto plano al cliente; en la base de datos solo se
    almacena su hash SHA-256 junto con la fecha de creación y de expiración.
    """
    token = secrets.token_urlsafe(32)
    token_hash = seguridad._hash_token(token)

    # Una única variable `ahora` para mantener la consistencia de la marca temporal
    ahora = _ahora()

    try:
        sesion = models.Sesion(
            token_hash=token_hash,
            usuario_id=usuario_id,
            created_at=ahora,
            expires_at=ahora + DURACION_SESION,
        )
        db.add(sesion)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="No se pudo crear la sesión.")

    return token

def _obtener_sesion_valida(db: Session, token: str) -> models.Sesion: # metodo para verificar si una sesion no ha caducado y devolverla
    """Valida que exista una sesión activa y no expirada para el token dado.

    Calcula el hash SHA-256 del token opaco, busca la sesión en la base de datos y
    comprueba que no haya superado su fecha de expiración. Lanza 401 si la sesión
    no existe o ha expirado.
    """
    token_hash = seguridad._hash_token(token)
    sesion = (
        db.query(models.Sesion)
        .filter(models.Sesion.token_hash == token_hash)
        .first()
    )
    if sesion is None:
        raise HTTPException(status_code=401, detail="Sesión no válida.")

    if sesion.expires_at < dependencias._ahora():
        raise HTTPException(status_code=401, detail="La sesión ha expirado.")

    return sesion

def cerrar_sesion(
    *,
    token: Annotated[HTTPAuthorizationCredentials | None, Depends(security)] = None,
    db: SesionDB,
):
    """Cierra la sesión del usuario autenticado (RF-3.1, RF-3.2).

    Elimina la sesión asociada al token Bearer recibido en el header
    ``Authorization: Bearer <token>``. Si no hay token, o el token es inválido
    o ha expirado, se responde con 401.
    """
    if token is None:
        raise HTTPException(status_code=401, detail="No autenticado.")

    sesion = _obtener_sesion_valida(db, token.credentials)

    try:
        db.delete(sesion)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="No se pudo cerrar la sesión.",
        )

    return schemas.LogoutResponse(message="Sesión cerrada correctamente")
