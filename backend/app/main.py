from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
# (ver BACKEND_CORS_ORIGINS en app.core.config). Nunca comodín en producción.
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

# Incluir router API V1
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "online",
        "docs_url": "/docs"
    }
