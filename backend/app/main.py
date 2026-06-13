import logging
import sys
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db, SessionLocal
from app.services.playbook_engine import seed_default_playbook
from app.routers import contracts, playbooks, analysis, billing, auth
from app.web.routes import router as web_router
from app.middleware.auth import APIKeyMiddleware
from app.middleware.audit import AuditMiddleware

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("contract-review")

if settings.sentry_dsn:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.asgi import SentryASGIMiddleware

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment="production" if not settings.debug else "development",
            release=settings.app_version,
        )
        logger.info("Sentry error monitoring initialized")
    except ImportError:
        logger.warning("sentry_sdk not installed; skipping Sentry init")

app = FastAPI(title=settings.app_name, version=settings.app_version)

origins = settings.cors_origins
if isinstance(origins, str):
    origins = [o.strip() for o in origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(APIKeyMiddleware)
app.add_middleware(AuditMiddleware)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again later."},
    )


app.include_router(auth.router, prefix="/api")
app.include_router(contracts.router, prefix="/api")
app.include_router(playbooks.router, prefix="/api")
app.include_router(analysis.router, prefix="/api")
app.include_router(billing.router, prefix="/api")
app.include_router(web_router)

static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

storage = Path(settings.storage_dir)
storage.mkdir(parents=True, exist_ok=True)
(data_dir := Path("./data")).mkdir(exist_ok=True)


@app.on_event("startup")
def on_startup():
    init_db()
    logger.info("Database initialized (%s)", settings.database_url)
    if settings.encrypt_documents and not settings.encryption_key:
        logger.warning("ENCRYPT_DOCUMENTS enabled but ENCRYPTION_KEY not set — using default key (INSECURE)")
    db = SessionLocal()
    try:
        seed_default_playbook(db)
    finally:
        db.close()
    logger.info("Application started v%s", settings.app_version)


@app.get("/api/health")
def health():
    return {"status": "ok", "version": settings.app_version, "environment": "production" if not settings.debug else "development"}
