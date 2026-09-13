from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import session
from database import get_db, engine, Base
import models
import shcemas

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="API de Gestión de Citas para Salón de Uñas Angi Nails", description="Esta API permite gestionar clientes, servicios y citas para un salón de uñas.", version="1.0.0")

@app.get("/")
def root():
    return {"message": "Bienvenido a la API de Gestión de Citas para Salón de Uñas Angi Nails"}

@app.get("/clientes/")
def listar_clientes(db: session = Depends(get_db)):
    # Ejecutamos la consulta SQL de lectura mapeada a través de SQLAlchemy
    clientes = db.query(models.Cliente).all()
    return clientes

@app.post("/clientes/", response_model=shcemas.userresponse)
def crear_cliente(cliente: shcemas.User, db: session = Depends(get_db)):
    # Verificamos si el correo ya existe en la base de datos
    existing_cliente = db.query(models.Cliente).filter(models.Cliente.correo == cliente.email).first()
    if existing_cliente:
        raise HTTPException(status_code=400, detail="El correo ya está registrado.")
    
    nuevo_cliente = models.Cliente(
        nombre=cliente.nombre,
        numero=cliente.numero,
        correo=cliente.email
    )
    db.add(nuevo_cliente)
    db.commit()
    db.refresh(nuevo_cliente)
    return nuevo_cliente

@app.get("/servicios/")
def listar_servicios(db: session = Depends(get_db)):
    # Ejecutamos la consulta SQL de lectura mapeada a través de SQLAlchemy
    servicios = db.query(models.Servicio).all()
    return servicios

@app.post("/servicios/", response_model=shcemas.serviceResponse)
def crear_servicio(servicio: shcemas.service, db: session = Depends(get_db)):
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