"""安全中间件：API Key 认证 + 速率限制"""

from __future__ import annotations

import time
from collections import defaultdict

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


EXCLUDED_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}


class ApiKeyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, api_key: str):
        super().__init__(app)
        self._api_key = api_key

    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)

        if request.url.path in EXCLUDED_PATHS:
            return await call_next(request)

        key = request.headers.get("X-API-Key")
        if not key or key != self._api_key:
            return JSONResponse(
                status_code=401,
                content={"detail": "无效的 API Key"},
            )

        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, session_qps: int = 2):
        super().__init__(app)
        self._session_qps = session_qps
        # {session_id: [(timestamp, ...)]}
        self._session_requests: dict[str, list[float]] = defaultdict(list)
        # 定期清理过期记录
        self._last_cleanup = time.monotonic()

    async def dispatch(self, request: Request, call_next):
        now = time.monotonic()

        # 每 60 秒清理一次过期记录
        if now - self._last_cleanup > 60:
            self._cleanup(now)
            self._last_cleanup = now

        session_id = request.headers.get("X-Session-Id") or "default"

        # 检查 session 限流（滑动窗口 1 秒）
        self._session_requests[session_id] = [
            t for t in self._session_requests[session_id] if now - t < 1.0
        ]
        self._session_requests[session_id].append(now)

        remaining = self._session_qps - len(self._session_requests[session_id])

        if remaining < 0:
            return JSONResponse(
                status_code=429,
                content={"detail": "请求过于频繁，请稍后再试"},
                headers={
                    "X-RateLimit-Limit": str(self._session_qps),
                    "X-RateLimit-Remaining": "0",
                    "Retry-After": "1",
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self._session_qps)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
        return response

    def _cleanup(self, now: float):
        expired = [s for s, times in self._session_requests.items() if all(now - t > 1.0 for t in times)]
        for session_id in expired:
            del self._session_requests[session_id]
