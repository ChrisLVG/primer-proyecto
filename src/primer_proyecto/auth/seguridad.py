import bcrypt
import hashlib
from typing import Annotated
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from datetime import timedelta

from primer_proyecto import models
from primer_proyecto.auth import dependencias
from primer_proyecto.database import get_db
from primer_proyecto.utilidades import ROL_BARBERO

DURACION_SESION = timedelta(hours=24)

security = HTTPBearer(auto_error=False)
SesionDB = Annotated[Session, Depends(get_db)]

def hashear_contrasena(contrasena: str) -> str:
    """Genera y devuelve el hash bcrypt de una contraseña."""
    return bcrypt.hashpw(
        contrasena.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")

def _verificar_contrasena(contrasena: str, contrasena_hash: str) -> bool:
    """Comprueba una contraseña contra su hash bcrypt."""
    return bcrypt.checkpw(
        contrasena.encode("utf-8"),
        contrasena_hash.encode("utf-8"),
    )

def _hash_token(token: str) -> str: # metodo para encriptar un token
    """Devuelve el hash SHA-256 hexadecimal del token opaco.

    El token opaco nunca se almacena en texto plano; solo se guarda su hash
    en la tabla ``sesiones`` para poder localizarlo sin exponerlo.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def _autenticar(db: Session, correo: str, contrasena: str) -> models.Usuario:
    """Autentica las credenciales o responde con el error genérico 401."""
    usuario = (
        db.query(models.Usuario)
        .filter(models.Usuario.correo == correo)
        .first()
    )
    if (
        usuario is None
        or usuario.contrasena_hash is None
        or not _verificar_contrasena(contrasena, usuario.contrasena_hash)
    ):
        raise HTTPException(status_code=401, detail="Credenciales inválidas.")

    return usuario

SoloBarbero = Annotated[models.Usuario,Depends(dependencias.require_rol(ROL_BARBERO)),] # funcion annotated en el primer parametro defines el tipo de dato y en el segundo una condicion que deba tener ese dato