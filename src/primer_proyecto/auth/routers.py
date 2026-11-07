from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import timedelta
from datetime import timedelta

from primer_proyecto.database import get_db
from primer_proyecto import schemas, models
from primer_proyecto.utilidades import ROL_USUARIO
from . import sesiones,seguridad

DURACION_SESION = timedelta(hours=24)

security = HTTPBearer(auto_error=False)
router = APIRouter(prefix="/auth", tags=["Autenticación"])
SesionDB = Annotated[Session, Depends(get_db)]

@router.post(
    "/register",
    response_model=schemas.UsuarioResponse,
    status_code=status.HTTP_201_CREATED,
)
def registrar_usuario(registro: schemas.UsuarioCreate, db: SesionDB):
    """Registra un nuevo usuario público con rol `usuario` (RF-1).

    Es un endpoint público: no requiere token de autenticación. La contraseña se hashea con
    bcrypt antes de almacenarla (RF-1.2) y nunca se devuelve en la respuesta, ya que
    `UsuarioResponse` no la incluye. Si el correo ya está registrado se devuelve 400
    (RF-1.3); los errores de validación del esquema se devuelven como 422 por Pydantic.
    """
    # Validamos que el correo no esté ya registrado (RF-1.3)
    existing_usuario = (
        db.query(models.Usuario)
        .filter(models.Usuario.correo == registro.correo)
        .first()
    )
    if existing_usuario:
        raise HTTPException(status_code=400, detail="El correo ya está registrado.")

    # Hasheamos la contraseña con bcrypt antes de almacenarla (RF-1.2).
    # bcrypt impone un límite de 72 bytes, ya validado por el esquema de entrada.
    contrasena_hash = seguridad.hashear_contrasena(registro.contrasena)

    try:
        nuevo_usuario = models.Usuario(
            nombre=registro.nombre,
            numero=registro.numero,
            correo=registro.correo,
            contrasena_hash=contrasena_hash,
            rol=ROL_USUARIO,  # Rol por defecto al registrarse (RF-1.5)
        )
        db.add(nuevo_usuario)
        db.commit()
        db.refresh(nuevo_usuario)
        return nuevo_usuario
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="El correo ya está registrado.")

@router.post("/login", response_model=schemas.AuthResponse)
def iniciar_sesion(credenciales: schemas.LoginRequest, db: SesionDB):
    """Inicia sesión con correo y contraseña (RF-2.1, RF-2.3).

    Autentica al usuario con sus credenciales y, si son válidas, emite un token
    opaco con TTL de 24 horas (RF-2.2). Las credenciales inválidas (correo
    inexistente, contraseña incorrecta o usuario sin contraseña) se rechazan
    con 401 sin revelar qué parte falló.
    """
    usuario = seguridad._autenticar(db, credenciales.correo, credenciales.contrasena)

    # 5. Creamos la sesión y obtenemos el token opaco
    token = sesiones._crear_sesion(db, usuario.id)

    # 6. Devolvemos el token junto con los datos del usuario (sin contraseña)
    return schemas.AuthResponse(token=token, usuario=usuario)

@router.post("/logout", response_model=schemas.LogoutResponse)
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

    sesion = sesiones._obtener_sesion_valida(db, token.credentials)

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
