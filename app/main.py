from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import auth, checklists, employees, health, occurrences, photos
from app.core.config import settings
from app.db.init_db import init_db


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description="API REST para sistema de zeladoria.",
        lifespan=lifespan,
    )

    settings.media_root.mkdir(parents=True, exist_ok=True)
    app.mount("/media", StaticFiles(directory=settings.media_root), name="media")
    app.mount("/assets", StaticFiles(directory="frontend"), name="assets")

    app.include_router(health.router)
    app.include_router(auth.router, prefix="/auth", tags=["Autenticacao"])
    app.include_router(employees.router, prefix="/employees", tags=["Funcionarios"])
    app.include_router(checklists.router, prefix="/checklists", tags=["Checklists"])
    app.include_router(occurrences.router, prefix="/occurrences", tags=["Ocorrencias"])
    app.include_router(photos.router, prefix="/photos", tags=["Fotos"])

    @app.get("/", include_in_schema=False)
    def frontend() -> FileResponse:
        return FileResponse("frontend/index.html")

    return app


app = create_app()
