from datetime import date, datetime, time, timedelta
from typing import Literal, TypeVar

from fastapi import HTTPException
from sqlalchemy.orm import Session, selectinload

from . import models

ROL_USUARIO = "usuario"
ROL_BARBERO = "barbero"
ROLES = (ROL_USUARIO, ROL_BARBERO)

ESTADOS_CITA = ("pendiente", "confirmada", "cancelada", "terminada")
ESTADOS_ACTIVOS = ("pendiente", "confirmada")
ORIGENES_CITA = (ROL_USUARIO, ROL_BARBERO)
MENSAJE_ESTADO_INVALIDO = "El estado debe ser uno de: pendiente, confirmada, cancelada, terminada."

ModeloORM = TypeVar(
    "ModeloORM",
    models.Usuario,
    models.Servicio,
    models.Cita,
)


def obtener_o_404(
    db: Session,
    modelo: type[ModeloORM],
    objeto_id: str,
    mensaje: str,
) -> ModeloORM:
    """Obtiene un registro por ID o responde con el mensaje 404 indicado."""
    objeto = db.query(modelo).filter(modelo.id == objeto_id).first()
    if objeto is None:
        raise HTTPException(status_code=404, detail=mensaje)
    return objeto


def exigir_propietario(
    current_user: models.Usuario,
    propietario_id: str,
    mensaje: str,
) -> None:
    """Lanza 403 si un usuario intenta operar sobre datos ajenos."""
    if current_user.rol == ROL_USUARIO and propietario_id != current_user.id:
        raise HTTPException(status_code=403, detail=mensaje)


def obtener_servicios(
    db: Session,
    servicios_ids: list[str],
) -> list[models.Servicio]:
    """Valida que los IDs sean únicos y existan; devuelve los servicios solicitados."""
    if len(set(servicios_ids)) != len(servicios_ids):
        raise HTTPException(
            status_code=400,
            detail="La lista de servicios contiene IDs duplicados.",
        )

    servicios = db.query(models.Servicio).filter(
        models.Servicio.id.in_(servicios_ids)
    ).all()
    encontrados = {servicio.id for servicio in servicios}
    faltantes = [
        servicio_id
        for servicio_id in servicios_ids
        if servicio_id not in encontrados
    ]
    if faltantes:
        raise HTTPException(
            status_code=400,
            detail=f"Servicios no registrados: {', '.join(faltantes)}",
        )

    return servicios


def calcular_precio_total(servicios: list[models.Servicio]) -> float:
    """Calcula el precio de una cita sumando los precios de sus servicios."""
    return sum(servicio.precio for servicio in servicios)


def calcular_duracion_total(servicios: list[models.Servicio]) -> int:
    """Calcula la duración de una cita sumando la duración de sus servicios."""
    return sum(servicio.duracion_minutos for servicio in servicios)


def hay_solapamiento(
    db: Session,
    inicio: datetime,
    duracion_minutos: int,
    excluir_id: str | None = None,
) -> bool:
    """Indica si una cita activa se solapa con el intervalo propuesto."""
    fin = inicio + timedelta(minutes=duracion_minutos)
    candidatas = db.query(models.Cita).options(
        selectinload(models.Cita.servicios)
    ).filter(models.Cita.estado.in_(ESTADOS_ACTIVOS)).all()

    for cita in candidatas:
        if excluir_id is not None and cita.id == excluir_id:
            continue

        inicio_existente = cita.fecha_hora
        fin_existente = inicio_existente + timedelta(
            minutes=calcular_duracion_total(cita.servicios)
        )
        if inicio < fin_existente and inicio_existente < fin:
            return True

    return False


def normalizar_naive(fecha_hora: datetime) -> datetime:
    """Normaliza datetimes con zona a la hora local naive usada por la base."""
    if fecha_hora.tzinfo is not None:
        return fecha_hora.astimezone().replace(tzinfo=None)
    return fecha_hora


def limite_de_fecha(
    fecha: date | datetime,
    extremo: Literal["inicio", "fin"],
    dia_completo: bool = False,
) -> datetime:
    """Devuelve el límite de fecha exacto o el inicio/fin de su día."""
    hora = time.min if extremo == "inicio" else time.max
    if isinstance(fecha, datetime):
        if not dia_completo:
            return normalizar_naive(fecha)
        dia = fecha.astimezone().date() if fecha.tzinfo is not None else fecha.date()
    else:
        dia = fecha
    return datetime.combine(dia, hora)


def resolver_rango_fechas(
    desde: date | datetime | None,
    hasta: date | datetime | None,
) -> tuple[datetime | None, datetime | None]:
    """Resuelve el rango solicitado y rechaza los límites invertidos."""
    if desde is not None and hasta is not None:
        inicio = limite_de_fecha(desde, "inicio")
        fin = limite_de_fecha(hasta, "fin")
    elif desde is not None:
        inicio = limite_de_fecha(desde, "inicio", dia_completo=True)
        fin = limite_de_fecha(desde, "fin", dia_completo=True)
    elif hasta is not None:
        inicio = limite_de_fecha(hasta, "inicio", dia_completo=True)
        fin = limite_de_fecha(hasta, "fin", dia_completo=True)
    else:
        return None, None

    if inicio > fin:
        raise HTTPException(
            status_code=400,
            detail=(
                "El rango de fechas es inválido: la fecha inicial no puede ser "
                "posterior a la fecha final."
            ),
        )
    return inicio, fin


