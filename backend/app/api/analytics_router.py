"""Authenticated analytics endpoints for the dashboard."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_principal
from app.core.database import get_db
from app.models.api_key import ApiKey
from app.repositories.request_log_repositories import request_log_repository
from app.schemas.request_log import AnalyticsSummary, RequestLogEntry

router = APIRouter(prefix="/v1/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummary)
async def analytics_summary(
    db: AsyncSession = Depends(get_db),
    principal: ApiKey = Depends(get_current_principal),
) -> AnalyticsSummary:
    data = await request_log_repository.summary(db, principal.principal_id)
    return AnalyticsSummary(**data)


@router.get("/requests", response_model=list[RequestLogEntry])
async def analytics_requests(
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    principal: ApiKey = Depends(get_current_principal),
) -> list[RequestLogEntry]:
    rows = await request_log_repository.list_recent(db, principal.principal_id, limit)
    return [RequestLogEntry.model_validate(row) for row in rows]
