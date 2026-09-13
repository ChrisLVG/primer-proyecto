from sqlalchemy import Column, DateTime, Float, ForeignKey, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import relationship
import uuid
from database import Base

class Cliente(Base):
    __tablename__ = "clientes"
    
    # Usamos UUIDs de texto único en lugar de IDs secuenciales (1, 2, 3...) por seguridad,
    # evitando que usuarios externos adivinen IDs de otros registros a través de las URLs de tu API.
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    nombre = Column(String, nullable=False)
    numero = Column(String, nullable=False)
    correo = Column(String, unique=True, nullable=False)
    
    # SQLAlchemy une las clases lógicamente para permitir la navegación de objetos en Python.
    # 'back_populates' se conecta con la propiedad de la clase destino.
    citas = relationship("Cita", back_populates="cliente")

class Servicio(Base):
    __tablename__ = "servicios"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    nombre = Column(String, nullable=False)
    precio = Column(Float, nullable=False)
    duracion_minutos = Column(Integer, nullable=False)
    
    citas = relationship("Cita", back_populates="servicio")

class Cita(Base):
    __tablename__ = "citas"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Establecemos las Claves Foráneas (FK) que garantizan la integridad referencial [4].
    # No se puede crear una cita para un cliente o un servicio que no existan previamente.
    cliente_id = Column(String, ForeignKey("clientes.id"), nullable=False)
    servicio_id = Column(String, ForeignKey("servicios.id"), nullable=False)
    
    fecha_hora = Column(DateTime, nullable=False) # Almacenará fecha y hora de la cita
    estado = Column(String, default="pendiente") # 'pendiente', 'confirmada', 'cancelada'
    
    # Conexiones lógicas de SQLAlchemy para acceder a los datos relacionados de forma directa en Python.
    # Nos permite hacer cosas elegantes como: print(cita.cliente.nombre)
    cliente = relationship("Cliente", back_populates="citas")
    servicio = relationship("Servicio", back_populates="citas")