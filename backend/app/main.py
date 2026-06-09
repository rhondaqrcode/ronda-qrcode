from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.api.routes import (
    attendance,
    auth,
    checklists,
    dashboard,
    employees,
    health,
    locations,
    occurrences,
    patrol,
    photos,
    reports,
    ronda,
)
from backend.app.core.config import settings
from backend.app.core.exceptions import register_exception_handlers
from backend.app.core.logging import configure_logging
from backend.app.db.init_db import init_db
from backend.app.services.storage import cleanup_old_storage_files


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    init_db()
    cleanup_old_storage_files()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
    title=settings.app_name,
    version="2.0.0",
    description="API REST para supervisao de zeladoria, conservacao e facilities.",
    # lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def no_cache_frontend(request, call_next):
        response = await call_next(request)
        if request.url.path == "/" or request.url.path.startswith("/assets/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
        return response

    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=settings.uploads_dir), name="uploads")
    app.mount("/reports-files", StaticFiles(directory=settings.reports_dir), name="reports-files")
    app.mount("/assets", StaticFiles(directory="frontend"), name="assets")

    register_exception_handlers(app)

    app.include_router(health.router)
    app.include_router(auth.router, prefix="/auth", tags=["Autenticacao"])
    app.include_router(employees.router, prefix="/employees", tags=["Funcionarios"])
    app.include_router(locations.router, prefix="/locations", tags=["Locais"])
    app.include_router(attendance.router, prefix="/attendance", tags=["Presenca"])
    app.include_router(checklists.router, prefix="/checklists", tags=["Checklists"])
    app.include_router(occurrences.router, prefix="/occurrences", tags=["Ocorrencias"])
    app.include_router(patrol.router, prefix="/patrol", tags=["Rondas QR"])
    app.include_router(photos.router, prefix="/photos", tags=["Fotos"])
    app.include_router(reports.router, prefix="/reports", tags=["Relatorios"])
    app.include_router(ronda.router, prefix="/ronda", tags=["Ronda Eletronica QR"])
    app.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])

    @app.get("/", include_in_schema=False)
    def frontend() -> FileResponse:
        return FileResponse("frontend/index.html")

    return app


app = create_app()
