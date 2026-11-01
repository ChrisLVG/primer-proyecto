import bcrypt
import hashlib
import secrets
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from .database import get_db
from . import models
from . import schemas

security = HTTPBearer(auto_error=False)
router = APIRouter(prefix="/auth", tags=["Autenticación"])

# --- Autenticación ---

@router.post(
    "/register",
    response_model=schemas.UsuarioResponse,
    status_code=status.HTTP_201_CREATED,
)
def registrar_usuario(registro: schemas.UsuarioCreate, db: Session = Depends(get_db)):
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
    contrasena_hash = bcrypt.hashpw(
        registro.contrasena.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")

    try:
        nuevo_usuario = models.Usuario(
            nombre=registro.nombre,
            numero=registro.numero,
            correo=registro.correo,
            contrasena_hash=contrasena_hash,
            rol="usuario",  # Rol por defecto al registrarse (RF-1.5)
        )
        db.add(nuevo_usuario)
        db.commit()
        db.refresh(nuevo_usuario)
        return nuevo_usuario
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="El correo ya está registrado.")


def _hash_token(token: str) -> str: # metodo para encriptar un token
    """Devuelve el hash SHA-256 hexadecimal del token opaco.

    El token opaco nunca se almacena en texto plano; solo se guarda su hash
    en la tabla ``sesiones`` para poder localizarlo sin exponerlo.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _crear_sesion(db: Session, usuario_id: str) -> str: #se ejecuta cuando el usuario hace un login, usa el metodo para encriptar el token, lo guarda en la base de datos y devuelve el token en texto plano
    """Genera un token opaco, persiste su hash SHA-256 con TTL de 24 h y devuelve el token.

    El token se entrega en texto plano al cliente; en la base de datos solo se
    almacena su hash SHA-256 junto con la fecha de creación y de expiración.
    """
    token = secrets.token_urlsafe(32)
    token_hash = _hash_token(token)

    # Una única variable `ahora` para mantener la consistencia de la marca temporal
    ahora = datetime.now()

    try:
        sesion = models.Sesion(
            token_hash=token_hash,
            usuario_id=usuario_id,
            created_at=ahora,
            expires_at=ahora + timedelta(hours=24),
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
    token_hash = _hash_token(token)
    sesion = (
        db.query(models.Sesion)
        .filter(models.Sesion.token_hash == token_hash)
        .first()
    )
    if sesion is None:
        raise HTTPException(status_code=401, detail="Sesión no válida.")

    if sesion.expires_at < datetime.now():
        raise HTTPException(status_code=401, detail="La sesión ha expirado.")

    return sesion


def get_current_user(
    token: Annotated[HTTPAuthorizationCredentials | None, Depends(security)] = None,
    db: Session = Depends(get_db),
) -> models.Usuario: #funcion verifica si el usuario esta autenticado y lo devuelve, usa el metodo para verificar si la sesion no ha expirado
    """Devuelve el usuario autenticado a partir del token Bearer.

    Si no se envía token, lanza 401 "No autenticado.". Si la sesión no existe
    o ha expirado, `_obtener_sesion_valida` lanza el 401 correspondiente.
    Devuelve el modelo `Usuario` asociado a la sesión válida.
    """
    if token is None:
        raise HTTPException(status_code=401, detail="No autenticado.")

    sesion = _obtener_sesion_valida(db, token.credentials)
    return sesion.usuario


def require_rol(rol_requerido: str): # funcion que recibe como parametro un rol, usa la funcion para verificar si el usuario esta autenticado, cuenta con un metodo que extrae el rol de ese usuario y verifica si es el rol requerido
    """Devuelve una dependencia que exige que el usuario autenticado tenga el rol indicado.

    Si el rol del usuario no coincide, responde con 403. Si el usuario no está
    autenticado, `get_current_user` ya responde con 401.
    """

    def _verificar_rol(current_user: models.Usuario = Depends(get_current_user)) -> models.Usuario:
        if current_user.rol != rol_requerido:
            raise HTTPException(
                status_code=403,
                detail=f"Se requiere rol '{rol_requerido}'.",
            )
        return current_user

    return _verificar_rol


@router.post("/login", response_model=schemas.AuthResponse)
def iniciar_sesion(credenciales: schemas.LoginRequest, db: Session = Depends(get_db)):
    """Inicia sesión con correo y contraseña (RF-2.1, RF-2.3).

    Autentica al usuario con sus credenciales y, si son válidas, emite un token
    opaco con TTL de 24 horas (RF-2.2). Las credenciales inválidas (correo
    inexistente, contraseña incorrecta o usuario sin contraseña) se rechazan
    con 401 sin revelar qué parte falló.
    """
    # 1. Buscamos al usuario por correo
    usuario = (
        db.query(models.Usuario)
        .filter(models.Usuario.correo == credenciales.correo)
        .first()
    )

    # 2. Usuario inexistente → credenciales inválidas (sin revelar si el correo existe)
    if usuario is None:
        raise HTTPException(status_code=401, detail="Credenciales inválidas.")

    # 3. Usuario sin contraseña (creado por POST /usuarios/ o promovido sin contraseña)
    if usuario.contrasena_hash is None:
        raise HTTPException(status_code=401, detail="Credenciales inválidas.")

    # 4. Verificamos la contraseña antes de crear la sesión (fallar temprano)
    if not bcrypt.checkpw(
        credenciales.contrasena.encode("utf-8"),
        usuario.contrasena_hash.encode("utf-8"),
    ):
        raise HTTPException(status_code=401, detail="Credenciales inválidas.")

    # 5. Creamos la sesión y obtenemos el token opaco
    token = _crear_sesion(db, usuario.id)

    # 6. Devolvemos el token junto con los datos del usuario (sin contraseña)
    return schemas.AuthResponse(token=token, usuario=usuario)


@router.post("/logout", response_model=schemas.LogoutResponse)
def cerrar_sesion(
    token: Annotated[HTTPAuthorizationCredentials | None, Depends(security)] = None,
    db: Session = Depends(get_db),
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