def validar_filtros_citas(
    db: Session,
    origen: str | None,
    estado: str | None,
    usuario_id: str | None,
) -> None:
    """Valida origen, estado y existencia de usuario en el orden de la API."""
    if origen is not None and origen not in ORIGENES_CITA:
        raise HTTPException(
            status_code=400,
            detail="El origen debe ser 'usuario' o 'barbero'.",
        )

    if estado is not None and estado not in ESTADOS_CITA:
        raise HTTPException(status_code=400, detail=MENSAJE_ESTADO_INVALIDO)

    if usuario_id is not None:
        existing_usuario = db.query(models.Usuario).filter(
            models.Usuario.id == usuario_id
        ).first()
        if existing_usuario is None:
            raise HTTPException(
                status_code=400,
                detail="El usuario no está registrado.",
            )


def existe_cita_duplicada(
    db: Session,
    usuario_id: str,
    fecha_hora: datetime,
    servicios_ids: list[str],
) -> bool:
    """Indica si existe la misma combinación de servicios para esa fecha y usuario."""
    citas_existentes = db.query(models.Cita).options(
        selectinload(models.Cita.servicios)
    ).filter(
        models.Cita.usuario_id == usuario_id,
        models.Cita.fecha_hora == fecha_hora,
    ).all()
    servicios_solicitados = set(servicios_ids)
    return any(
        {servicio.id for servicio in cita.servicios} == servicios_solicitados
        for cita in citas_existentes
    )


def resolver_origen(
    origen_enviado: str | None,
    current_user: models.Usuario,
) -> str:
    """Resuelve el origen según el rol autenticado o rechaza uno incompatible."""
    if origen_enviado is None:
        return current_user.rol
    if origen_enviado != current_user.rol:
        raise HTTPException(
            status_code=400,
            detail="El origen no corresponde al rol del usuario autenticado.",
        )
    return origen_enviado


def validar_nueva_fecha(
    db: Session,
    cita_existente: models.Cita,
    fecha_hora: datetime,
) -> datetime:
    """Normaliza y valida una nueva fecha conservando el orden de errores actual."""
    fecha_normalizada = normalizar_naive(fecha_hora)

    cita_en_fecha = db.query(models.Cita).filter(
        models.Cita.fecha_hora == fecha_normalizada,
        models.Cita.id != cita_existente.id,
    ).first()
    if cita_en_fecha:
        raise HTTPException(
            status_code=400,
            detail="La fecha y hora de la cita ya está ocupada por otra cita.",
        )

    cita_usuario_en_fecha = db.query(models.Cita).filter(
        models.Cita.usuario_id == cita_existente.usuario_id,
        models.Cita.fecha_hora == fecha_normalizada,
        models.Cita.id != cita_existente.id,
    ).first()
    if cita_usuario_en_fecha:
        raise HTTPException(
            status_code=400,
            detail=(
                "La fecha y hora de la cita ya está ocupada por otra cita "
                "del mismo usuario."
            ),
        )

    if fecha_normalizada < datetime.now():
        raise HTTPException(
            status_code=400,
            detail=(
                "La fecha y hora de la cita no puede ser anterior a la fecha "
                "y hora actual."
            ),
        )

    return fecha_normalizada


def eliminar_dependencias_de_usuario(db: Session, usuario_id: str) -> None:
    """Elimina citas, asociaciones y sesiones sin confirmar la transacción."""
    citas_ids = [
        cita_id
        for (cita_id,) in db.query(models.Cita.id).filter(
            models.Cita.usuario_id == usuario_id
        ).all()
    ]
    if citas_ids:
        db.query(models.CitaServicio).filter(
            models.CitaServicio.cita_id.in_(citas_ids)
        ).delete(synchronize_session=False)
        db.query(models.Cita).filter(
            models.Cita.id.in_(citas_ids)
        ).delete(synchronize_session=False)

    db.query(models.Sesion).filter(
        models.Sesion.usuario_id == usuario_id
    ).delete(synchronize_session=False)


def retirar_servicio_de_citas(
    db: Session,
    servicio_id: str,
    citas: list[models.Cita],
) -> None:
    """Retira el servicio; elimina citas vacías y recalcula el precio restante."""
    for cita in citas:
        servicios_restantes = [
            servicio for servicio in cita.servicios if servicio.id != servicio_id
        ]
        if not servicios_restantes:
            db.delete(cita)
            continue

        cita.servicios = servicios_restantes
        cita.precio_total = calcular_precio_total(servicios_restantes)
