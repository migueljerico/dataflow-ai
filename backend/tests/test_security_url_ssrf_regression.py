import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock

from app.main import app
from app.core.security_url import validate_and_resolve_url

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


# ─────────────────────────────────────────────────────────────────────────────
# CATEGORÍA A: Rangos de IP directamente bloqueados (Metadata Cloud & Loopback)
# ─────────────────────────────────────────────────────────────────────────────

def test_regression_ssrf_gcp_metadata_ip():
    """
    Caso 1 de Penetration Testing:
    URL: http://169.254.169.254/computeMetadata/v1/
    Resultado esperado: 400 — code: SSRF_BLOCKED_IP
    Body details: {"blocked_ip": "169.254.169.254", "host": "169.254.169.254"}
    """
    response = client.post(
        "/api/v1/datasets/from-url",
        json={"url": "http://169.254.169.254/computeMetadata/v1/"}
    )
    assert response.status_code == 400
    data = response.json()
    assert data["code"] == "SSRF_BLOCKED_IP"
    assert data["details"]["blocked_ip"] == "169.254.169.254"
    assert data["details"]["host"] == "169.254.169.254"


def test_regression_ssrf_ipv4_loopback_ip():
    """
    Caso 2 de Penetration Testing:
    URL: http://127.0.0.1/
    Resultado esperado: 400 — code: SSRF_BLOCKED_IP
    Body details: {"blocked_ip": "127.0.0.1", "host": "127.0.0.1"}
    """
    response = client.post(
        "/api/v1/datasets/from-url",
        json={"url": "http://127.0.0.1/"}
    )
    assert response.status_code == 400
    data = response.json()
    assert data["code"] == "SSRF_BLOCKED_IP"
    assert data["details"]["blocked_ip"] == "127.0.0.1"
    assert data["details"]["host"] == "127.0.0.1"


# ─────────────────────────────────────────────────────────────────────────────
# CATEGORÍA B: Resolución de hostname a IP antes de validar (DNS Pre-resolution)
# ─────────────────────────────────────────────────────────────────────────────

def test_regression_ssrf_hostname_dns_resolution_localhost():
    """
    Caso 3 de Penetration Testing:
    URL: http://localhost/
    Resultado esperado: 400 — code: SSRF_BLOCKED_IP
    Body details: {"blocked_ip": "127.0.0.1", "host": "localhost"}
    Confirma que se resuelve el hostname a IP antes de validar, no solo comparación de texto.
    """
    response = client.post(
        "/api/v1/datasets/from-url",
        json={"url": "http://localhost/"}
    )
    assert response.status_code == 400
    data = response.json()
    assert data["code"] == "SSRF_BLOCKED_IP"
    assert data["details"]["blocked_ip"] in ("127.0.0.1", "::1")
    assert data["details"]["host"] == "localhost"


# ─────────────────────────────────────────────────────────────────────────────
# CATEGORÍA C: Normalización de formatos alternativos de IP (Decimal, Hex, Octal)
# ─────────────────────────────────────────────────────────────────────────────

def test_regression_ssrf_ip_decimal_notation():
    """
    Caso 4 de Penetration Testing:
    URL: http://2130706433/ (127.0.0.1 en notación decimal)
    Resultado esperado: 400 — code: SSRF_BLOCKED_IP
    Body details: {"blocked_ip": "127.0.0.1", "host": "2130706433"}
    Confirma normalización de IP antes de comparar contra rangos bloqueados.
    """
    response = client.post(
        "/api/v1/datasets/from-url",
        json={"url": "http://2130706433/"}
    )
    assert response.status_code == 400
    data = response.json()
    assert data["code"] == "SSRF_BLOCKED_IP"
    assert data["details"]["blocked_ip"] == "127.0.0.1"
    assert data["details"]["host"] == "2130706433"


def test_regression_ssrf_ip_hexadecimal_notation():
    """
    Caso 5 de Penetration Testing:
    URL: http://0x7f.0.0.1/ (127.0.0.1 en hexadecimal)
    Resultado esperado: 400 — code: SSRF_BLOCKED_IP
    Body details: {"blocked_ip": "127.0.0.1", "host": "0x7f.0.0.1"}
    """
    response = client.post(
        "/api/v1/datasets/from-url",
        json={"url": "http://0x7f.0.0.1/"}
    )
    assert response.status_code == 400
    data = response.json()
    assert data["code"] == "SSRF_BLOCKED_IP"
    assert data["details"]["blocked_ip"] == "127.0.0.1"
    assert data["details"]["host"] == "0x7f.0.0.1"


def test_regression_ssrf_ip_octal_notation():
    """
    Caso 6 de Penetration Testing:
    URL: http://0177.0.0.1/ (127.0.0.1 en octal)
    Resultado esperado: 400 — code: SSRF_BLOCKED_IP
    Body details: {"blocked_ip": "127.0.0.1", "host": "0177.0.0.1"}
    """
    response = client.post(
        "/api/v1/datasets/from-url",
        json={"url": "http://0177.0.0.1/"}
    )
    assert response.status_code == 400
    data = response.json()
    assert data["code"] == "SSRF_BLOCKED_IP"
    assert data["details"]["blocked_ip"] == "127.0.0.1"
    assert data["details"]["host"] == "0177.0.0.1"


# ─────────────────────────────────────────────────────────────────────────────
# CATEGORÍA D: Rechazo de credenciales embebidas (URL Userinfo Spoofing)
# ─────────────────────────────────────────────────────────────────────────────

def test_regression_ssrf_embedded_credentials_disallowed():
    """
    Caso 7 de Penetration Testing:
    URL: http://169.254.169.254@raw.githubusercontent.com/
    Resultado esperado: 400 — code: EMBEDDED_CREDENTIALS_DISALLOWED
    Body: {} rechazo directo de credenciales embebidas en la URL.
    """
    response = client.post(
        "/api/v1/datasets/from-url",
        json={"url": "http://169.254.169.254@raw.githubusercontent.com/"}
    )
    assert response.status_code == 400
    data = response.json()
    assert data["code"] == "EMBEDDED_CREDENTIALS_DISALLOWED"


# ─────────────────────────────────────────────────────────────────────────────
# CASO POSITIVO DE CONTROL: URL pública legítima no bloqueada
# ─────────────────────────────────────────────────────────────────────────────

def test_regression_ssrf_positive_control_legitimate_url():
    """
    Caso positivo de control verificado en producción:
    URL: https://raw.githubusercontent.com/datasets/gdp/master/data/gdp.csv
    Resultado esperado: 201 — dataset_id generado, status: 'validated'
    """
    csv_sample = b"Country Name,Country Code,Year,Value\nSpain,ESP,2022,1417800000000\n"
    
    with patch("app.core.security_url.httpx.AsyncClient") as mock_client_cls:
        mock_client_cls.return_value = _setup_stream_mock(
            status_code=200,
            headers={"content-type": "text/csv", "content-length": str(len(csv_sample))},
            byte_chunks=[csv_sample]
        )

        response = client.post(
            "/api/v1/datasets/from-url",
            json={"url": "https://raw.githubusercontent.com/datasets/gdp/master/data/gdp.csv"}
        )

        assert response.status_code == 201
        data = response.json()
        assert "dataset_id" in data
        assert data["filename"] == "gdp.csv"
        assert data["status"] == "validated"
        assert data["column_count"] == 4
