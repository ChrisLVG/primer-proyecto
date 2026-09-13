from pydantic import BaseModel, Field
from datetime import datetime
class User(BaseModel):
    nombre: str = Field(..., description="The name of the user")
    numero: str = Field(..., description="The phone number of the user")
    email: str = Field(..., description="The email address of the user")

class userresponse(User):
    id: str = Field(..., description="The unique identifier of the user")

    class Config:
        from_attributes = True

class service(BaseModel):
    nombre: str = Field(..., description="The name of the service")
    precio: str = Field(..., description="The price of the service")
    duracion_minutos: str = Field(..., description="The duration of the service in minutes")

class serviceResponse(service):
    id: str = Field(..., description="The unique identifier of the service")

    class Config:
        from_attributes = True

class date(BaseModel):
    cliente_id: str = Field(..., description="The ID of the client")
    servicio_id: str = Field(..., description="The ID of the service")
    fecha_hora: datetime = Field(..., description="The date and time of the appointment")

class dateResponse(date):
    id: str = Field(..., description="The unique identifier of the appointment")
    estado: str = Field(..., description="The status of the appointment")
    class Config:
        from_attributes = True