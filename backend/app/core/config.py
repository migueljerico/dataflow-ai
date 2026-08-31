# pydantic-settings recomendado para validación futura; se mantiene compatibilidad sin dependencia extra
import os
from pathlib import Path
from typing import List, Optional


class Settings:
    PROJECT_NAME: str = "DataFlow AI"
    VERSION: str = "1.8.0"
    API_V1_STR: str = "/api/v1"

    # File limits
    MAX_FILE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB limit for direct file upload
    MAX_URL_FILE_SIZE_BYTES: int = 20 * 1024 * 1024  # 20 MB limit for URL imports
    URL_DOWNLOAD_TIMEOUT_SECONDS: float = 20.0  # 20s timeout
    MAX_UPLOAD_FILES_KEPT: int = 20  # Prevent unbounded growth in Cloud Run tmpfs
    ALLOWED_EXTENSIONS: set = {".csv", ".xlsx"}
    MAX_RECOMMENDED_ROWS: int = 100_000
    MAX_RECOMMENDED_COLS: int = 50

    # Storage paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    UPLOAD_DIR: Path = BASE_DIR / "uploads"

    # Cloud Storage & S3 configuration
    STORAGE_BACKEND: str = os.getenv("STORAGE_BACKEND", "local").lower()
    STORAGE_BUCKET_NAME: str = os.getenv("STORAGE_BUCKET_NAME", "")
    STORAGE_GCS_PROJECT: Optional[str] = os.getenv("STORAGE_GCS_PROJECT", None)
    STORAGE_S3_ENDPOINT_URL: Optional[str] = os.getenv("STORAGE_S3_ENDPOINT_URL", None)
    STORAGE_S3_REGION_NAME: str = os.getenv("STORAGE_S3_REGION_NAME", "us-east-1")
    STORAGE_S3_ACCESS_KEY_ID: Optional[str] = os.getenv("STORAGE_S3_ACCESS_KEY_ID", None)
    STORAGE_S3_SECRET_ACCESS_KEY: Optional[str] = os.getenv("STORAGE_S3_SECRET_ACCESS_KEY", None)
    STORAGE_PREFIX: str = os.getenv("STORAGE_PREFIX", "dataflow/")

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
