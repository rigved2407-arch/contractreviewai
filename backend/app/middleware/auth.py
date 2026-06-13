from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings

EXEMPT_PATHS = {
    "/api/health",
    "/",
    "/dashboard",
    "/billing",
    "/contracts/new",
    "/login",
}


class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not settings.auth_enabled:
            return await call_next(request)

        path = request.url.path

        if path in EXEMPT_PATHS or path.startswith("/static") or path.startswith("/web/"):
            return await call_next(request)

        if path.startswith("/api/"):
            api_key = request.headers.get("X-API-Key") or request.query_params.get("api_key")
            if not api_key or api_key != settings.api_key:
                return JSONResponse(status_code=401, content={"detail": "Invalid or missing API key"})

        return await call_next(request)
