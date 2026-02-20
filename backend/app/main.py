import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
from sqlalchemy import text
from starlette.concurrency import run_in_threadpool

from app.routers import auth, debates, websocket
from app.config import get_settings
from app.db.session import SessionLocal
from app.dependencies import (
    SessionDep,
)
from app.services.auth_service import cleanup_expired_refresh_tokens

settings = get_settings()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_refresh_token_cleanup_once() -> int:
    """Run one cleanup pass in a sync context (for threadpool execution)."""
    db = SessionLocal()
    try:
        return cleanup_expired_refresh_tokens(db)
    finally:
        db.close()


async def refresh_token_cleanup_worker() -> None:
    """Periodically remove expired refresh tokens using bulk delete query."""
    while True:
        try:
            deleted_count = await run_in_threadpool(run_refresh_token_cleanup_once)
            if deleted_count > 0:
                logger.info(f"Deleted {deleted_count} expired refresh tokens")
        except Exception as exc:
            logger.error(f"Refresh token cleanup failed: {exc}")

        await asyncio.sleep(settings.REFRESH_TOKEN_CLEANUP_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown events."""
    # Startup
    logger.info("Starting up AI Debate System...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info("Database schema management is delegated to Alembic migrations")

    app.state.refresh_cleanup_task = asyncio.create_task(refresh_token_cleanup_worker())

    yield

    # Shutdown
    cleanup_task = getattr(app.state, "refresh_cleanup_task", None)
    if cleanup_task is not None:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            logger.info("Refresh token cleanup task cancelled")

    logger.info("Shutting down AI Debate System...")


app = FastAPI(
    title="Lets-Debate",
    description="Multi-agent AI debate platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin"],
)

# Include API routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])
app.include_router(debates.router, prefix="/api/v1/debates", tags=["debates"])
app.include_router(websocket.router, prefix="/api/v1/ws", tags=["websocket"])


@app.get("/health", tags=["health"])
async def health_check(db: SessionDep):
    """Health endpoint with liveness/readiness checks for orchestrators."""
    checks: dict[str, dict[str, object]] = {}
    ready = True

    try:
        db.execute(text("SELECT 1"))
        checks["database"] = {"ok": True}
    except Exception as exc:
        ready = False
        checks["database"] = {"ok": False, "error": str(exc)}

    payload = {
        "status": "healthy" if ready else "degraded",
        "live": True,
        "ready": ready,
        "checks": checks,
    }
    status_code = 200 if ready else 503
    return JSONResponse(content=payload, status_code=status_code)
