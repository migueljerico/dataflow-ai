import ipaddress
import socket
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpcore
import httpx
from httpcore._backends.auto import AutoBackend

from app.core.exceptions import FunctionalException

BLOCKED_IP_NETWORKS = [
    # IPv4 Privadas, Loopback, Link-Local y Metadatos
    ipaddress.ip_network("127.0.0.0/8"),  # Loopback
    ipaddress.ip_network("10.0.0.0/8"),  # RFC1918 Privada Clase A
    ipaddress.ip_network("172.16.0.0/12"),  # RFC1918 Privada Clase B
    ipaddress.ip_network("192.168.0.0/16"),  # RFC1918 Privada Clase C
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local / GCP & Cloud Metadata
    ipaddress.ip_network("0.0.0.0/8"),  # Current network
    ipaddress.ip_network("224.0.0.0/4"),  # Multicast
    ipaddress.ip_network("240.0.0.0/4"),  # Reservada
    # IPv6 Privadas, Loopback, Link-Local y Especiales
    ipaddress.ip_network("::1/128"),  # Loopback IPv6
    ipaddress.ip_network("::/128"),  # Unspecified IPv6
    ipaddress.ip_network("fe80::/10"),  # Link-local IPv6
    ipaddress.ip_network("fc00::/7"),  # Unique Local Addresses / ULA IPv6
    ipaddress.ip_network("::ffff:0:0/96"),  # IPv4-mapped IPv6
    ipaddress.ip_network("64:ff9b::/96"),  # IPv4/IPv6 translation
    ipaddress.ip_network("ff00::/8"),  # Multicast IPv6
]

ALLOWED_SCHEMES = {"http", "https"}


def is_ip_blocked(ip_str: str) -> bool:
    """
    Verifica si una dirección IP (IPv4 o IPv6) pertenece a rangos privados,
    locales, de loopback, metadatos en la nube o no enrutables públicamente.
    """
    try:
        clean_ip_str = ip_str.strip("[]")
        ip = ipaddress.ip_address(clean_ip_str)

        # Si es una dirección IPv4 mapeada en IPv6 (::ffff:127.0.0.1), evaluar la IPv4 subyacente
        if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
            ip = ip.ipv4_mapped

        # Chequeo estricto contra la lista de redes prohibidas y propiedades nativas
        if any(ip in net for net in BLOCKED_IP_NETWORKS):
            return True
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            return True

        return False
    except ValueError:
        return True


def _try_parse_custom_ipv4(host_str: str) -> Optional[str]:
    """
    Intenta parsear y normalizar notaciones numéricas alternativas de IPv4 (decimal entero, hex, octal).
    Ejemplos:
    - '2130706433' -> '127.0.0.1'
    - '0x7f.0.0.1' -> '127.0.0.1'
    - '0177.0.0.1' -> '127.0.0.1'
    """
    host_clean = host_str.strip().strip("[]")
    # 1. Entero decimal puro (ej. 2130706433)
    if host_clean.isdigit():
        try:
            num = int(host_clean, 10)
            if 0 <= num <= 0xFFFFFFFF:
                return str(ipaddress.IPv4Address(num))
        except (ValueError, OverflowError):
            pass

    # 2. Notaciones con puntos (decimal, hex 0x.., octal 0..)
    if "." in host_clean:
        parts = host_clean.split(".")
        if len(parts) == 4:
            try:
                octets = []
                for p in parts:
                    p = p.strip()
                    if p.startswith(("0x", "0X")):
                        val = int(p, 16)
                    elif p.startswith("0") and len(p) > 1 and p.isdigit():
                        val = int(p, 8)
                    elif p.isdigit():
                        val = int(p, 10)
                    else:
                        return None
                    if 0 <= val <= 255:
                        octets.append(str(val))
                    else:
                        return None
                if len(octets) == 4:
                    normalized = ".".join(octets)
                    return str(ipaddress.IPv4Address(normalized))
            except (ValueError, OverflowError):
                pass
    return None


