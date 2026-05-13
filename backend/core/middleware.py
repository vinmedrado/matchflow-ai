from __future__ import annotations

from typing import Callable

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from backend.core.logging_config import get_logger

logger = get_logger("matchflow.auth_middleware")

PUBLIC_PATH_PREFIXES = (
    "/health",
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/refresh",
    "/api/auth/forgot-password",
    "/api/auth/reset-password",
    "/api/auth/verify-email",
    "/api/auth/resend-verification",
    "/api/auth/status",
    "/ready",
    "/metrics",
    "/api/health",
    "/api/demo",
    "/api/data-engine/public-status",
    "/docs",
    "/redoc",
    "/openapi.json",
)


class AuthMiddleware(BaseHTTPMiddleware):
    """Global local/dev auth middleware for private API routes."""

    def __init__(self, app, auth_manager, enabled: bool = True) -> None:
        super().__init__(app)
        self.auth_manager = auth_manager
        self.enabled = enabled

    async def dispatch(self, request: Request, call_next: Callable):
        if not self.enabled:
            return await call_next(request)

        path = request.url.path
        if request.method == "OPTIONS" or any(path.startswith(prefix) for prefix in PUBLIC_PATH_PREFIXES):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            logger.warning("Requisição privada bloqueada sem token: path=%s", path)
            return self._unauthorized("Token ausente. Faça login novamente.")

        token = auth_header.replace("Bearer ", "", 1).strip()
        record = self.auth_manager.validate_token(token)
        if not record:
            logger.warning("Requisição privada bloqueada por token inválido/expirado: path=%s", path)
            return self._unauthorized("Token inválido ou expirado. Faça login novamente.")

        request.state.user = self.auth_manager.user_payload(record)
        logger.info("Requisição autenticada: path=%s user=%s", path, record.email)
        return await call_next(request)

    @staticmethod
    def _unauthorized(message: str) -> JSONResponse:
        return JSONResponse(
            status_code=401,
            content={
                "ok": False,
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": message,
                },
            },
        )
