import socket
import pytest
from unittest.mock import patch, MagicMock
from app.core.security_url import (
    is_ip_blocked,
    validate_and_resolve_url,
    PinnedAsyncNetworkBackend
)
from app.core.exceptions import FunctionalException


@pytest.mark.parametrize("blocked_ip", [
    # IPv4 Loopback & Privadas
    "127.0.0.1",
    "127.0.1.1",
    "10.0.0.1",
    "10.255.255.255",
    "172.16.0.1",
    "172.31.255.255",
    "192.168.1.1",
    "192.168.0.254",
    # GCP / Cloud Metadata Link-Local
    "169.254.169.254",
    "169.254.0.1",
    # Especiales IPv4
    "0.0.0.0",
    "224.0.0.1",
    "240.0.0.1",
    # IPv6 Loopback, Link-Local y ULA
    "::1",
    "[::1]",
    "fe80::1",
    "[fe80::1]",
    "fe80::dead:beef:1",
    "fc00::1",
    "fd00::1234",
    # IPv4-Mapped IPv6
    "::ffff:127.0.0.1",
    "[::ffff:127.0.0.1]",
    "::ffff:169.254.169.254",
    "::ffff:192.168.1.100",
])
def test_is_ip_blocked_true_for_forbidden_ranges(blocked_ip):
    assert is_ip_blocked(blocked_ip) is True


@pytest.mark.parametrize("public_ip", [
    "8.8.8.8",
    "1.1.1.1",
    "93.184.216.34",
    "185.199.108.153",
    "2606:4700:4700::1111",
])
def test_is_ip_blocked_false_for_public_ips(public_ip):
    assert is_ip_blocked(public_ip) is False


@pytest.mark.parametrize("invalid_scheme_url", [
    "file:///etc/passwd",
    "ftp://ftp.example.com/data.csv",
    "gopher://evil.com",
    "dict://127.0.0.1:11211",
    "data:text/plain;base64,SGVsbG8=",
])
def test_validate_url_rejects_non_http_schemes(invalid_scheme_url):
    with pytest.raises(FunctionalException) as exc_info:
        validate_and_resolve_url(invalid_scheme_url)
    assert exc_info.value.code == "INVALID_URL_SCHEME"


def test_validate_url_rejects_empty_or_invalid():
    with pytest.raises(FunctionalException) as exc_info:
        validate_and_resolve_url("")
    assert exc_info.value.code == "INVALID_URL"


def test_validate_url_blocks_resolved_metadata_ip():
    with patch("socket.getaddrinfo") as mock_dns:
        # Simular que el hostname resuelve a la IP de metadatos de GCP
        mock_dns.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("169.254.169.254", 80))
        ]
        with pytest.raises(FunctionalException) as exc_info:
            validate_and_resolve_url("http://internal-metadata.test/computeMetadata/v1/")
        assert exc_info.value.code == "SSRF_BLOCKED_IP"
        assert "169.254.169.254" in str(exc_info.value.details.get("blocked_ip"))


def test_validate_url_blocks_if_any_resolved_ip_is_private():
    with patch("socket.getaddrinfo") as mock_dns:
        # Simular respuesta DNS dual (una pública y una privada tipo DNS Rebinding parcial)
        mock_dns.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 80)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.5", 80)),
        ]
        with pytest.raises(FunctionalException) as exc_info:
            validate_and_resolve_url("http://dual-resolve.test/data.csv")
        assert exc_info.value.code == "SSRF_BLOCKED_IP"


def test_validate_url_returns_pinned_ip_for_public_domain():
    with patch("socket.getaddrinfo") as mock_dns:
        mock_dns.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))
        ]
        result = validate_and_resolve_url("https://example.com/dataset.csv")
        assert result["pinned_ip"] == "93.184.216.34"
        assert result["hostname"] == "example.com"
        assert result["port"] == 443
        assert result["scheme"] == "https"


@pytest.mark.anyio
async def test_pinned_network_backend_forces_pinned_ip():
    """
    Verifica que PinnedAsyncNetworkBackend redirige la llamada TCP
    a la IP fijada (pinned_ip) en lugar del host pasado.
    """
    backend = PinnedAsyncNetworkBackend("93.184.216.34")
    with patch("httpcore._backends.auto.AutoBackend.connect_tcp") as mock_connect:
        mock_connect.return_value = MagicMock()
        await backend.connect_tcp(host="evil-attacker-domain.com", port=443)
        
        # Debe haber llamado a connect_tcp con la IP fijada ("93.184.216.34"), NO con el dominio atacante
        mock_connect.assert_called_once()
        args, kwargs = mock_connect.call_args
        assert args[0] == "93.184.216.34"
        assert args[1] == 443
