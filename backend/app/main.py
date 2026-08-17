from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.exceptions import FunctionalException, functional_exception_handler, global_exception_handler
from app.api.v1.router import api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    description="DataFlow AI — Intelligent Data Preparation & Business Analytics API"
)

# Configuración de CORS: orígenes permitidos configurables por entorno
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
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
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
if not STATIC_DIR.exists():
    STATIC_DIR = Path("static")

if STATIC_DIR.exists() and (STATIC_DIR / "index.html").exists():
    assets_dir = STATIC_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api/") or full_path.startswith("docs") or full_path.startswith("openapi.json"):
            return {"detail": "Not Found"}
        target_file = STATIC_DIR / full_path
        if target_file.exists() and target_file.is_file():
            return FileResponse(target_file)
        return FileResponse(STATIC_DIR / "index.html")
else:
    @app.get("/")
    def root():
        return {
            "name": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "status": "online",
            "docs_url": "/docs"
        }
