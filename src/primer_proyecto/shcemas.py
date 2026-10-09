from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
class User(BaseModel):
    nombre: str = Field(..., description="The name of the user")
    numero: str = Field(..., description="The phone number of the user")
    correo: str = Field(..., description="The email address of the user")

class UserUpdate(BaseModel):
    nombre: Optional[str] = None
    numero: Optional[str] = None
    correo: Optional[str] = None

class userresponse(User):
    id: str = Field(..., description="The unique identifier of the user")

    class Config:
        from_attributes = True


class service(BaseModel):
    nombre: str = Field(..., description="The name of the service")
    precio: float = Field(..., description="The price of the service")
    duracion_minutos: int = Field(..., description="The duration of the service in minutes")

class ServiceUpdate(BaseModel):
    nombre: Optional[str] = None
    precio: Optional[float] = None
    duracion_minutos: Optional[int] = None

class serviceResponse(service):
    id: str = Field(..., description="The unique identifier of the service")

    class Config:
        from_attributes = True

class date(BaseModel):
    cliente_id: str = Field(..., description="The ID of the client")
    servicio_id: str = Field(..., description="The ID of the service")
    fecha_hora: datetime = Field(..., description="The date and time of the appointment")

class dateupdate(BaseModel):
    servicio_id: Optional[str] = None
    fecha_hora: Optional[datetime] = None
    estado: Optional[str] = None
class dateResponse(date):
    id: str = Field(..., description="The unique identifier of the appointment")
    estado: str = Field(..., description="The status of the appointment")
    class Config:
        from_attributes = True