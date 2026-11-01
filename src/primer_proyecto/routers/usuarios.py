from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import IntegrityError

from .. import autenticador, models, schemas, utilidades

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


@router.get("/", response_model=list[schemas.UsuarioResponse])
def listar_usuarios(
    db: autenticador.SesionDB,
    current_user: autenticador.UsuarioActual,
):
    # RF-4.7: el barbero ve todos los usuarios; el usuario autenticado solo ve el suyo.
    if current_user.rol == utilidades.ROL_BARBERO:
        usuarios = db.query(models.Usuario).all()
    else:
        usuarios = db.query(models.Usuario).filter(
            models.Usuario.id == current_user.id
        ).all()
    return usuarios


@router.post(
    "/",
    response_model=schemas.UsuarioResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_usuario(
    usuario: schemas.UsuarioCreate,
    db: autenticador.SesionDB,
    _barbero: autenticador.SoloBarbero,
):
    existing_usuario = db.query(models.Usuario).filter(
        models.Usuario.correo == usuario.correo
    ).first()
    if existing_usuario:
        raise HTTPException(status_code=400, detail="El correo ya está registrado.")

    contrasena_hash = None
    if usuario.contrasena:
        contrasena_hash = autenticador.hashear_contrasena(usuario.contrasena)

    try:
        nuevo_usuario = models.Usuario(
            nombre=usuario.nombre,
            numero=usuario.numero,
            correo=usuario.correo,
            contrasena_hash=contrasena_hash,
            rol=utilidades.ROL_USUARIO,
        )
        db.add(nuevo_usuario)
        db.commit()
        db.refresh(nuevo_usuario)
        return nuevo_usuario
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="El correo ya está registrado.")


@router.patch("/{usuario_id}", response_model=schemas.UsuarioResponse)
def actualizar_usuario(
    usuario_id: str,
    usuario: schemas.UsuarioUpdate,
    db: autenticador.SesionDB,
    current_user: autenticador.UsuarioActual,
):
    usuario_db = utilidades.obtener_o_404(
        db, models.Usuario, usuario_id, "El usuario no está registrado."
    )

    utilidades.exigir_propietario(
        current_user,
        usuario_id,
        "No puedes modificar el registro de otro usuario.",
    )
    if current_user.rol == utilidades.ROL_USUARIO:
        if usuario.rol is not None:
            raise HTTPException(
                status_code=403,
                detail="No puedes modificar el rol de tu propio registro.",
            )

    if usuario.nombre is not None:
        usuario_db.nombre = usuario.nombre

    if usuario.numero is not None:
        usuario_db.numero = usuario.numero

    if usuario.correo is not None:
        correo_en_uso = db.query(models.Usuario).filter(
            models.Usuario.correo == usuario.correo,
            models.Usuario.id != usuario_id,
        ).first()
        if correo_en_uso:
            raise HTTPException(status_code=400, detail="El correo ya está registrado.")
        usuario_db.correo = usuario.correo

    if usuario.contrasena is not None:
        usuario_db.contrasena_hash = autenticador.hashear_contrasena(
            usuario.contrasena
        )

    if usuario.rol is not None:
        if usuario.rol not in utilidades.ROLES:
            raise HTTPException(
                status_code=400,
                detail="El rol debe ser 'usuario' o 'barbero'.",
            )
        usuario_db.rol = usuario.rol

    db.commit()
    db.refresh(usuario_db)
    return usuario_db


@router.delete("/{usuario_id}")
def eliminar_usuario(
    usuario_id: str,
    db: autenticador.SesionDB,
    _barbero: autenticador.SoloBarbero,
):
    usuario_db = utilidades.obtener_o_404(
        db, models.Usuario, usuario_id, "El usuario no está registrado."
    )

    try:
        utilidades.eliminar_dependencias_de_usuario(db, usuario_id)
        db.delete(usuario_db)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="No se pudo eliminar el usuario debido a una relación existente.",
        )

    return {"message": "Usuario eliminado correctamente"}
