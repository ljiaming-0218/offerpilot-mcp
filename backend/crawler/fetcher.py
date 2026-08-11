import time

import requests


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


def fetch_public_page(url: str) -> str:
    last_error: Exception | None = None

    # 最多请求两次，不做高频重试
    for attempt in range(2):
        try:
            with requests.Session() as session:
                # 避免错误的 HTTP_PROXY/HTTPS_PROXY 环境变量干扰TLS连接
                session.trust_env = False

                response = session.get(
                    url,
                    headers=HEADERS,
                    timeout=(5, 30),
                    allow_redirects=True,
                )
                response.raise_for_status()
                response.encoding = response.apparent_encoding

                return response.text

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