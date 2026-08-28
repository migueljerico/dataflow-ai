import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from app.core.config import settings


class StorageBackend(ABC):
    """Interfaz abstracta para el almacenamiento de datasets y artefactos generados."""

    @abstractmethod
    def save_file(self, filename: str, content: bytes) -> Path:
        pass

    @abstractmethod
    def read_file(self, filename: str) -> bytes:
        pass

    @abstractmethod
    def delete_file(self, filename: str) -> bool:
        pass

    @abstractmethod
    def exists(self, filename: str) -> bool:
        pass

    @abstractmethod
    def get_path(self, filename: str) -> Path:
        pass

    @abstractmethod
    def cleanup(self, max_age_seconds: int = 7200, max_files: int = 20) -> int:
        pass


class LocalStorageBackend(StorageBackend):
    """Implementación de almacenamiento local basada en Path/tmpfs con retención controlada."""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or settings.UPLOAD_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_file(self, filename: str, content: bytes) -> Path:
        safe_name = Path(filename).name
        target_path = self.base_dir / safe_name
        with open(target_path, "wb") as f:
            f.write(content)
        return target_path

    def read_file(self, filename: str) -> bytes:
        target_path = self.get_path(filename)
        with open(target_path, "rb") as f:
            return f.read()

    def delete_file(self, filename: str) -> bool:
        try:
            target_path = self.get_path(filename)
            if target_path.exists():
                target_path.unlink(missing_ok=True)
                return True
        except OSError:
            pass
        return False

    def exists(self, filename: str) -> bool:
        return (self.base_dir / Path(filename).name).exists()

    def get_path(self, filename: str) -> Path:
        return self.base_dir / Path(filename).name

    def cleanup(self, max_age_seconds: int = 7200, max_files: int = 20) -> int:
        deleted_count = 0
        try:
            if not self.base_dir.exists():
                return 0
            now = time.time()
            files = [f for f in self.base_dir.iterdir() if f.is_file()]

            for f in files:
                try:
                    if now - f.stat().st_mtime > max_age_seconds:
                        f.unlink(missing_ok=True)
                        deleted_count += 1
                except OSError:
                    pass

            remaining = [f for f in self.base_dir.iterdir() if f.is_file()]
            if len(remaining) > max_files:
                remaining.sort(key=lambda x: x.stat().st_mtime)
                for f in remaining[: len(remaining) - max_files]:
                    try:
                        f.unlink(missing_ok=True)
                        deleted_count += 1
                    except OSError:
                        pass
        except Exception:
            pass
        return deleted_count


_default_storage: Optional[StorageBackend] = None


def get_storage() -> StorageBackend:
    global _default_storage
    if _default_storage is None:
        _default_storage = LocalStorageBackend()
    return _default_storage
