import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import FunctionalException, functional_exception_handler, global_exception_handler
from app.core.logging_config import request_id_middleware, setup_logging
from app.services.report_service import ReportService

setup_logging()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Scheduler de exportaciones programadas (reportes ejecutivos + webhooks de drift).
    # Solo arranca con el servidor real (uvicorn); los TestClient sin context manager
    # no disparan el lifespan, de modo que la suite de tests permanece determinista.
    scheduler_task = asyncio.create_task(ReportService.scheduler_loop())
    yield
    scheduler_task.cancel()
    try:
        await scheduler_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    description="DataFlow AI — Intelligent Data Preparation & Business Analytics API",
    lifespan=lifespan,
)

# Middleware de trazabilidad de peticiones HTTP (X-Request-ID)
app.middleware("http")(request_id_middleware)

# Configuración de CORS: orígenes permitidos configurables por entorno
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Gemini-Api-Key", "X-Request-ID"],
)


# Manejadores de excepciones
app.add_exception_handler(FunctionalException, functional_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)


# Endpoint de Healthcheck para Cloud Run
@app.get("/health")
def health():
    return {"status": "ok", "service": settings.PROJECT_NAME, "version": settings.VERSION}


# Incluir router API V1
app.include_router(api_router, prefix=settings.API_V1_STR)

# Montar frontend estático si existe la carpeta 'static' (compilado en Docker para producción)
BASE_STATIC_DIR = os.path.abspath(str(Path(__file__).resolve().parent.parent / "static"))
if not os.path.exists(BASE_STATIC_DIR):
    BASE_STATIC_DIR = os.path.abspath("static")

INDEX_HTML_PATH = os.path.join(BASE_STATIC_DIR, "index.html")

if os.path.exists(BASE_STATIC_DIR) and os.path.exists(INDEX_HTML_PATH):
    assets_dir = os.path.join(BASE_STATIC_DIR, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api/") or full_path.startswith("docs") or full_path.startswith("openapi.json"):
            return {"detail": "Not Found"}

        # CodeQL CWE-022 Sanitizer Pattern canónico
        sanitized_subpath = os.path.normpath(full_path).lstrip(r"\/")
        full_target_path = os.path.normpath(os.path.join(BASE_STATIC_DIR, sanitized_subpath))

        if not full_target_path.startswith(BASE_STATIC_DIR):
            return FileResponse(INDEX_HTML_PATH)

        if os.path.isfile(full_target_path):
            return FileResponse(full_target_path)

        return FileResponse(INDEX_HTML_PATH)

else:

    @app.get("/")
    def root():
        return {"name": settings.PROJECT_NAME, "version": settings.VERSION, "status": "online", "docs_url": "/docs"}
