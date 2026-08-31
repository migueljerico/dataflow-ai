import logging
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, List, Optional

from app.core.config import settings
from app.core.exceptions import FunctionalException

logger = logging.getLogger("dataflow.storage")


class StorageBackend(ABC):
    """Interfaz abstracta para el almacenamiento de datasets y artefactos generados."""

    @abstractmethod
    def save_file(self, filename: str, content: bytes) -> Path:
        """Guarda el contenido en bytes y retorna la ruta local utilizable."""
        pass

    @abstractmethod
    def read_file(self, filename: str) -> bytes:
        """Lee el contenido completo del archivo en bytes."""
        pass

    @abstractmethod
    def delete_file(self, filename: str) -> bool:
        """Elimina el archivo del almacenamiento."""
        pass

    @abstractmethod
    def exists(self, filename: str) -> bool:
        """Verifica la existencia del archivo."""
        pass

    @abstractmethod
    def get_path(self, filename: str) -> Path:
        """Obtiene la ruta local sincronizada para procesamiento en Pandas/OpenPyXL."""
        pass

    @abstractmethod
    def list_files(self, prefix: str = "") -> List[str]:
        """Lista los nombres de archivo almacenados que coincidan con el prefijo."""
        pass

    @abstractmethod
    def cleanup(self, max_age_seconds: int = 7200, max_files: int = 20) -> int:
        """Limpia archivos antiguos o excedentes para respetar límites de almacenamiento."""
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
        if not target_path.exists():
            raise FunctionalException(
                message=f"El archivo '{filename}' no existe en el almacenamiento local.",
                code="FILE_NOT_FOUND",
                status_code=404,
            )
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

    def list_files(self, prefix: str = "") -> List[str]:
        try:
            if not self.base_dir.exists():
                return []
            return [f.name for f in self.base_dir.iterdir() if f.is_file() and f.name.startswith(prefix)]
        except Exception:
            return []

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


