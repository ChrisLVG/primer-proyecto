from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import session
from database import get_db, engine
import models
import shcemas
from datetime import datetime

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="API de Gestión de Citas para la barberia, description="Esta API permite gestionar clientes, servicios y citas para un salón de uñas.", version="1.0.0")

@app.get("/")
def root():
    return {"message": "Bienvenido a la API de Gestión de Citas para la barberia"}

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

@app.patch("/clientes/{cliente_id}", response_model=shcemas.userresponse)
def actualizar_cliente(cliente_id: str, cliente: shcemas.UserUpdate, db: session = Depends(get_db)):
    cliente_db = db.query(models.Cliente).filter(models.Cliente.id == cliente_id).first()
    if not cliente_db:
        raise HTTPException(status_code=404, detail="El cliente no está registrado.")

    if cliente.nombre is not None:
        cliente_db.nombre = cliente.nombre

    if cliente.numero is not None:
        numero_en_uso = db.query(models.Cliente).filter(models.Cliente.numero == cliente.numero, models.Cliente.id != cliente_id).first()
        if numero_en_uso:
            raise HTTPException(status_code=400, detail="El número telefónico ya está asignado a otro cliente.")
        cliente_db.numero = cliente.numero

    if cliente.correo is not None:
        cliente_db.correo = cliente.correo

    db.commit()
    db.refresh(cliente_db)
    return cliente_db

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

@app.patch("/servicios/{servicio_id}", response_model=shcemas.serviceResponse)
def actualizar_servicio(servicio_id: str, servicio: shcemas.ServiceUpdate, db: session = Depends(get_db)):
    servicio_db = db.query(models.Servicio).filter(models.Servicio.id == servicio_id).first()
    if not servicio_db:
        raise HTTPException(status_code=404, detail="El servicio no está registrado.")

    if servicio.nombre is not None:
        servicio_existente = db.query(models.Servicio).filter(models.Servicio.nombre == servicio.nombre, models.Servicio.id != servicio_id).first()
        if servicio_existente:
            raise HTTPException(status_code=400, detail="El nombre del servicio ya está registrado.")
        servicio_db.nombre = servicio.nombre

    if servicio.precio is not None:
        servicio_db.precio = servicio.precio

    if servicio.duracion_minutos is not None:
        servicio_db.duracion_minutos = servicio.duracion_minutos

    db.commit()
    db.refresh(servicio_db)
    return servicio_db

@app.get("/citas/")
def listar_citas(db: session = Depends(get_db)):
    # Ejecutamos la consulta SQL de lectura mapeada a través de SQLAlchemy
    citas = db.query(models.Cita).all()
    return citas

@app.post("/citas/", response_model=shcemas.dateResponse)
def crear_cita(cita: shcemas.date, db: session = Depends(get_db)):
    # Verificamos si la cita ya existe en la base de datos
    existing_cita = db.query(models.Cita).filter(models.Cita.cliente_id == cita.cliente_id, models.Cita.servicio_id == cita.servicio_id, models.Cita.fecha_hora == cita.fecha_hora).first()
    if existing_cita:
        raise HTTPException(status_code=400, detail="La cita ya está registrada.")

    # Validamos si el servicio ya existe en la base de datos
    existing_servicio = db.query(models.Servicio).filter(models.Servicio.id == cita.servicio_id).first()
    if not existing_servicio:
        raise HTTPException(status_code=400, detail="El servicio no está registrado.")
    
    # Validamos si el cliente ya existe en la base de datos
    existing_cliente = db.query(models.Cliente).filter(models.Cliente.id == cita.cliente_id).first()
    if not existing_cliente:
        raise HTTPException(status_code=400, detail="El cliente no está registrado.")

    nueva_cita = models.Cita(
        cliente_id=cita.cliente_id,
        servicio_id=cita.servicio_id,
        fecha_hora=cita.fecha_hora
    )
    db.add(nueva_cita)
    db.commit()
    db.refresh(nueva_cita)
    return nueva_cita

@app.patch("/citas/{cita_id}", response_model=shcemas.dateResponse)
def actualizar_cita(cita_id: str, cita: shcemas.dateupdate, db: session = Depends(get_db)):
    # Verificamos si la cita existe en la base de datos
    existing_cita = db.query(models.Cita).filter(models.Cita.id == cita_id).first()
    if not existing_cita:
        raise HTTPException(status_code=404, detail="La cita no está registrada.")
    # Actualizamos los campos de la cita según los datos proporcionados
    if cita.servicio_id is not None:
        #Verificamos si el servicio existe en la base de datos    
        existing_servicio = db.query(models.Servicio).filter(models.Servicio.id == cita.servicio_id).first()
        if not existing_servicio:
            raise HTTPException(status_code=400, detail="El servicio no está registrado.")
        existing_cita.servicio_id = cita.servicio_id
    if cita.fecha_hora is not None:
        # Verificamos si la fecha y hora de la cita ya esta ocupada por otra cita de otro cliente   
        existing_cita_fecha = db.query(models.Cita).filter(models.Cita.fecha_hora == cita.fecha_hora, models.Cita.id != cita_id).first()
        if existing_cita_fecha:
            raise HTTPException(status_code=400, detail="La fecha y hora de la cita ya está ocupada por otra cita.")
        # Verificamos si la fecha y hora de la cita es anterior a la fecha y hora actual
        if cita.fecha_hora < datetime.now():
            raise HTTPException(status_code=400, detail="La fecha y hora de la cita no puede ser anterior a la fecha y hora actual.")
        # Verificamos si la fecha y hora de la cita coincide con la fecha y hora de otra cita del mismo cliente
        existing_cita_cliente = db.query(models.Cita).filter(models.Cita.cliente_id == existing_cita.cliente_id, models.Cita.fecha_hora == cita.fecha_hora, models.Cita.id != cita_id).first()
        if existing_cita_cliente:
            raise HTTPException(status_code=400, detail="La fecha y hora de la cita ya está ocupada por otra cita del mismo cliente.")
        existing_cita.fecha_hora = cita.fecha_hora
    if cita.estado is not None:
        existing_cita.estado = cita.estado

    db.commit()
    db.refresh(existing_cita)
    return existing_cita