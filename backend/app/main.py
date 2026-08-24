from contextlib import asynccontextmanager
from app.api.guardrail_router import router as guardrail_router
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.api.request_router import router as request_router
from app.api.review_router import router as review_router
from app.api.router import router
from app.api.analytics_router import router as analytics_router
from app.api.chat_router import router as chat_router
from app.api.budget_router import router as budget_router
from app.api.human_reviews_router import router as human_reviews_router

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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_origin_regex=r"chrome-extension://.*",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(human_reviews_router)
app.include_router(chat_router)
app.include_router(budget_router)
app.include_router(analytics_router)
app.include_router(websocket_router)
app.include_router(request_router)
app.include_router(review_router)
app.include_router(guardrail_router)

@app.get("/")
def read_root():
    return {"Hello": "World"}


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