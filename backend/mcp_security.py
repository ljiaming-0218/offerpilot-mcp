import hashlib
import hmac
import logging
import threading
import time
from collections import defaultdict, deque
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


logger = logging.getLogger("offerpilot.mcp.security")


class SlidingWindowRateLimiter:
    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, now: float | None = None) -> tuple[bool, int]:
        current = time.monotonic() if now is None else now
        cutoff = current - self.window_seconds

        with self._lock:
            timestamps = self._requests[key]
            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()

            if len(timestamps) >= self.max_requests:
                retry_after = max(1, int(timestamps[0] + self.window_seconds - current) + 1)
                return False, retry_after

            timestamps.append(current)
            return True, 0


class McpSecurityMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        access_token: str,
        rate_limit_requests: int,
        rate_limit_window_seconds: int,
    ) -> None:
        self.app = app
        self.access_token = access_token
        self.rate_limiter = SlidingWindowRateLimiter(
            max_requests=rate_limit_requests,
            window_seconds=rate_limit_window_seconds,
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        started_at = time.perf_counter()
        client_id = _client_id(scope)
        method = scope.get("method", "UNKNOWN")

        if not self.access_token:
            logger.error("MCP request rejected: access token is not configured")
            await _json_response(
                scope,
                receive,
                send,
                status_code=503,
                content={"error": "MCP_AUTH_NOT_CONFIGURED", "message": "MCP 访问令牌未配置"},
            )
            return

        provided_token = _bearer_token(scope)
        if provided_token is None or not hmac.compare_digest(provided_token, self.access_token):
            logger.warning("MCP authentication failed method=%s client=%s", method, client_id)
            await _json_response(
                scope,
                receive,
                send,
                status_code=401,
                content={"error": "INVALID_MCP_TOKEN", "message": "MCP 访问令牌无效"},
                headers={"WWW-Authenticate": "Bearer"},
            )
            return

        allowed, retry_after = self.rate_limiter.check(client_id)
        if not allowed:
            logger.warning("MCP rate limit exceeded method=%s client=%s", method, client_id)
            await _json_response(
                scope,
                receive,
                send,
                status_code=429,
                content={"error": "MCP_RATE_LIMITED", "message": "MCP 请求过于频繁"},
                headers={"Retry-After": str(retry_after)},
            )
            return

        status_code = 500

        async def audit_send(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, audit_send)
        finally:
            latency_ms = int((time.perf_counter() - started_at) * 1000)
            logger.info(
                "MCP request method=%s status=%s client=%s latency_ms=%s",
                method,
                status_code,
                client_id,
                latency_ms,
            )


def _bearer_token(scope: Scope) -> str | None:
    headers = {key.lower(): value for key, value in scope.get("headers", [])}
    authorization = headers.get(b"authorization", b"").decode("latin-1")
    scheme, separator, token = authorization.partition(" ")
    if not separator or scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def _client_id(scope: Scope) -> str:
    client = scope.get("client")
    host = client[0] if client else "unknown"
    return hashlib.sha256(host.encode("utf-8")).hexdigest()[:12]


async def _json_response(
    scope: Scope,
    receive: Receive,
    send: Send,
    status_code: int,
    content: dict,
    headers: dict[str, str] | None = None,
) -> None:
    response = JSONResponse(content=content, status_code=status_code, headers=headers)
    await response(scope, receive, send)
