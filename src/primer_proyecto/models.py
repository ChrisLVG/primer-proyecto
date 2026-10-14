from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
import uuid

from .database import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    # Usamos UUIDs de texto único en lugar de IDs secuenciales (1, 2, 3...) por seguridad,
    # evitando que usuarios externos adivinen IDs de otros registros a través de las URLs de la API.
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    nombre = Column(String, nullable=False)
    numero = Column(String, nullable=False)
    correo = Column(String, unique=True, nullable=False)
    # 'usuario' (cliente que agenda desde el sitio) o 'barbero' (personal que agenda por teléfono o en el mostrador)
    rol = Column(String, nullable=False, default="usuario")

    # SQLAlchemy une las clases lógicamente para permitir la navegación de objetos en Python.
    # 'back_populates' se conecta con la propiedad de la clase destino.
    citas = relationship("Cita", back_populates="usuario")


class Servicio(Base):
    __tablename__ = "servicios"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    nombre = Column(String, nullable=False)
    precio = Column(Float, nullable=False)
    duracion_minutos = Column(Integer, nullable=False)

    citas = relationship("Cita", secondary="cita_servicio", back_populates="servicios")


class Cita(Base):
    __tablename__ = "citas"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Establecemos las Claves Foráneas (FK) que garantizan la integridad referencial.
    # No se puede crear una cita para un usuario que no exista previamente.
    usuario_id = Column(String, ForeignKey("usuarios.id"), nullable=False)

    fecha_hora = Column(DateTime, nullable=False)  # Almacenará fecha y hora de la cita
    estado = Column(String, default="pendiente")  # 'pendiente', 'confirmada', 'cancelada'

    # Snapshot del tipo de cuenta que agendó. Se escribe una sola vez al crear la cita y NO se
    # recalcula a partir del rol actual del usuario, para que un cambio de rol posterior no
    # reescriba la historia de cómo se generó la cita.
    origen = Column(String, nullable=False, default="usuario")  # 'usuario' | 'barbero'

    # Precio total desnormalizado: suma de los precios de los servicios de la cita.
    # Se recalcula en cada escritura (crear cita, cambiar sus servicios y cambiar el precio de un
    # servicio) para que no arrastre valores obsoletos.
    precio_total = Column(Float, nullable=False, default=0.0)

    # Conexiones lógicas de SQLAlchemy para acceder a los datos relacionados de forma directa en Python.
    usuario = relationship("Usuario", back_populates="citas")

    # Una cita puede incluir varios servicios (relación N:M resuelta con la tabla intermedia
    # 'cita_servicio'), por lo que ya no hay un único servicio_id en esta tabla.
    servicios = relationship("Servicio", secondary="cita_servicio", back_populates="citas")


class CitaServicio(Base):
    """Tabla intermedia que resuelve la relación N:M entre Cita y Servicio."""

    __tablename__ = "cita_servicio"

    # La clave primaria compuesta impide que un mismo servicio se repita dentro de la misma cita.
    cita_id = Column(String, ForeignKey("citas.id"), primary_key=True)
    servicio_id = Column(String, ForeignKey("servicios.id"), primary_key=True)