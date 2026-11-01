from datetime import date, datetime

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from .. import autenticador, models, schemas, utilidades

router = APIRouter(prefix="/citas", tags=["Citas"])


@router.get("/", response_model=list[schemas.CitaResponse])
def listar_citas(
    *,
    fecha_desde: date | datetime | None = Query(
        None,
        description=(
            "Filtra las citas desde esta fecha (inclusive). Si se envía como "
            "fecha sin hora, cubre el día completo"
        ),
    ),
    fecha_hasta: date | datetime | None = Query(
        None,
        description=(
            "Filtra las citas hasta esta fecha (inclusive). Si se envía como "
            "fecha sin hora, cubre el día completo"
        ),
    ),
    estado: str | None = Query(
        None,
        description=(
            "Filtra las citas por estado: 'pendiente', 'confirmada', "
            "'cancelada' o 'terminada'"
        ),
    ),
    usuario_id: str | None = Query(None, description="Filtra las citas por usuario"),
    origen: str | None = Query(
        None,
        description="Filtra las citas por origen: 'usuario' o 'barbero'",
    ),
    limit: int = Query(100, ge=1, le=500, description="Máximo de citas a devolver"),
    offset: int = Query(0, ge=0, description="Desplazamiento para paginación"),
    db: autenticador.SesionDB,
    current_user: autenticador.UsuarioActual,
):
    """Lista las citas ordenadas por fecha, limitadas al alcance del usuario."""
    utilidades.validar_filtros_citas(db, origen, estado, usuario_id)

    if current_user.rol == utilidades.ROL_USUARIO:
        if usuario_id is not None and usuario_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="No puedes consultar citas de otro usuario.",
            )
        usuario_id = current_user.id

    inicio, fin = utilidades.resolver_rango_fechas(fecha_desde, fecha_hasta)

    consulta = db.query(models.Cita).options(selectinload(models.Cita.servicios))

    if origen is not None:
        consulta = consulta.filter(models.Cita.origen == origen)

    if estado is not None:
        consulta = consulta.filter(models.Cita.estado == estado)

    if usuario_id is not None:
        consulta = consulta.filter(models.Cita.usuario_id == usuario_id)

    if inicio is not None:
        consulta = consulta.filter(models.Cita.fecha_hora >= inicio)

    if fin is not None:
        consulta = consulta.filter(models.Cita.fecha_hora <= fin)

    consulta = consulta.order_by(
        models.Cita.fecha_hora.asc(),
        models.Cita.id.asc(),
    )

    return consulta.offset(offset).limit(limit).all()


@router.post(
    "/",
    response_model=schemas.CitaResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_cita(
    cita: schemas.CitaCreate,
    db: autenticador.SesionDB,
    current_user: autenticador.UsuarioActual,
):
    existing_usuario = db.query(models.Usuario).filter(
        models.Usuario.id == cita.usuario_id
    ).first()
    if existing_usuario is None:
        raise HTTPException(status_code=400, detail="El usuario no está registrado.")

    utilidades.exigir_propietario(
        current_user,
        cita.usuario_id,
        "No puedes crear citas para otro usuario.",
    )
    servicios = utilidades.obtener_servicios(db, cita.servicios_ids)
    fecha_hora = utilidades.normalizar_naive(cita.fecha_hora)

    if utilidades.existe_cita_duplicada(
        db, cita.usuario_id, fecha_hora, cita.servicios_ids
    ):
        raise HTTPException(status_code=400, detail="La cita ya está registrada.")

    origen = utilidades.resolver_origen(cita.origen, current_user)
    duracion_total = utilidades.calcular_duracion_total(servicios)

    if utilidades.hay_solapamiento(db, fecha_hora, duracion_total):
        raise HTTPException(
            status_code=400,
            detail="La cita se solapa con otra cita existente.",
        )

    nueva_cita = models.Cita(
        usuario_id=cita.usuario_id,
        fecha_hora=fecha_hora,
        origen=origen,
        precio_total=utilidades.calcular_precio_total(servicios),
        servicios=servicios,
    )

    try:
        db.add(nueva_cita)
        db.commit()
        db.refresh(nueva_cita)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="La cita ya está registrada.")

    return nueva_cita


@router.patch("/{cita_id}", response_model=schemas.CitaResponse)
def actualizar_cita(
    cita_id: str,
    cita: schemas.CitaUpdate,
    db: autenticador.SesionDB,
    current_user: autenticador.UsuarioActual,
):
    existing_cita = utilidades.obtener_o_404(
        db, models.Cita, cita_id, "La cita no está registrada."
    )

    utilidades.exigir_propietario(
        current_user,
        existing_cita.usuario_id,
        "No puedes modificar citas de otro usuario.",
    )

    if cita.estado is not None and cita.estado not in utilidades.ESTADOS_CITA:
        raise HTTPException(
            status_code=400,
            detail=utilidades.MENSAJE_ESTADO_INVALIDO,
        )

    fecha_final = existing_cita.fecha_hora
    if cita.fecha_hora is not None:
        fecha_final = utilidades.validar_nueva_fecha(
            db, existing_cita, cita.fecha_hora
        )

    servicios_finales = existing_cita.servicios
    if cita.servicios_ids is not None:
        servicios_finales = utilidades.obtener_servicios(db, cita.servicios_ids)
        existing_cita.servicios = servicios_finales
        existing_cita.precio_total = utilidades.calcular_precio_total(
            servicios_finales
        )

    if cita.fecha_hora is not None or cita.servicios_ids is not None:
        duracion_total = utilidades.calcular_duracion_total(servicios_finales)
        if utilidades.hay_solapamiento(
            db, fecha_final, duracion_total, excluir_id=cita_id
        ):
            db.rollback()
            raise HTTPException(
                status_code=400,
                detail="La cita se solapa con otra cita existente.",
            )

    if cita.fecha_hora is not None:
        existing_cita.fecha_hora = fecha_final

    if cita.estado is not None:
        existing_cita.estado = cita.estado

    db.commit()
    db.refresh(existing_cita)
    return existing_cita


@router.delete("/{cita_id}")
def eliminar_cita(
    cita_id: str,
    db: autenticador.SesionDB,
    current_user: autenticador.UsuarioActual,
):
    existing_cita = utilidades.obtener_o_404(
        db, models.Cita, cita_id, "La cita no está registrada."
    )

    utilidades.exigir_propietario(
        current_user,
        existing_cita.usuario_id,
        "No puedes eliminar citas de otro usuario.",
    )

    db.delete(existing_cita)
    db.commit()

    return {"message": "Cita eliminada correctamente"}