def validate_and_resolve_url(url_str: str) -> Dict[str, Any]:
    """
    Parsea la URL con urlsplit, valida esquema y puertos, comprueba ausencia de credenciales,
    resuelve el DNS una única vez y verifica que todas las IPs candidatas sean públicas.
    Reconstruye una URL segura y canónica y retorna los datos de conexión con IP Pinning.
    """
    if not url_str or not isinstance(url_str, str):
        raise FunctionalException(
            message="La URL proporcionada está vacía o no es válida.", code="INVALID_URL", status_code=400
        )

    cleaned_url = url_str.strip()
    parsed = urllib.parse.urlsplit(cleaned_url)

    scheme = parsed.scheme.lower()
    if scheme not in ALLOWED_SCHEMES:
        raise FunctionalException(
            message=f"Esquema de URL no permitido ('{parsed.scheme}'). Solo se aceptan URLs 'http' o 'https'.",
            code="INVALID_URL_SCHEME",
            status_code=400,
            details={"allowed_schemes": list(ALLOWED_SCHEMES)},
        )

    hostname = parsed.hostname
    if not hostname:
        raise FunctionalException(
            message="La URL no contiene un nombre de host válido.", code="INVALID_URL_HOST", status_code=400
        )

    # Validar que no contenga credenciales de autenticación embebidas
    if parsed.username or parsed.password:
        raise FunctionalException(
            message="No se permiten credenciales embebidas en la URL.",
            code="EMBEDDED_CREDENTIALS_DISALLOWED",
            status_code=400,
        )

    port = parsed.port or (443 if scheme == "https" else 80)

    # Normalización proactiva de formatos de IP alternativos (decimal, hex, octal)
    normalized_ip = _try_parse_custom_ipv4(hostname)
    if normalized_ip:
        if is_ip_blocked(normalized_ip):
            raise FunctionalException(
                message=f"Acceso denegado por seguridad: el destino ({normalized_ip}) es una dirección IP privada o restringida.",
                code="SSRF_BLOCKED_IP",
                status_code=400,
                details={"blocked_ip": normalized_ip, "host": hostname},
            )
        addr_info = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (normalized_ip, port))]
    else:
        # Resolución DNS única
        try:
            addr_info = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
        except socket.gaierror as e:
            raise FunctionalException(
                message=f"No se pudo resolver el nombre de dominio '{hostname}'. Verifica que la URL sea correcta.",
                code="DNS_RESOLUTION_FAILED",
                status_code=400,
                details={"technical_error": str(e)},
            ) from e

    validated_ips: List[str] = []
    for _family, _, _, _, sockaddr in addr_info:
        ip_candidate = sockaddr[0]
        if is_ip_blocked(ip_candidate):
            raise FunctionalException(
                message=f"Acceso denegado por seguridad: el destino ({ip_candidate}) es una dirección IP privada o restringida.",
                code="SSRF_BLOCKED_IP",
                status_code=400,
                details={"blocked_ip": ip_candidate, "host": hostname},
            )
        if ip_candidate not in validated_ips:
            validated_ips.append(ip_candidate)

    if not validated_ips:
        raise FunctionalException(
            message=f"No se encontraron direcciones IP públicas válidas para '{hostname}'.",
            code="NO_VALID_PUBLIC_IP",
            status_code=400,
        )

    pinned_ip = validated_ips[0]

    # Reconstrucción explícita de URL canónica a partir de componentes validados
    netloc = (
        f"{hostname}:{port}" if ((scheme == "http" and port != 80) or (scheme == "https" and port != 443)) else hostname
    )
    path = parsed.path if parsed.path else "/"
    safe_url = urllib.parse.urlunsplit((scheme, netloc, path, parsed.query, ""))

    return {
        "url": cleaned_url,
        "safe_url": safe_url,
        "scheme": scheme,
        "hostname": hostname,
        "port": port,
        "path": path,
        "query": parsed.query,
        "pinned_ip": pinned_ip,
    }


class PinnedAsyncNetworkBackend(AutoBackend):
    """
    Backend de red que fuerza la conexión TCP directamente a la IP validada
    (IP Pinning), evitando que se vuelva a consultar el DNS y mitigando DNS Rebinding.
    """

    def __init__(self, pinned_ip: str):
        super().__init__()
        self.pinned_ip = pinned_ip

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: Optional[float] = None,
        local_address: Optional[str] = None,
        socket_options: Any = None,
    ) -> Any:
        return await super().connect_tcp(
            self.pinned_ip, port, timeout=timeout, local_address=local_address, socket_options=socket_options
        )


class PinnedAsyncHTTPTransport(httpx.AsyncHTTPTransport):
    """
    Transporte HTTP de httpx con soporte de IP Pinning y validación TLS SNI
    contra el nombre de host original.
    """

    def __init__(self, pinned_ip: str, **kwargs):
        super().__init__(**kwargs)
        backend = PinnedAsyncNetworkBackend(pinned_ip)
        self._pool = httpcore.AsyncConnectionPool(
            ssl_context=self._pool._ssl_context,
            max_connections=self._pool._max_connections,
            max_keepalive_connections=self._pool._max_keepalive_connections,
            keepalive_expiry=self._pool._keepalive_expiry,
            http1=self._pool._http1,
            http2=self._pool._http2,
            retries=self._pool._retries,
            network_backend=backend,
        )


def _extract_filename_from_response(response: httpx.Response, url: str) -> str:
    """Extrae el nombre de archivo desde Content-Disposition o de la ruta de la URL."""
    content_disposition = response.headers.get("content-disposition", "")
    if "filename=" in content_disposition:
        parts = content_disposition.split("filename=")
        if len(parts) > 1:
            name = parts[1].strip("\"'; ")
            if name:
                return Path(name).name

    parsed_path = urllib.parse.urlparse(url).path
    candidate_name = Path(parsed_path).name
    if candidate_name and "." in candidate_name:
        return candidate_name

    content_type = response.headers.get("content-type", "").lower()
    if "excel" in content_type or "spreadsheet" in content_type:
        return "imported_dataset.xlsx"
    return "imported_dataset.csv"