class GCSStorageBackend(StorageBackend):
    """
    Conector de almacenamiento para Google Cloud Storage (GCS).
    Diseñado para entornos multi-instancia en Google Cloud Run y Kubernetes.
    Mantiene sincronización transparente con un directorio de caché local
    para permitir lectura eficiente de DataFrames con Pandas/OpenPyXL.
    """

    def __init__(
        self,
        bucket_name: Optional[str] = None,
        project: Optional[str] = None,
        prefix: Optional[str] = None,
        cache_dir: Optional[Path] = None,
        client: Optional[Any] = None,
    ):
        self.bucket_name = bucket_name or settings.STORAGE_BUCKET_NAME
        self.project = project or settings.STORAGE_GCS_PROJECT
        self.prefix = prefix if prefix is not None else settings.STORAGE_PREFIX
        self.cache_dir = cache_dir or settings.UPLOAD_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        if not self.bucket_name:
            raise FunctionalException(
                message="Debe configurarse la variable 'STORAGE_BUCKET_NAME' para utilizar el backend GCS.",
                code="GCS_BUCKET_NAME_MISSING",
                status_code=500,
            )

        if client is not None:
            self.client = client
        else:
            try:
                from google.cloud import storage as gcs_storage

                self.client = gcs_storage.Client(project=self.project)
            except ImportError as exc:
                raise FunctionalException(
                    message="El backend de almacenamiento GCS requiere instalar la dependencia 'google-cloud-storage'.",
                    code="GCS_DEPENDENCY_MISSING",
                    status_code=500,
                ) from exc
            except Exception as exc:
                raise FunctionalException(
                    message=f"No se pudo inicializar el cliente de Google Cloud Storage: {str(exc)}",
                    code="GCS_INITIALIZATION_ERROR",
                    status_code=500,
                ) from exc

    def _blob_name(self, filename: str) -> str:
        safe_name = Path(filename).name
        clean_prefix = self.prefix.strip("/")
        return f"{clean_prefix}/{safe_name}" if clean_prefix else safe_name

    def save_file(self, filename: str, content: bytes) -> Path:
        safe_name = Path(filename).name
        local_path = self.cache_dir / safe_name
        with open(local_path, "wb") as f:
            f.write(content)

        try:
            bucket = self.client.bucket(self.bucket_name)
            blob = bucket.blob(self._blob_name(safe_name))
            blob.upload_from_string(content)
        except Exception as exc:
            logger.error("Error al subir blob a GCS '%s': %s", safe_name, str(exc))
            raise FunctionalException(
                message=f"Error al subir el archivo '{safe_name}' a Google Cloud Storage.",
                code="GCS_UPLOAD_ERROR",
                details={"error": str(exc)},
            ) from exc

        return local_path

    def read_file(self, filename: str) -> bytes:
        safe_name = Path(filename).name
        try:
            bucket = self.client.bucket(self.bucket_name)
            blob = bucket.blob(self._blob_name(safe_name))
            if not blob.exists():
                raise FunctionalException(
                    message=f"El archivo '{safe_name}' no existe en el bucket GCS '{self.bucket_name}'.",
                    code="FILE_NOT_FOUND",
                    status_code=404,
                )
            content = blob.download_as_bytes()
            local_path = self.cache_dir / safe_name
            with open(local_path, "wb") as f:
                f.write(content)
            return content
        except FunctionalException:
            raise
        except Exception as exc:
            logger.error("Error al leer blob de GCS '%s': %s", safe_name, str(exc))
            raise FunctionalException(
                message=f"Error al descargar el archivo '{safe_name}' desde Google Cloud Storage.",
                code="GCS_DOWNLOAD_ERROR",
                details={"error": str(exc)},
            ) from exc

    def delete_file(self, filename: str) -> bool:
        safe_name = Path(filename).name
        local_path = self.cache_dir / safe_name
        if local_path.exists():
            local_path.unlink(missing_ok=True)

        try:
            bucket = self.client.bucket(self.bucket_name)
            blob = bucket.blob(self._blob_name(safe_name))
            if blob.exists():
                blob.delete()
                return True
        except Exception as exc:
            logger.warning("Error al eliminar blob de GCS '%s': %s", safe_name, str(exc))
        return False

    def exists(self, filename: str) -> bool:
        safe_name = Path(filename).name
        try:
            bucket = self.client.bucket(self.bucket_name)
            blob = bucket.blob(self._blob_name(safe_name))
            return bool(blob.exists())
        except Exception:
            return (self.cache_dir / safe_name).exists()

    def get_path(self, filename: str) -> Path:
        safe_name = Path(filename).name
        local_path = self.cache_dir / safe_name
        if local_path.exists():
            return local_path

        # Si no existe en caché local, se descarga de GCS
        self.read_file(safe_name)
        return local_path

    def list_files(self, prefix: str = "") -> List[str]:
        try:
            bucket = self.client.bucket(self.bucket_name)
            search_prefix = self._blob_name(prefix) if prefix else self.prefix.strip("/")
            blobs = bucket.list_blobs(prefix=search_prefix)
            results = []
            for b in blobs:
                name = b.name.split("/")[-1]
                if name:
                    results.append(name)
            return results
        except Exception:
            return [f.name for f in self.cache_dir.iterdir() if f.is_file() and f.name.startswith(prefix)]

    def cleanup(self, max_age_seconds: int = 7200, max_files: int = 20) -> int:
        deleted_count = 0
        try:
            now = time.time()
            bucket = self.client.bucket(self.bucket_name)
            search_prefix = self.prefix.strip("/")
            blobs = list(bucket.list_blobs(prefix=search_prefix))

            for b in blobs:
                if b.time_created and (now - b.time_created.timestamp() > max_age_seconds):
                    try:
                        b.delete()
                        deleted_count += 1
                    except Exception:
                        pass

            if len(blobs) > max_files:
                blobs.sort(key=lambda x: x.time_created.timestamp() if x.time_created else 0)
                for b in blobs[: len(blobs) - max_files]:
                    try:
                        b.delete()
                        deleted_count += 1
                    except Exception:
                        pass
        except Exception as exc:
            logger.warning("Error en cleanup de GCS: %s", str(exc))

        # Limpiar también la caché local
        LocalStorageBackend(self.cache_dir).cleanup(max_age_seconds, max_files)
        return deleted_count


