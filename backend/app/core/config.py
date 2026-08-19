import os
from pathlib import Path
from typing import List

class Settings:
    PROJECT_NAME: str = "DataFlow AI"
    VERSION: str = "1.1.2"
    API_V1_STR: str = "/api/v1"

    # File limits
    MAX_FILE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB limit for MVP
    ALLOWED_EXTENSIONS: set = {".csv", ".xlsx"}
    MAX_RECOMMENDED_ROWS: int = 100_000
    MAX_RECOMMENDED_COLS: int = 50

    # Storage paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    UPLOAD_DIR: Path = BASE_DIR / "uploads"

    # CORS: en desarrollo el frontend Vite hace proxy de /api, por lo que esta
    # lista es una red de seguridad. En producción (Cloud Run) se configura vía
    # la variable de entorno BACKEND_CORS_ORIGINS (orígenes separados por coma).
    DEFAULT_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
    ]

    def __init__(self):
        cors_env = os.getenv("BACKEND_CORS_ORIGINS", "")
        configured = [origin.strip() for origin in cors_env.split(",") if origin.strip()]
        self.BACKEND_CORS_ORIGINS: List[str] = configured or self.DEFAULT_CORS_ORIGINS
        os.makedirs(self.UPLOAD_DIR, exist_ok=True)

settings = Settings()
