import bcrypt
import hashlib
import secrets
from typing import Annotated
from fastapi import FastAPI, Depends, HTTPException, Query, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload
from datetime import date, datetime, time, timedelta

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


def _calcular_duracion_total(servicios: list[models.Servicio]) -> int:
    """Calcula la duración total de una cita sumando las duraciones de sus servicios."""
    return sum(servicio.duracion_minutos for servicio in servicios)


def _hay_solapamiento(
    db: Session,
    inicio: datetime,
    duracion_minutos: int,
    excluir_id: str | None = None,
) -> bool:
    """Indica si existe una cita activa cuyo intervalo se solapa con el propuesto.

    Una cita ocupa el intervalo [inicio, inicio + duración_total). Dos citas se solapan si
    (inicio_nuevo < fin_existente) Y (inicio_existente < fin_nuevo). El intervalo es abierto por
    la derecha: una cita que termina a las 10:30 no bloquea otra que empiece a las 10:30.

    Solo se consideran las citas activas (pendiente o confirmada): las canceladas y terminadas
    liberan el hueco.
    """
    fin = inicio + timedelta(minutes=duracion_minutos)

    candidatas = db.query(models.Cita).options(
        selectinload(models.Cita.servicios)
    ).filter(models.Cita.estado.in_(("pendiente", "confirmada"))).all()

    for cita in candidatas:
        # Al actualizar una cita, la propia no debe contarse como solapamiento consigo misma
        if excluir_id is not None and cita.id == excluir_id:
            continue

        inicio_existente = cita.fecha_hora
        fin_existente = inicio_existente + timedelta(
            minutes=_calcular_duracion_total(cita.servicios)
        )

        if inicio < fin_existente and inicio_existente < fin:
            return True

    return False


def _normalizar_naive(fecha_hora: datetime) -> datetime:
    """Convierte un datetime con zona horaria a naive (UTC local), para poder compararlo.

    Las citas se almacenan naive en la base de datos. Comparar un datetime aware contra uno naive
    lanza TypeError, por lo que se normaliza siempre antes de comparar o almacenar.
    """
    if fecha_hora.tzinfo is not None:
        return fecha_hora.astimezone().replace(tzinfo=None)
    return fecha_hora


def _a_inicio_del_dia(fecha: datetime | date) -> datetime:
    """Convierte una fecha en el instante inicial de ese día (00:00:00).

    Si ya es un datetime con hora, se devuelve ese instante exacto (normalizado a naive).
    """
    if isinstance(fecha, datetime):
        return _normalizar_naive(fecha)
    return datetime.combine(fecha, time.min)


def _a_fin_del_dia(fecha: datetime | date) -> datetime:
    """Convierte una fecha en el instante final de ese día (23:59:59.999999).

    Si ya es un datetime con hora, se devuelve ese instante exacto (normalizado a naive).
    """
    if isinstance(fecha, datetime):
        return _normalizar_naive(fecha)
    return datetime.combine(fecha, time.max)


def _a_fin_del_dia_de(fecha: datetime | date) -> datetime:
    """Devuelve el último instante del día de la fecha indicada, ignorando la hora que traiga."""
    if isinstance(fecha, datetime):
        dia = fecha.astimezone().date() if fecha.tzinfo is not None else fecha.date()
    else:
        dia = fecha
    return datetime.combine(dia, time.max)


def _a_inicio_del_dia_de(fecha: datetime | date) -> datetime:
    """Devuelve el primer instante del día de la fecha indicada, ignorando la hora que traiga."""
    if isinstance(fecha, datetime):
        dia = fecha.astimezone().date() if fecha.tzinfo is not None else fecha.date()
    else:
        dia = fecha
    return datetime.combine(dia, time.min)


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

        db.delete(usuario_db)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="No se pudo eliminar el usuario debido a una relación existente.",
        )

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

    citas_afectadas = db.query(models.Cita).join(
        models.CitaServicio, models.CitaServicio.cita_id == models.Cita.id
    ).options(
        selectinload(models.Cita.servicios)
    ).filter(models.CitaServicio.servicio_id == servicio_id).all()

    try:
        for cita in citas_afectadas:
            servicios_restantes = [
                servicio for servicio in cita.servicios if servicio.id != servicio_id
            ]

            if not servicios_restantes:
                db.delete(cita)
                continue

            cita.servicios = servicios_restantes
            cita.precio_total = _calcular_precio_total(servicios_restantes)

        db.delete(servicio_db)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="No se pudo eliminar el servicio debido a una relación existente.",
        )

    return {"message": "Servicio eliminado correctamente"}


# --- Citas ---

