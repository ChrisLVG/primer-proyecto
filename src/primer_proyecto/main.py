from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload
from datetime import datetime

from .database import get_db, engine
from . import models
from . import schemas

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="API de Gestión de Citas para la barberia",
    description="Esta API permite gestionar usuarios, servicios y citas para una barberia.",
    version="1.0.0"
)


def _obtener_servicios(db: Session, servicios_ids: list[str]) -> list[models.Servicio]:
    """Valida que la lista tenga IDs únicos y que todos los servicios existan.

    Devuelve los objetos Servicio para poder calcular el precio total.
    """
    # Una cita no puede llevar dos veces el mismo servicio
    if len(set(servicios_ids)) != len(servicios_ids):
        raise HTTPException(status_code=400, detail="La lista de servicios contiene IDs duplicados.")

    servicios = db.query(models.Servicio).filter(models.Servicio.id.in_(servicios_ids)).all()
    encontrados = {servicio.id for servicio in servicios}

    faltantes = [servicio_id for servicio_id in servicios_ids if servicio_id not in encontrados]
    if faltantes:
        raise HTTPException(status_code=400, detail=f"Servicios no registrados: {', '.join(faltantes)}")

    return servicios


def _calcular_precio_total(servicios: list[models.Servicio]) -> float:
    """Calcula el precio total de una cita sumando los precios de sus servicios."""
    return sum(servicio.precio for servicio in servicios)


@app.get("/")
def root():
    return {"message": "Bienvenido a la API de Gestión de Citas para la barberia"}


# --- Usuarios ---

@app.get("/usuarios/")
def listar_usuarios(db: Session = Depends(get_db)):
    # Ejecutamos la consulta SQL de lectura mapeada a través de SQLAlchemy
    usuarios = db.query(models.Usuario).all()
    return usuarios


@app.post("/usuarios/", response_model=schemas.UsuarioResponse)
def crear_usuario(usuario: schemas.UsuarioCreate, db: Session = Depends(get_db)):
    # Verificamos si el correo ya existe en la base de datos
    existing_usuario = db.query(models.Usuario).filter(models.Usuario.correo == usuario.correo).first()
    if existing_usuario:
        raise HTTPException(status_code=400, detail="El correo ya está registrado.")

    try:
        nuevo_usuario = models.Usuario(
            nombre=usuario.nombre,
            numero=usuario.numero,
            correo=usuario.correo
        )
        db.add(nuevo_usuario)
        db.commit()
        db.refresh(nuevo_usuario)
        return nuevo_usuario
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="El correo ya está registrado.")


@app.patch("/usuarios/{usuario_id}", response_model=schemas.UsuarioResponse)
def actualizar_usuario(usuario_id: str, usuario: schemas.UsuarioUpdate, db: Session = Depends(get_db)):
    usuario_db = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not usuario_db:
        raise HTTPException(status_code=404, detail="El usuario no está registrado.")

    if usuario.nombre is not None:
        usuario_db.nombre = usuario.nombre

    if usuario.numero is not None:
        usuario_db.numero = usuario.numero

    if usuario.correo is not None:
        correo_en_uso = db.query(models.Usuario).filter(
            models.Usuario.correo == usuario.correo, models.Usuario.id != usuario_id
        ).first()
        if correo_en_uso:
            raise HTTPException(status_code=400, detail="El correo ya está registrado.")
        usuario_db.correo = usuario.correo

    if usuario.rol is not None:
        if usuario.rol not in ("usuario", "barbero"):
            raise HTTPException(status_code=400, detail="El rol debe ser 'usuario' o 'barbero'.")
        usuario_db.rol = usuario.rol

    db.commit()
    db.refresh(usuario_db)
    return usuario_db


@app.delete("/usuarios/{usuario_id}")
def eliminar_usuario(usuario_id: str, db: Session = Depends(get_db)):
    usuario_db = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not usuario_db:
        raise HTTPException(status_code=404, detail="El usuario no está registrado.")

    try:
        db.delete(usuario_db)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="El usuario tiene citas registradas y no puede eliminarse.")

    return {"message": "Usuario eliminado correctamente"}


# --- Servicios ---

