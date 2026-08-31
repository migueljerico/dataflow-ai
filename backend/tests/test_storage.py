from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.core.exceptions import FunctionalException
from app.core.storage import (
    GCSStorageBackend,
    LocalStorageBackend,
    S3StorageBackend,
    get_storage,
    reset_storage,
)


def test_local_storage_backend_crud_and_lifecycle(tmp_path):
    storage = LocalStorageBackend(base_dir=tmp_path)

    # 1. Guardar archivo
    saved_path = storage.save_file("test_data.csv", b"col1,col2\n1,2\n")
    assert saved_path.exists()
    assert saved_path.name == "test_data.csv"

    # 2. Comprobar existencia
    assert storage.exists("test_data.csv") is True
    assert storage.exists("non_existent.csv") is False

    # 3. Leer archivo
    content = storage.read_file("test_data.csv")
    assert content == b"col1,col2\n1,2\n"

    # 4. Obtener ruta
    path = storage.get_path("test_data.csv")
    assert path == saved_path

    # 5. Listar archivos
    files = storage.list_files(prefix="test_")
    assert "test_data.csv" in files
    assert len(storage.list_files(prefix="other_")) == 0

    # 6. Excepcion al leer archivo inexistente
    with pytest.raises(FunctionalException) as exc_info:
        storage.read_file("ghost_file.csv")
    assert exc_info.value.code == "FILE_NOT_FOUND"

    # 7. Eliminar archivo
    deleted = storage.delete_file("test_data.csv")
    assert deleted is True
    assert storage.exists("test_data.csv") is False
    assert storage.delete_file("test_data.csv") is False


def test_local_storage_cleanup_max_files(tmp_path):
    storage = LocalStorageBackend(base_dir=tmp_path)

    for i in range(10):
        storage.save_file(f"file_{i:02d}.csv", f"content_{i}".encode("utf-8"))

    assert len(storage.list_files()) == 10
    deleted = storage.cleanup(max_age_seconds=99999, max_files=5)
    assert deleted == 5
    assert len(storage.list_files()) == 5


def test_gcs_storage_backend_requires_bucket_name(tmp_path):
    with pytest.raises(FunctionalException) as exc_info:
        GCSStorageBackend(bucket_name="", cache_dir=tmp_path)
    assert exc_info.value.code == "GCS_BUCKET_NAME_MISSING"


def test_gcs_storage_backend_with_mock_client(tmp_path):
    mock_client = MagicMock()
    mock_bucket = MagicMock()
    mock_blob = MagicMock()

    mock_client.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob
    mock_blob.exists.return_value = True
    mock_blob.download_as_bytes.return_value = b"gcs_mock_content"

    storage = GCSStorageBackend(
        bucket_name="my-dataflow-bucket",
        project="my-gcp-project",
        prefix="datasets/",
        cache_dir=tmp_path,
        client=mock_client,
    )

    # 1. Guardar archivo
    saved_path = storage.save_file("sample_gcs.csv", b"a,b\n10,20\n")
    assert saved_path.exists()
    mock_client.bucket.assert_called_with("my-dataflow-bucket")
    mock_bucket.blob.assert_called_with("datasets/sample_gcs.csv")
    mock_blob.upload_from_string.assert_called_with(b"a,b\n10,20\n")

    # 2. Comprobar existencia
    assert storage.exists("sample_gcs.csv") is True

    # 3. Leer archivo
    read_bytes = storage.read_file("sample_gcs.csv")
    assert read_bytes == b"gcs_mock_content"

    # 4. Obtener ruta sincronizada
    path = storage.get_path("sample_gcs.csv")
    assert path.exists()

    # 5. Listar blobs
    mock_blob_item = MagicMock()
    mock_blob_item.name = "datasets/file1.csv"
    mock_bucket.list_blobs.return_value = [mock_blob_item]
    files = storage.list_files()
    assert "file1.csv" in files

    # 6. Eliminar archivo
    deleted = storage.delete_file("sample_gcs.csv")
    assert deleted is True
    mock_blob.delete.assert_called_once()


