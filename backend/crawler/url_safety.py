import ipaddress
import socket
from urllib.parse import urlsplit


ALLOWED_SCHEMES = {"http", "https"}
ALLOWED_PORTS = {80, 443}


class UnsafeUrlError(ValueError):
    pass


def validate_public_http_url(url: str) -> None:
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as exc:
        raise UnsafeUrlError("URL 格式无效") from exc

    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        raise UnsafeUrlError("只允许访问 HTTP 或 HTTPS 地址")

    if parsed.username is not None or parsed.password is not None:
        raise UnsafeUrlError("URL 不允许包含用户名或密码")

    hostname = (parsed.hostname or "").rstrip(".").lower()
    if not hostname:
        raise UnsafeUrlError("URL 缺少有效域名")

    if hostname == "localhost" or hostname.endswith(".localhost") or hostname.endswith(".local"):
        raise UnsafeUrlError("不允许访问本机或局域网域名")

    effective_port = port or (443 if parsed.scheme.lower() == "https" else 80)
    if effective_port not in ALLOWED_PORTS:
        raise UnsafeUrlError("只允许访问标准 HTTP/HTTPS 端口")

    addresses = _resolve_addresses(hostname, effective_port)
    if not addresses:
        raise UnsafeUrlError("域名没有可用的 IP 地址")

    for address in addresses:
        ip = ipaddress.ip_address(address.split("%", 1)[0])
        if not ip.is_global:
            raise UnsafeUrlError(f"目标地址不是公网 IP：{ip}")


def _resolve_addresses(hostname: str, port: int) -> set[str]:
    try:
        results = socket.getaddrinfo(
            hostname,
            port,
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror as exc:
        raise UnsafeUrlError("域名解析失败") from exc

    return {result[4][0] for result in results}