@app.get("/servicios/")
def listar_servicios(db: Session = Depends(get_db)):
    # Ejecutamos la consulta SQL de lectura mapeada a través de SQLAlchemy
    servicios = db.query(models.Servicio).all()
    return servicios


@app.post("/servicios/", response_model=schemas.ServicioResponse)
def crear_servicio(servicio: schemas.ServicioCreate, db: Session = Depends(get_db)):
    # Verificamos si el servicio ya existe en la base de datos
    existing_servicio = db.query(models.Servicio).filter(models.Servicio.nombre == servicio.nombre).first()
    if existing_servicio:
        raise HTTPException(status_code=400, detail="El servicio ya está registrado.")

    nuevo_servicio = models.Servicio(
        nombre=servicio.nombre,
        precio=servicio.precio,
        duracion_minutos=servicio.duracion_minutos
    )
    db.add(nuevo_servicio)
    db.commit()
    db.refresh(nuevo_servicio)
    return nuevo_servicio


@app.patch("/servicios/{servicio_id}", response_model=schemas.ServicioResponse)
def actualizar_servicio(servicio_id: str, servicio: schemas.ServicioUpdate, db: Session = Depends(get_db)):
    servicio_db = db.query(models.Servicio).filter(models.Servicio.id == servicio_id).first()
    if not servicio_db:
        raise HTTPException(status_code=404, detail="El servicio no está registrado.")

    if servicio.nombre is not None:
        servicio_existente = db.query(models.Servicio).filter(
            models.Servicio.nombre == servicio.nombre, models.Servicio.id != servicio_id
        ).first()
        if servicio_existente:
            raise HTTPException(status_code=400, detail="El nombre del servicio ya está registrado.")
        servicio_db.nombre = servicio.nombre

    if servicio.precio is not None:
        servicio_db.precio = servicio.precio

    if servicio.duracion_minutos is not None:
        servicio_db.duracion_minutos = servicio.duracion_minutos

    db.commit()

    # Si cambió el precio, recalculamos el precio_total de todas las citas que incluyen este servicio,
    # para que el valor desnormalizado no arrastre el precio anterior.
    if servicio.precio is not None:
        citas = db.query(models.Cita).join(
            models.CitaServicio, models.CitaServicio.cita_id == models.Cita.id
        ).filter(models.CitaServicio.servicio_id == servicio_id).all()

        for cita in citas:
            cita.precio_total = _calcular_precio_total(cita.servicios)

        db.commit()

    db.refresh(servicio_db)
    return servicio_db


@app.delete("/servicios/{servicio_id}")
def eliminar_servicio(servicio_id: str, db: Session = Depends(get_db)):
    servicio_db = db.query(models.Servicio).filter(models.Servicio.id == servicio_id).first()
    if not servicio_db:
        raise HTTPException(status_code=404, detail="El servicio no está registrado.")

    try:
        db.delete(servicio_db)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="El servicio está asociado a citas y no puede eliminarse.")

    return {"message": "Servicio eliminado correctamente"}


# --- Citas ---

@app.get("/citas/", response_model=list[schemas.CitaResponse])
def listar_citas(
    origen: str | None = Query(None, description="Filtra las citas por origen: 'usuario' o 'barbero'"),
    db: Session = Depends(get_db)
):
    """Lista las citas registradas. Si se indica 'origen', devuelve solo las creadas por ese tipo de cuenta."""
    consulta = db.query(models.Cita).options(selectinload(models.Cita.servicios))

    if origen is not None:
        if origen not in ("usuario", "barbero"):
            raise HTTPException(status_code=400, detail="El origen debe ser 'usuario' o 'barbero'.")
        consulta = consulta.filter(models.Cita.origen == origen)

    return consulta.all()


