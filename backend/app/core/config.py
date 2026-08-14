import os
from pathlib import Path

class Settings:
    PROJECT_NAME: str = "DataFlow AI"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    
    # File limits
    MAX_FILE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB limit for MVP
    ALLOWED_EXTENSIONS: set = {".csv", ".xlsx"}
    MAX_RECOMMENDED_ROWS: int = 100_000
    MAX_RECOMMENDED_COLS: int = 50

    # Storage paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    UPLOAD_DIR: Path = BASE_DIR / "uploads"

    def __init__(self):
        os.makedirs(self.UPLOAD_DIR, exist_ok=True)

settings = Settings()