async def safe_download_url_to_file(
    url: str, destination_path: Path, max_bytes: int, timeout_seconds: float = 20.0, max_redirects: int = 3
) -> Dict[str, Any]:
    """
    Descarga de forma segura un archivo remoto en streaming a un fichero local:
    - Valida contra SSRF en cada salto (incluidas redirecciones).
    - Aplica IP Pinning para mitigar DNS Rebinding.
    - Preserva TLS SNI para certificados HTTPS válidos.
    - Corta inmediatamente si el tamaño acumulado o Content-Length supera max_bytes.
    - Maneja timeouts defensivos.
    """
    current_url = url
    redirect_count = 0

    while True:
        target_info = validate_and_resolve_url(current_url)
        pinned_ip = target_info["pinned_ip"]
        safe_url = target_info.get("safe_url") or target_info["url"]
        transport = PinnedAsyncHTTPTransport(pinned_ip)

        headers = {
            "Host": target_info["hostname"],
            "User-Agent": "DataFlow-AI/1.2 (Dataset Importer; Portfolio BI)",
            "Accept": "text/csv, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, application/vnd.ms-excel, text/plain, */*",
        }

        try:
            async with httpx.AsyncClient(
                transport=transport, timeout=timeout_seconds, follow_redirects=False
            ) as client:
                async with client.stream("GET", safe_url, headers=headers) as response:
                    # Manejo explícito y controlado de redirecciones
                    if response.status_code in (301, 302, 303, 307, 308):
                        redirect_count += 1
                        if redirect_count > max_redirects:
                            raise FunctionalException(
                                message=f"Se excedió el número máximo de redirecciones permitidas ({max_redirects}).",
                                code="TOO_MANY_REDIRECTS",
                                status_code=400,
                            )

                        location = response.headers.get("location")
                        if not location:
                            raise FunctionalException(
                                message="El servidor remoto envió una redirección sin cabecera 'Location'.",
                                code="INVALID_REDIRECT",
                                status_code=400,
                            )

                        current_url = urllib.parse.urljoin(safe_url, location)
                        continue

                    if response.status_code != 200:
                        raise FunctionalException(
                            message=f"El servidor remoto respondió con estado HTTP {response.status_code}.",
                            code="REMOTE_SERVER_ERROR",
                            status_code=400,
                            details={"http_status": response.status_code, "url": current_url},
                        )

                    # Validación previa por cabecera Content-Length si viene informada
                    content_length_header = response.headers.get("content-length")
                    if content_length_header and content_length_header.isdigit():
                        content_length = int(content_length_header)
                        if content_length > max_bytes:
                            max_mb = round(max_bytes / (1024 * 1024), 2)
                            actual_mb = round(content_length / (1024 * 1024), 2)
                            raise FunctionalException(
                                message=f"El archivo remoto supera el límite permitido de {max_mb} MB (tamaño declarado: {actual_mb} MB).",
                                code="FILE_TOO_LARGE",
                                status_code=400,
                                details={"max_bytes": max_bytes, "declared_bytes": content_length},
                            )

                    # Streaming defensivo por chunks escribiendo a disco
                    downloaded_bytes = 0
                    with open(destination_path, "wb") as f:
                        async for chunk in response.aiter_bytes(chunk_size=65536):
                            downloaded_bytes += len(chunk)
                            if downloaded_bytes > max_bytes:
                                f.close()
                                if destination_path.exists():
                                    destination_path.unlink(missing_ok=True)
                                max_mb = round(max_bytes / (1024 * 1024), 2)
                                raise FunctionalException(
                                    message=f"La descarga se canceló porque el archivo superó el límite de {max_mb} MB.",
                                    code="FILE_TOO_LARGE",
                                    status_code=400,
                                    details={"max_bytes": max_bytes, "downloaded_bytes": downloaded_bytes},
                                )
                            f.write(chunk)

                    if downloaded_bytes == 0:
                        if destination_path.exists():
                            destination_path.unlink(missing_ok=True)
                        raise FunctionalException(
                            message="El archivo descargado está vacío (0 bytes).", code="EMPTY_FILE", status_code=400
                        )

                    filename = _extract_filename_from_response(response, current_url)
                    content_type = response.headers.get("content-type", "")

                    return {
                        "filename": filename,
                        "downloaded_bytes": downloaded_bytes,
                        "content_type": content_type,
                        "final_url": current_url,
                        "pinned_ip": pinned_ip,
                    }

        except (httpx.TimeoutException, httpcore.TimeoutException):
            if destination_path.exists():
                destination_path.unlink(missing_ok=True)
            raise FunctionalException(
                message=f"Tiempo de espera agotado al intentar descargar el archivo tras {timeout_seconds} segundos.",
                code="DOWNLOAD_TIMEOUT",
                status_code=408,
                details={"timeout_seconds": timeout_seconds, "url": current_url},
            ) from None
        except (httpx.NetworkError, httpcore.NetworkError) as e:
            if destination_path.exists():
                destination_path.unlink(missing_ok=True)
            raise FunctionalException(
                message=f"Error de conexión al acceder al servidor remoto: {str(e)}",
                code="REMOTE_CONNECTION_ERROR",
                status_code=400,
                details={"technical_error": str(e), "url": current_url},
            ) from e