@app.post("/citas/", response_model=schemas.CitaResponse)
def crear_cita(cita: schemas.CitaCreate, db: Session = Depends(get_db)):
    # Validamos que el usuario ya existe en la base de datos
    existing_usuario = db.query(models.Usuario).filter(models.Usuario.id == cita.usuario_id).first()
    if not existing_usuario:
        raise HTTPException(status_code=400, detail="El usuario no está registrado.")

    # Validamos que todos los servicios existen y calculamos el precio total
    servicios = _obtener_servicios(db, cita.servicios_ids)

    # Verificamos si ya existe una cita para este usuario, en esta fecha, con este conjunto de servicios
    existing_cita = db.query(models.Cita).options(selectinload(models.Cita.servicios)).filter(
        models.Cita.usuario_id == cita.usuario_id,
        models.Cita.fecha_hora == cita.fecha_hora
    ).all()
    for candidate in existing_cita:
        ids_existentes = {servicio.id for servicio in candidate.servicios}
        if ids_existentes == set(cita.servicios_ids):
            raise HTTPException(status_code=400, detail="La cita ya está registrada.")

    # El origen por defecto es 'usuario'; solo se marca como 'barbero' si viene explícito
    if cita.origen is None:
        origen = db.query(models.Usuario).get(cita.usuario_id).rol
    else:
        origen = cita.origen
    if origen not in ("usuario", "barbero"):
        raise HTTPException(status_code=400, detail="El origen debe ser 'usuario' o 'barbero'.")

    nueva_cita = models.Cita(
        usuario_id=cita.usuario_id,
        fecha_hora=cita.fecha_hora,
        origen=origen,
        precio_total=_calcular_precio_total(servicios),
        servicios=servicios
    )

    try:
        db.add(nueva_cita)
        db.commit()
        db.refresh(nueva_cita)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="La cita ya está registrada.")

    return nueva_cita


@app.patch("/citas/{cita_id}", response_model=schemas.CitaResponse)
def actualizar_cita(cita_id: str, cita: schemas.CitaUpdate, db: Session = Depends(get_db)):
    # Verificamos si la cita existe en la base de datos
    existing_cita = db.query(models.Cita).filter(models.Cita.id == cita_id).first()
    if not existing_cita:
        raise HTTPException(status_code=404, detail="La cita no está registrada.")

    # Si se envía el conjunto de servicios, se reemplaza por completo y se recalcula el precio total
    if cita.servicios_ids is not None:
        servicios = _obtener_servicios(db, cita.servicios_ids)
        existing_cita.servicios = servicios
        existing_cita.precio_total = _calcular_precio_total(servicios)

    if cita.fecha_hora is not None:
        # Verificamos si la fecha y hora de la cita ya está ocupada por otra cita
        existing_cita_fecha = db.query(models.Cita).filter(
            models.Cita.fecha_hora == cita.fecha_hora, models.Cita.id != cita_id
        ).first()
        if existing_cita_fecha:
            raise HTTPException(status_code=400, detail="La fecha y hora de la cita ya está ocupada por otra cita.")

        # Verificamos si la fecha y hora de la cita coincide con la de otra cita del mismo usuario
        existing_cita_usuario = db.query(models.Cita).filter(
            models.Cita.usuario_id == existing_cita.usuario_id,
            models.Cita.fecha_hora == cita.fecha_hora,
            models.Cita.id != cita_id
        ).first()
        if existing_cita_usuario:
            raise HTTPException(status_code=400, detail="La fecha y hora de la cita ya está ocupada por otra cita del mismo usuario.")

        # Verificamos si la fecha y hora de la cita es anterior a la fecha y hora actual.
        # Se normaliza a naive porque el cliente puede enviar un timestamp con zona horaria y
        # compararlo contra datetime.now() (naive) lanza TypeError.
        fecha_hora = cita.fecha_hora
        if fecha_hora.tzinfo is not None:
            fecha_hora = fecha_hora.astimezone().replace(tzinfo=None)

        if fecha_hora < datetime.now():
            raise HTTPException(status_code=400, detail="La fecha y hora de la cita no puede ser anterior a la fecha y hora actual.")

        existing_cita.fecha_hora = fecha_hora

    if cita.estado is not None:
        existing_cita.estado = cita.estado

    db.commit()
    db.refresh(existing_cita)
    return existing_cita


@app.delete("/citas/{cita_id}")
def eliminar_cita(cita_id: str, db: Session = Depends(get_db)):
    # Verificamos si la cita existe en la base de datos
    existing_cita = db.query(models.Cita).filter(models.Cita.id == cita_id).first()
    if not existing_cita:
        raise HTTPException(status_code=404, detail="La cita no está registrada.")

    db.delete(existing_cita)
    db.commit()

    return {"message": "Cita eliminada correctamente"}