from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from .. import autenticador, models, schemas, utilidades

router = APIRouter(prefix="/servicios", tags=["Servicios"])


@router.get("/")
def listar_servicios(db: autenticador.SesionDB):
    servicios = db.query(models.Servicio).all()
    return servicios


@router.post(
    "/",
    response_model=schemas.ServicioResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_servicio(
    servicio: schemas.ServicioCreate,
    db: autenticador.SesionDB,
    _barbero: autenticador.SoloBarbero,
):
    existing_servicio = db.query(models.Servicio).filter(
        models.Servicio.nombre == servicio.nombre
    ).first()
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


@router.patch("/{servicio_id}", response_model=schemas.ServicioResponse)
def actualizar_servicio(
    servicio_id: str,
    servicio: schemas.ServicioUpdate,
    db: autenticador.SesionDB,
    _barbero: autenticador.SoloBarbero,
):
    servicio_db = utilidades.obtener_o_404(
        db, models.Servicio, servicio_id, "El servicio no está registrado."
    )

    if servicio.nombre is not None:
        servicio_existente = db.query(models.Servicio).filter(
            models.Servicio.nombre == servicio.nombre,
            models.Servicio.id != servicio_id,
        ).first()
        if servicio_existente:
            raise HTTPException(
                status_code=400,
                detail="El nombre del servicio ya está registrado.",
            )
        servicio_db.nombre = servicio.nombre

    if servicio.precio is not None:
        servicio_db.precio = servicio.precio

    if servicio.duracion_minutos is not None:
        servicio_db.duracion_minutos = servicio.duracion_minutos

    db.commit()

    # Recalcula el precio desnormalizado si cambió el precio del servicio.
    if servicio.precio is not None:
        citas = db.query(models.Cita).join(
            models.CitaServicio, models.CitaServicio.cita_id == models.Cita.id
        ).filter(models.CitaServicio.servicio_id == servicio_id).all()

        for cita in citas:
            cita.precio_total = utilidades.calcular_precio_total(cita.servicios)

        db.commit()

    db.refresh(servicio_db)
    return servicio_db


@router.delete("/{servicio_id}")
def eliminar_servicio(
    servicio_id: str,
    db: autenticador.SesionDB,
    _barbero: autenticador.SoloBarbero,
):
    servicio_db = utilidades.obtener_o_404(
        db, models.Servicio, servicio_id, "El servicio no está registrado."
    )

    citas_afectadas = db.query(models.Cita).join(
        models.CitaServicio, models.CitaServicio.cita_id == models.Cita.id
    ).options(
        selectinload(models.Cita.servicios)
    ).filter(models.CitaServicio.servicio_id == servicio_id).all()

    try:
        utilidades.retirar_servicio_de_citas(db, servicio_id, citas_afectadas)
        db.delete(servicio_db)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="No se pudo eliminar el servicio debido a una relación existente.",
        )

    return {"message": "Servicio eliminado correctamente"}
