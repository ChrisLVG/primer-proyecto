def main() -> None:
    """Arranca el servidor de desarrollo de la API con recarga automática."""
    import uvicorn

    uvicorn.run("primer_proyecto.main:app", reload=True)