class S3StorageBackend(StorageBackend):
    """
    Conector de almacenamiento para AWS S3 y servicios compatibles (MinIO, Cloudflare R2, LocalStack).
    Soporta autenticación estándar por IAM o credenciales explícitas y endpoints personalizados.
    Mantiene sincronización transparente con un directorio de caché local.
    """

    def __init__(
        self,
        bucket_name: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        region_name: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        prefix: Optional[str] = None,
        cache_dir: Optional[Path] = None,
        client: Optional[Any] = None,
    ):
        self.bucket_name = bucket_name or settings.STORAGE_BUCKET_NAME
        self.endpoint_url = endpoint_url or settings.STORAGE_S3_ENDPOINT_URL
        self.region_name = region_name or settings.STORAGE_S3_REGION_NAME
        self.aws_access_key_id = aws_access_key_id or settings.STORAGE_S3_ACCESS_KEY_ID
        self.aws_secret_access_key = aws_secret_access_key or settings.STORAGE_S3_SECRET_ACCESS_KEY
        self.prefix = prefix if prefix is not None else settings.STORAGE_PREFIX
        self.cache_dir = cache_dir or settings.UPLOAD_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        if not self.bucket_name:
            raise FunctionalException(
                message="Debe configurarse la variable 'STORAGE_BUCKET_NAME' para utilizar el backend S3.",
                code="S3_BUCKET_NAME_MISSING",
                status_code=500,
            )

        if client is not None:
            self.client = client
        else:
            try:
                import boto3

                kwargs: dict = {"region_name": self.region_name}
                if self.endpoint_url:
                    kwargs["endpoint_url"] = self.endpoint_url
                if self.aws_access_key_id and self.aws_secret_access_key:
                    kwargs["aws_access_key_id"] = self.aws_access_key_id
                    kwargs["aws_secret_access_key"] = self.aws_secret_access_key

                self.client = boto3.client("s3", **kwargs)
            except ImportError as exc:
                raise FunctionalException(
                    message="El backend de almacenamiento S3 requiere instalar la dependencia 'boto3'.",
                    code="S3_DEPENDENCY_MISSING",
                    status_code=500,
                ) from exc
            except Exception as exc:
                raise FunctionalException(
                    message=f"No se pudo inicializar el cliente S3: {str(exc)}",
                    code="S3_INITIALIZATION_ERROR",
                    status_code=500,
                ) from exc

    def _key_name(self, filename: str) -> str:
        safe_name = Path(filename).name
        clean_prefix = self.prefix.strip("/")
        return f"{clean_prefix}/{safe_name}" if clean_prefix else safe_name

    def save_file(self, filename: str, content: bytes) -> Path:
        safe_name = Path(filename).name
        local_path = self.cache_dir / safe_name
        with open(local_path, "wb") as f:
            f.write(content)

        try:
            self.client.put_object(Bucket=self.bucket_name, Key=self._key_name(safe_name), Body=content)
        except Exception as exc:
            logger.error("Error al subir objeto a S3 '%s': %s", safe_name, str(exc))
            raise FunctionalException(
                message=f"Error al subir el archivo '{safe_name}' al almacenamiento S3.",
                code="S3_UPLOAD_ERROR",
                details={"error": str(exc)},
            ) from exc

        return local_path

    def read_file(self, filename: str) -> bytes:
        safe_name = Path(filename).name
        try:
            response = self.client.get_object(Bucket=self.bucket_name, Key=self._key_name(safe_name))
            content = response["Body"].read()
            local_path = self.cache_dir / safe_name
            with open(local_path, "wb") as f:
                f.write(content)
            return content
        except Exception as exc:
            err_str = str(exc).lower()
            if "nosuchkey" in err_str or "notfound" in err_str or "404" in err_str:
                raise FunctionalException(
                    message=f"El archivo '{safe_name}' no existe en el bucket S3 '{self.bucket_name}'.",
                    code="FILE_NOT_FOUND",
                    status_code=404,
                ) from exc
            logger.error("Error al leer objeto de S3 '%s': %s", safe_name, str(exc))
            raise FunctionalException(
                message=f"Error al descargar el archivo '{safe_name}' desde S3.",
                code="S3_DOWNLOAD_ERROR",
                details={"error": str(exc)},
            ) from exc

    def delete_file(self, filename: str) -> bool:
        safe_name = Path(filename).name
        local_path = self.cache_dir / safe_name
        if local_path.exists():
            local_path.unlink(missing_ok=True)

        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=self._key_name(safe_name))
            return True
        except Exception as exc:
            logger.warning("Error al eliminar objeto de S3 '%s': %s", safe_name, str(exc))
            return False

    def exists(self, filename: str) -> bool:
        safe_name = Path(filename).name
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=self._key_name(safe_name))
            return True
        except Exception:
            return (self.cache_dir / safe_name).exists()

    def get_path(self, filename: str) -> Path:
        safe_name = Path(filename).name
        local_path = self.cache_dir / safe_name
        if local_path.exists():
            return local_path

        self.read_file(safe_name)
        return local_path

    def list_files(self, prefix: str = "") -> List[str]:
        try:
            search_prefix = self._key_name(prefix) if prefix else self.prefix.strip("/")
            response = self.client.list_objects_v2(Bucket=self.bucket_name, Prefix=search_prefix)
            contents = response.get("Contents", [])
            results = []
            for item in contents:
                key = item.get("Key", "")
                name = key.split("/")[-1]
                if name:
                    results.append(name)
            return results
        except Exception:
            return [f.name for f in self.cache_dir.iterdir() if f.is_file() and f.name.startswith(prefix)]

    def cleanup(self, max_age_seconds: int = 7200, max_files: int = 20) -> int:
        deleted_count = 0
        try:
            now = time.time()
            search_prefix = self.prefix.strip("/")
            response = self.client.list_objects_v2(Bucket=self.bucket_name, Prefix=search_prefix)
            items = response.get("Contents", [])

            for item in items:
                last_modified = item.get("LastModified")
                if last_modified and (now - last_modified.timestamp() > max_age_seconds):
                    try:
                        self.client.delete_object(Bucket=self.bucket_name, Key=item["Key"])
                        deleted_count += 1
                    except Exception:
                        pass

            if len(items) > max_files:
                items.sort(key=lambda x: x["LastModified"].timestamp() if x.get("LastModified") else 0)
                for item in items[: len(items) - max_files]:
                    try:
                        self.client.delete_object(Bucket=self.bucket_name, Key=item["Key"])
                        deleted_count += 1
                    except Exception:
                        pass
        except Exception as exc:
            logger.warning("Error en cleanup de S3: %s", str(exc))

        LocalStorageBackend(self.cache_dir).cleanup(max_age_seconds, max_files)
        return deleted_count


