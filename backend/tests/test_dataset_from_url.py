import pytest
import io
import pandas as pd
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings

client = TestClient(app)


def _setup_stream_mock(status_code=200, headers=None, byte_chunks=None):
    if headers is None:
        headers = {}
    if byte_chunks is None:
        byte_chunks = []

    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.headers = headers

    async def mock_aiter(chunk_size=65536):
        for chunk in byte_chunks:
            yield chunk

    mock_resp.aiter_bytes = mock_aiter

    mock_stream_ctx = AsyncMock()
    mock_stream_ctx.__aenter__.return_value = mock_resp
    mock_stream_ctx.__aexit__.return_value = None

    mock_client = MagicMock()
    mock_client.stream = MagicMock(return_value=mock_stream_ctx)

    mock_client_ctx = AsyncMock()
    mock_client_ctx.__aenter__.return_value = mock_client
    mock_client_ctx.__aexit__.return_value = None

    return mock_client_ctx


def test_import_dataset_from_url_success():
    """
    Test de importación exitosa de un CSV remoto vía /api/v1/datasets/from-url
    """
    csv_data = b"id,nombre,ventas\n1,Alpha,100.5\n2,Beta,200.0\n3,Gamma,350.2\n"

    with (
        patch("app.core.security_url.validate_and_resolve_url") as mock_val,
        patch("app.core.security_url.httpx.AsyncClient") as mock_client_cls,
    ):

        mock_val.return_value = {
            "url": "https://public-open-data.org/sales.csv",
            "scheme": "https",
            "hostname": "public-open-data.org",
            "port": 443,
            "path": "/sales.csv",
            "pinned_ip": "93.184.216.34",
        }

        mock_client_cls.return_value = _setup_stream_mock(
            status_code=200,
            headers={"content-type": "text/csv", "content-length": str(len(csv_data))},
            byte_chunks=[csv_data],
        )

        response = client.post("/api/v1/datasets/from-url", json={"url": "https://public-open-data.org/sales.csv"})

        assert response.status_code == 201
        data = response.json()
        assert "dataset_id" in data
        assert data["filename"] == "sales.csv"
        assert data["row_count"] == 3
        assert data["column_count"] == 3
        assert data["columns"] == ["id", "nombre", "ventas"]
        assert data["status"] == "validated"


def test_import_dataset_from_url_blocked_ssrf_metadata():
    """
    Test de bloqueo inmediato de petición SSRF al endpoint de metadatos de GCP.
    """
    response = client.post("/api/v1/datasets/from-url", json={"url": "http://169.254.169.254/computeMetadata/v1/"})
    assert response.status_code == 400
    data = response.json()
    assert data["error"] is True
    assert data["code"] == "SSRF_BLOCKED_IP"


def test_import_dataset_from_url_blocked_ipv6_loopback():
    """
    Test de bloqueo para IPv6 loopback [::1].
    """
    response = client.post("/api/v1/datasets/from-url", json={"url": "http://[::1]:8000/internal-data.csv"})
    assert response.status_code == 400
    data = response.json()
    assert data["error"] is True
    assert data["code"] == "SSRF_BLOCKED_IP"


def test_import_dataset_from_url_blocked_ipv4_mapped_ipv6():
    """
    Test de bloqueo para dirección IPv4-mapped IPv6 ::ffff:127.0.0.1.
    """
    response = client.post(
        "/api/v1/datasets/from-url", json={"url": "http://[::ffff:127.0.0.1]:8000/internal-data.csv"}
    )
    assert response.status_code == 400
    data = response.json()
    assert data["error"] is True
    assert data["code"] == "SSRF_BLOCKED_IP"


def test_import_dataset_from_url_blocked_non_http_scheme():
    """
    Test de rechazo de esquemas no permitidos (file://).
    """
    response = client.post("/api/v1/datasets/from-url", json={"url": "file:///etc/passwd"})
    assert response.status_code == 400
    data = response.json()
    assert data["error"] is True
    assert data["code"] == "INVALID_URL_SCHEME"


def test_import_dataset_from_url_oversized_content_length():
    """
    Test de rechazo cuando la cabecera Content-Length supera el límite configurado (20 MB).
    """
    with (
        patch("app.core.security_url.validate_and_resolve_url") as mock_val,
        patch("app.core.security_url.httpx.AsyncClient") as mock_client_cls,
    ):

        mock_val.return_value = {
            "url": "https://public-open-data.org/huge_file.csv",
            "scheme": "https",
            "hostname": "public-open-data.org",
            "port": 443,
            "path": "/huge_file.csv",
            "pinned_ip": "93.184.216.34",
        }

        # 30 MB declarados
        mock_client_cls.return_value = _setup_stream_mock(
            status_code=200, headers={"content-length": str(30 * 1024 * 1024)}, byte_chunks=[b"small chunk"]
        )

        response = client.post("/api/v1/datasets/from-url", json={"url": "https://public-open-data.org/huge_file.csv"})

        assert response.status_code == 400
        data = response.json()
        assert data["error"] is True
        assert data["code"] == "FILE_TOO_LARGE"


def test_import_dataset_from_url_empty_file():
    """
    Test de rechazo cuando el archivo remoto tiene 0 bytes.
    """
    with (
        patch("app.core.security_url.validate_and_resolve_url") as mock_val,
        patch("app.core.security_url.httpx.AsyncClient") as mock_client_cls,
    ):

        mock_val.return_value = {
            "url": "https://public-open-data.org/empty.csv",
            "scheme": "https",
            "hostname": "public-open-data.org",
            "port": 443,
            "path": "/empty.csv",
            "pinned_ip": "93.184.216.34",
        }

        mock_client_cls.return_value = _setup_stream_mock(status_code=200, headers={}, byte_chunks=[])

        response = client.post("/api/v1/datasets/from-url", json={"url": "https://public-open-data.org/empty.csv"})

        assert response.status_code == 400
        data = response.json()
        assert data["error"] is True
        assert data["code"] == "EMPTY_FILE"


def test_import_dataset_from_url_remote_404():
    """
    Test de manejo de error 404 proveniente del servidor remoto.
    """
    with (
        patch("app.core.security_url.validate_and_resolve_url") as mock_val,
        patch("app.core.security_url.httpx.AsyncClient") as mock_client_cls,
    ):

        mock_val.return_value = {
            "url": "https://public-open-data.org/not_found.csv",
            "scheme": "https",
            "hostname": "public-open-data.org",
            "port": 443,
            "path": "/not_found.csv",
            "pinned_ip": "93.184.216.34",
        }

        mock_client_cls.return_value = _setup_stream_mock(status_code=404, headers={}, byte_chunks=[])

        response = client.post("/api/v1/datasets/from-url", json={"url": "https://public-open-data.org/not_found.csv"})

        assert response.status_code == 400
        data = response.json()
        assert data["error"] is True
        assert data["code"] == "REMOTE_SERVER_ERROR"
