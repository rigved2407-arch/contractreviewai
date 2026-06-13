import time
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.database import SessionLocal
from app.models import AuditLog
from app.config import settings

logger = logging.getLogger("contract-review.audit")


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        duration_ms = int((time.time() - start) * 1000)

        if not settings.audit_enabled:
            return response
        if not request.url.path.startswith("/api/") or request.url.path == "/api/health":
            return response

        db = SessionLocal()
        try:
            log = AuditLog(
                method=request.method,
                path=str(request.url.path),
                query_params=str(request.url.query),
                status_code=response.status_code,
                duration_ms=duration_ms,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
            )
            db.add(log)
            db.commit()
        except Exception as e:
            logger.warning("Failed to write audit log: %s", e)
        finally:
            db.close()

        return response
