from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import session
from database import get_db, engine, Base
import models

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