@app.get("/citas/", response_model=list[schemas.CitaResponse])
def listar_citas(
    fecha_desde: date | datetime | None = Query(
        None, description="Filtra las citas desde esta fecha (inclusive). Si se envía como fecha sin hora, cubre el día completo"
    ),
    fecha_hasta: date | datetime | None = Query(
        None, description="Filtra las citas hasta esta fecha (inclusive). Si se envía como fecha sin hora, cubre el día completo"
    ),
    estado: str | None = Query(
        None, description="Filtra las citas por estado: 'pendiente', 'confirmada', 'cancelada' o 'terminada'"
    ),
    usuario_id: str | None = Query(None, description="Filtra las citas por usuario"),
    origen: str | None = Query(None, description="Filtra las citas por origen: 'usuario' o 'barbero'"),
    limit: int = Query(100, ge=1, le=500, description="Máximo de citas a devolver"),
    offset: int = Query(0, ge=0, description="Desplazamiento para paginación"),
    db: Session = Depends(get_db)
):
    """Lista las citas registradas, ordenadas por fecha ascendente.

    Todos los filtros son opcionales y se combinan entre sí (AND). Si no se indica ninguno,
    devuelve todas las citas.
    """
    # Validamos los filtros antes de consultar para no devolver datos con parámetros inválidos
    if origen is not None and origen not in ("usuario", "barbero"):
        raise HTTPException(status_code=400, detail="El origen debe ser 'usuario' o 'barbero'.")

    if estado is not None and estado not in ("pendiente", "confirmada", "cancelada", "terminada"):
        raise HTTPException(
            status_code=400,
            detail="El estado debe ser uno de: pendiente, confirmada, cancelada, terminada."
        )

    if usuario_id is not None:
        existing_usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
        if not existing_usuario:
            raise HTTPException(status_code=400, detail="El usuario no está registrado.")

    # Convertimos las fechas al instante correspondiente. Si solo se envía uno de los dos extremos,
    # se cubre el día completo de esa fecha; si se envían ambos, se cubren los días completos de
    # cada extremo y las citas intermedias.
    if fecha_desde is not None and fecha_hasta is not None:
        inicio = _a_inicio_del_dia(fecha_desde)
        fin = _a_fin_del_dia(fecha_hasta)
    elif fecha_desde is not None:
        inicio = _a_inicio_del_dia_de(fecha_desde)
        fin = _a_fin_del_dia_de(fecha_desde)
    elif fecha_hasta is not None:
        inicio = _a_inicio_del_dia_de(fecha_hasta)
        fin = _a_fin_del_dia_de(fecha_hasta)
    else:
        inicio = None
        fin = None

    if inicio is not None and fin is not None and inicio > fin:
        raise HTTPException(
            status_code=400,
            detail="El rango de fechas es inválido: la fecha inicial no puede ser posterior a la final."
        )

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

    # El id actúa de desempate para que la paginación sea estable cuando varias citas coinciden
    # en la misma fecha y hora
    consulta = consulta.order_by(models.Cita.fecha_hora.asc(), models.Cita.id.asc())

    return consulta.offset(offset).limit(limit).all()