_default_storage: Optional[StorageBackend] = None


def get_storage(backend_type: Optional[str] = None) -> StorageBackend:
    """
    Factory para obtener la instancia activa de StorageBackend según configuración.
    Soporta 'local', 'gcs' / 'google_cloud_storage' y 's3' / 'aws_s3'.
    """
    global _default_storage
    target_backend = (backend_type or settings.STORAGE_BACKEND).lower()

    if backend_type is not None:
        return _instantiate_backend(target_backend)

    if _default_storage is None:
        _default_storage = _instantiate_backend(target_backend)
    return _default_storage


def _instantiate_backend(target_backend: str) -> StorageBackend:
    if target_backend in ("local", "disk", "fs"):
        return LocalStorageBackend()
    elif target_backend in ("gcs", "google_cloud_storage", "cloud_storage"):
        return GCSStorageBackend()
    elif target_backend in ("s3", "aws_s3", "minio", "r2"):
        return S3StorageBackend()
    else:
        raise FunctionalException(
            message=f"Backend de almacenamiento no soportado: '{target_backend}'. Opciones válidas: ['local', 'gcs', 's3'].",
            code="INVALID_STORAGE_BACKEND",
            status_code=500,
        )


def reset_storage() -> None:
    """Restablece el singleton de almacenamiento (utilizado en testing y reconfiguración)."""
    global _default_storage
    _default_storage = None
