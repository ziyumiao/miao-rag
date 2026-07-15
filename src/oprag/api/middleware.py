"""API Key 认证中间件"""

from __future__ import annotations

from fastapi import FastAPI, Request, HTTPException
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