@app.post("/citas/", response_model=schemas.CitaResponse)
def crear_cita(cita: schemas.CitaCreate, db: Session = Depends(get_db)):
    # Validamos que el usuario ya existe en la base de datos
    existing_usuario = db.query(models.Usuario).filter(models.Usuario.id == cita.usuario_id).first()
    if not existing_usuario:
        raise HTTPException(status_code=400, detail="El usuario no está registrado.")

    # Validamos que todos los servicios existen y calculamos el precio total
    servicios = _obtener_servicios(db, cita.servicios_ids)

    # Normalizamos la fecha a naive para compararla de forma consistente con lo almacenado
    fecha_hora = _normalizar_naive(cita.fecha_hora)

    # Verificamos si ya existe una cita para este usuario, en esta fecha, con este conjunto de servicios
    existing_cita = db.query(models.Cita).options(selectinload(models.Cita.servicios)).filter(
        models.Cita.usuario_id == cita.usuario_id,
        models.Cita.fecha_hora == fecha_hora
    ).all()
    for candidate in existing_cita:
        ids_existentes = {servicio.id for servicio in candidate.servicios}
        if ids_existentes == set(cita.servicios_ids):
            raise HTTPException(status_code=400, detail="La cita ya está registrada.")

    # El origen por defecto se determina según el rol del usuario; si viene explícito, se respeta
    if cita.origen is None:
        origen = existing_usuario.rol
    else:
        origen = cita.origen
    if origen not in ("usuario", "barbero"):
        raise HTTPException(status_code=400, detail="El origen debe ser 'usuario' o 'barbero'.")

    # Verificamos que la cita no se solape con ninguna otra cita activa. La cita ocupa el
    # intervalo [fecha_hora, fecha_hora + duración total de sus servicios).
    duracion_total = _calcular_duracion_total(servicios)

    if _hay_solapamiento(db, fecha_hora, duracion_total):
        raise HTTPException(status_code=400, detail="La cita se solapa con otra cita existente.")

    nueva_cita = models.Cita(
        usuario_id=cita.usuario_id,
        fecha_hora=fecha_hora,
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

    # El estado solo admite los cuatro valores previstos; se valida aquí para devolver 400
    # en lugar del 422 que generaría el esquema.
    if cita.estado is not None and cita.estado not in ("pendiente", "confirmada", "cancelada", "terminada"):
        raise HTTPException(
            status_code=400,
            detail="El estado debe ser uno de: pendiente, confirmada, cancelada, terminada."
        )

    # Determinamos la fecha final de la cita: la actual o la nueva, ya normalizada a naive.
    fecha_final = existing_cita.fecha_hora

    if cita.fecha_hora is not None:
        fecha_hora = _normalizar_naive(cita.fecha_hora)

        # Verificamos si la fecha y hora de la cita ya está ocupada por otra cita
        existing_cita_fecha = db.query(models.Cita).filter(
            models.Cita.fecha_hora == fecha_hora, models.Cita.id != cita_id
        ).first()
        if existing_cita_fecha:
            raise HTTPException(status_code=400, detail="La fecha y hora de la cita ya está ocupada por otra cita.")

        # Verificamos si la fecha y hora de la cita coincide con la de otra cita del mismo usuario
        existing_cita_usuario = db.query(models.Cita).filter(
            models.Cita.usuario_id == existing_cita.usuario_id,
            models.Cita.fecha_hora == fecha_hora,
            models.Cita.id != cita_id
        ).first()
        if existing_cita_usuario:
            raise HTTPException(status_code=400, detail="La fecha y hora de la cita ya está ocupada por otra cita del mismo usuario.")

        # Verificamos si la fecha y hora de la cita es anterior a la fecha y hora actual
        if fecha_hora < datetime.now():
            raise HTTPException(status_code=400, detail="La fecha y hora de la cita no puede ser anterior a la fecha y hora actual.")

        fecha_final = fecha_hora

    # Si se envía el conjunto de servicios, se reemplaza por completo y se recalcula el precio total
    servicios_finales = existing_cita.servicios

    if cita.servicios_ids is not None:
        servicios = _obtener_servicios(db, cita.servicios_ids)
        servicios_finales = servicios
        existing_cita.servicios = servicios
        existing_cita.precio_total = _calcular_precio_total(servicios)

    # Verificamos el solapamiento con la combinación final de fecha y servicios. Solo se comprueba
    # si la cita cambia de fecha o de servicios; un cambio de estado no altera su intervalo.
    if cita.fecha_hora is not None or cita.servicios_ids is not None:
        duracion_total = _calcular_duracion_total(servicios_finales)

        if _hay_solapamiento(db, fecha_final, duracion_total, excluir_id=cita_id):
            # Descartamos los cambios ya aplicados en memoria para no dejar la sesión inconsistente
            db.rollback()
            raise HTTPException(status_code=400, detail="La cita se solapa con otra cita existente.")

    if cita.fecha_hora is not None:
        existing_cita.fecha_hora = fecha_final

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


security = HTTPBearer(auto_error=False)


# --- Autenticación ---

@app.post(
    "/auth/register",
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


def _hash_token(token: str) -> str:
    """Devuelve el hash SHA-256 hexadecimal del token opaco.

    El token opaco nunca se almacena en texto plano; solo se guarda su hash
    en la tabla ``sesiones`` para poder localizarlo sin exponerlo.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _crear_sesion(db: Session, usuario_id: str) -> str:
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


def _obtener_sesion_valida(db: Session, token: str) -> models.Sesion:
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
) -> models.Usuario:
    """Devuelve el usuario autenticado a partir del token Bearer.

    Si no se envía token, lanza 401 "No autenticado.". Si la sesión no existe
    o ha expirado, `_obtener_sesion_valida` lanza el 401 correspondiente.
    Devuelve el modelo `Usuario` asociado a la sesión válida.
    """
    if token is None:
        raise HTTPException(status_code=401, detail="No autenticado.")

    sesion = _obtener_sesion_valida(db, token.credentials)
    return sesion.usuario


def require_rol(rol_requerido: str):
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


@app.post("/auth/login", response_model=schemas.AuthResponse)
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


@app.post("/auth/logout", response_model=schemas.LogoutResponse)
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