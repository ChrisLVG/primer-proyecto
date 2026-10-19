from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional


# --- Usuarios ---

class UsuarioCreate(BaseModel):
    nombre: str = Field(..., description="El nombre del usuario")
    numero: str = Field(..., description="El número de teléfono del usuario")
    correo: str = Field(..., description="El correo electrónico del usuario")


class UsuarioUpdate(BaseModel):
    nombre: str | None = None
    numero: str | None = None
    correo: str | None = None
    rol: str | None = None


class UsuarioDelete(BaseModel):
    id: str = Field(..., description="El identificador único del usuario")


class UsuarioResponse(UsuarioCreate):
    id: str = Field(..., description="El identificador único del usuario")
    rol: str = Field(..., description="El rol del usuario: 'usuario' o 'barbero'")

    model_config = ConfigDict(from_attributes=True)


# --- Servicios ---

class ServicioCreate(BaseModel):
    nombre: str = Field(..., description="El nombre del servicio")
    precio: float = Field(..., description="El precio del servicio")
    duracion_minutos: int = Field(..., description="La duración del servicio en minutos")


class ServicioUpdate(BaseModel):
    nombre: str | None = None
    precio: float | None = None
    duracion_minutos: int | None = None


class ServicioDelete(BaseModel):
    id: str = Field(..., description="El identificador único del servicio")


class ServicioResponse(ServicioCreate):
    id: str = Field(..., description="El identificador único del servicio")

    model_config = ConfigDict(from_attributes=True)


# --- Citas ---

class CitaCreate(BaseModel):
    usuario_id: str = Field(..., description="El ID del usuario que agendas la cita")
    servicios_ids: list[str] = Field(..., min_length=1, description="Los IDs de los servicios incluidos en la cita")
    fecha_hora: datetime = Field(..., description="La fecha y hora de la cita")
    origen: Optional[str] | None= None  # Puede ser 'usuario' o 'barbero'; si no se envía, se determina automáticamente


class CitaUpdate(BaseModel):
    servicios_ids: list[str] | None = Field(None, min_length=1, description="Los IDs de los servicios; si se envía, reemplaza el conjunto completo")
    fecha_hora: datetime | None = None
    estado: str | None = None


class CitaDelete(BaseModel):
    id: str = Field(..., description="El identificador único de la cita")


class CitaResponse(BaseModel):
    id: str = Field(..., description="El identificador único de la cita")
    usuario_id: str = Field(..., description="El ID del usuario de la cita")
    servicios: list[ServicioResponse] = Field(..., description="Los servicios incluidos en la cita")
    fecha_hora: datetime = Field(..., description="La fecha y hora de la cita")
    estado: str = Field(..., description="El estado de la cita")
    origen: str = Field(..., description="El origen de la cita: 'usuario' o 'barbero'")
    precio_total: float = Field(..., description="La suma de los precios de los servicios de la cita")

    model_config = ConfigDict(from_attributes=True)