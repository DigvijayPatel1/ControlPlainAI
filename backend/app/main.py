from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.router import api_router

from app.core.config import settings
from app.core.logging import configure_logging
from app.websocket.review_socket import router as websocket_router
from app.core.database import Base, engine
from app.services.redis_service import redis_service

# Import models before development-only create_all.
from app.models.api_key import ApiKey  # noqa: F401
from app.models.budget import Budget  # noqa: F401
from app.models.check_result import RequestCheck  # noqa: F401
from app.models.request_log import RequestLog  # noqa: F401
from app.models.review_item import ReviewItem  # noqa: F401
from app.models.user import User  # noqa: F401

configure_logging(debug=settings.DEBUG)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if settings.APP_ENV == "development" and engine is not None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
    yield
    if engine is not None:
        await engine.dispose()


app = FastAPI(title="ControlPlaneAI", version="1.0.0", lifespan=lifespan)

# In development, allow any localhost/127.0.0.1 port (Vite auto-picks a free
# port, e.g. 5174, 5175, ... if 5173 is busy) plus the extension origin.
# In production, only the explicitly configured FRONTEND_ORIGIN is allowed.
if settings.APP_ENV == "development":
    _cors_origin_regex = r"chrome-extension://.*|http://(localhost|127\.0\.0\.1):\d+"
else:
    _cors_origin_regex = r"chrome-extension://.*"

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_origin_regex=_cors_origin_regex,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------
# API Routes
# -------------------------------
app.include_router(api_router)   


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "controlplane"}


@app.get("/health/database")
async def database_health() -> dict[str, str]:
    if engine is None:
        raise HTTPException(status_code=503, detail={"status": "error", "database": "driver_unavailable"})
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail={"status": "error", "database": "unavailable"}) from exc
    return {"status": "ok", "database": "postgresql"}


@app.get("/health/redis")
async def redis_health() -> dict[str, str]:
    if not await redis_service.health_check():
        raise HTTPException(status_code=503, detail={"status": "error", "redis": "unavailable"})
    return {"status": "ok", "redis": "available"}