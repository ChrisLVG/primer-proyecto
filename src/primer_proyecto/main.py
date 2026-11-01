from fastapi import FastAPI

from .database import engine
from . import models
from . import autenticador
from .routers import citas, servicios, usuarios

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="API de Gestión de Citas para la barberia",
    description="Esta API permite gestionar usuarios, servicios y citas para una barberia.",
    version="1.0.0"
)
app.include_router(autenticador.router)
app.include_router(usuarios.router)
app.include_router(servicios.router)
app.include_router(citas.router)


@app.get("/")
def root():
    return {"message": "Bienvenido a la API de Gestión de Citas para la barberia"}
