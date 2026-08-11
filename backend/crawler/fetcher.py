import time
from urllib.parse import urljoin

import requests

from backend.crawler.url_safety import UnsafeUrlError, validate_public_http_url


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36 OfferPilotMCP/0.1"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,*/*;q=0.8"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Connection": "close",
}

MAX_REDIRECTS = 5
MAX_RESPONSE_BYTES = 5 * 1024 * 1024
REDIRECT_STATUS_CODES = {301, 302, 303, 307, 308}


def fetch_public_page(url: str) -> str:
    last_error: Exception | None = None

    # 最多请求两次，不做高频重试
    for attempt in range(2):
        try:
            with requests.Session() as session:
                # 避免错误的 HTTP_PROXY/HTTPS_PROXY 环境变量干扰TLS连接
                session.trust_env = False

                return _fetch_with_safe_redirects(session, url)

        except UnsafeUrlError:
            raise

        except (
            requests.Timeout,
            requests.SSLError,
            requests.ConnectionError,
        ) as exc:
            last_error = exc

            if attempt == 0:
                time.sleep(1)
                continue

        except requests.RequestException as exc:
            raise RuntimeError(f"网页请求失败：{exc}") from exc

    raise RuntimeError(
        f"目标网页连接异常，两次请求均失败：{last_error}"
    ) from last_error


def _fetch_with_safe_redirects(session: requests.Session, url: str) -> str:
    current_url = url

    for redirect_count in range(MAX_REDIRECTS + 1):
        validate_public_http_url(current_url)

        response = session.get(
            current_url,
            headers=HEADERS,
            timeout=(5, 30),
            allow_redirects=False,
            stream=True,
        )

        if response.status_code in REDIRECT_STATUS_CODES:
            location = response.headers.get("Location")
            response.close()

            if not location:
                raise RuntimeError("网页返回重定向，但没有提供目标地址")
            if redirect_count >= MAX_REDIRECTS:
                raise RuntimeError("网页重定向次数超过限制")

            current_url = urljoin(current_url, location)
            continue

        try:
            response.raise_for_status()
            return _read_limited_text(response)
        finally:
            response.close()

    raise RuntimeError("网页重定向次数超过限制")


def _read_limited_text(response: requests.Response) -> str:
    content_length = response.headers.get("Content-Length")
    if content_length:
        try:
            if int(content_length) > MAX_RESPONSE_BYTES:
                raise RuntimeError("网页响应体超过 5 MB 限制")
        except ValueError:
            pass

    body = bytearray()
    for chunk in response.iter_content(chunk_size=64 * 1024):
        if not chunk:
            continue
        body.extend(chunk)
        if len(body) > MAX_RESPONSE_BYTES:
            raise RuntimeError("网页响应体超过 5 MB 限制")

    encoding = response.encoding or "utf-8"
    return bytes(body).decode(encoding, errors="replace")