def test_gcs_storage_cleanup(tmp_path):
    mock_client = MagicMock()
    mock_bucket = MagicMock()

    mock_blob_old = MagicMock()
    mock_blob_old.time_created = datetime(2020, 1, 1, tzinfo=timezone.utc)
    mock_blob_recent = MagicMock()
    mock_blob_recent.time_created = datetime.now(timezone.utc)

    mock_client.bucket.return_value = mock_bucket
    mock_bucket.list_blobs.return_value = [mock_blob_old, mock_blob_recent]

    storage = GCSStorageBackend(
        bucket_name="my-dataflow-bucket",
        cache_dir=tmp_path,
        client=mock_client,
    )

    deleted_count = storage.cleanup(max_age_seconds=3600, max_files=10)
    assert deleted_count >= 1
    mock_blob_old.delete.assert_called_once()


def test_s3_storage_backend_requires_bucket_name(tmp_path):
    with pytest.raises(FunctionalException) as exc_info:
        S3StorageBackend(bucket_name="", cache_dir=tmp_path)
    assert exc_info.value.code == "S3_BUCKET_NAME_MISSING"


def test_s3_storage_backend_with_mock_client(tmp_path):
    mock_client = MagicMock()

    body_mock = MagicMock()
    body_mock.read.return_value = b"s3_mock_bytes"
    mock_client.get_object.return_value = {"Body": body_mock}
    mock_client.head_object.return_value = {"ContentLength": 13}
    mock_client.list_objects_v2.return_value = {
        "Contents": [{"Key": "dataflow/s3_dataset.csv", "LastModified": datetime.now(timezone.utc)}]
    }

    storage = S3StorageBackend(
        bucket_name="my-s3-bucket",
        endpoint_url="https://s3.us-east-1.amazonaws.com",
        region_name="us-east-1",
        aws_access_key_id="mock_key",
        aws_secret_access_key="mock_secret",
        prefix="dataflow/",
        cache_dir=tmp_path,
        client=mock_client,
    )

    # 1. Guardar archivo
    saved_path = storage.save_file("s3_test.csv", b"x,y\n100,200\n")
    assert saved_path.exists()
    mock_client.put_object.assert_called_with(
        Bucket="my-s3-bucket",
        Key="dataflow/s3_test.csv",
        Body=b"x,y\n100,200\n",
    )

    # 2. Comprobar existencia
    assert storage.exists("s3_test.csv") is True

    # 3. Leer archivo
    data = storage.read_file("s3_test.csv")
    assert data == b"s3_mock_bytes"

    # 4. Obtener ruta
    path = storage.get_path("s3_test.csv")
    assert path.exists()

    # 5. Listar objetos
    files = storage.list_files()
    assert "s3_dataset.csv" in files

    # 6. Eliminar objeto
    deleted = storage.delete_file("s3_test.csv")
    assert deleted is True
    mock_client.delete_object.assert_called_with(Bucket="my-s3-bucket", Key="dataflow/s3_test.csv")


def test_storage_factory_and_reset(tmp_path):
    reset_storage()

    # 1. Por defecto -> LocalStorageBackend
    storage = get_storage()
    assert isinstance(storage, LocalStorageBackend)

    # 2. Backend invalido
    with pytest.raises(FunctionalException) as exc_info:
        get_storage(backend_type="unknown_storage_provider")
    assert exc_info.value.code == "INVALID_STORAGE_BACKEND"

    # 3. GCS explicit instantiation
    mock_gcs_client = MagicMock()
    gcs_backend = GCSStorageBackend(bucket_name="bkt", cache_dir=tmp_path, client=mock_gcs_client)
    assert gcs_backend.bucket_name == "bkt"

    # 4. S3 explicit instantiation
    mock_s3_client = MagicMock()
    s3_backend = S3StorageBackend(bucket_name="s3-bkt", cache_dir=tmp_path, client=mock_s3_client)
    assert s3_backend.bucket_name == "s3-bkt"

    reset_storage()
