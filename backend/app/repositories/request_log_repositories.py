"""Async persistence and analytics queries for request logs."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.common import ChatbotCategory, PrincipalType, Verdict
from app.models.request_log import RequestLog


async def create_request_log(db: AsyncSession, *, principal_id: str, principal_type: PrincipalType, prompt: str, response_raw: str, response_final: str, verdict: Verdict, model_used: str, latency_ms: int, chatbot_category: ChatbotCategory | None = None, context: str | None = None, corrections_applied: list[str] | None = None, flagged_reasons: list[str] | None = None, risk_score: float = 0.0, prompt_tokens: int = 0, completion_tokens: int = 0, cost_usd: float = 0.0, original_prompt_tokens: int = 0, optimized_prompt_tokens: int = 0, tokens_saved: int = 0, savings_usd: float = 0.0, cache_hit: bool = False) -> RequestLog:
    log = RequestLog(
        principal_id=principal_id, principal_type=principal_type, chatbot_category=chatbot_category,
        prompt=prompt, context=context, response_raw=response_raw, response_final=response_final,
        verdict=verdict, corrections_applied=corrections_applied or [], flagged_reasons=flagged_reasons or [],
        risk_score=risk_score, model_used=model_used, latency_ms=latency_ms, prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens, cost_usd=cost_usd, original_prompt_tokens=original_prompt_tokens,
        optimized_prompt_tokens=optimized_prompt_tokens, tokens_saved=tokens_saved, savings_usd=savings_usd,
        cache_hit=cache_hit,
    )
    db.add(log)
    await db.flush()
    return log


async def get_by_id(db: AsyncSession, request_id: UUID) -> RequestLog | None:
    result = await db.execute(select(RequestLog).where(RequestLog.id == request_id))
    return result.scalar_one_or_none()


async def list_requests(db: AsyncSession, *, limit: int = 50, cursor: datetime | None = None, verdict: Verdict | None = None, principal_id: str | None = None) -> list[RequestLog]:
    query = select(RequestLog).order_by(RequestLog.created_at.desc()).limit(max(1, min(limit, 500)))
    if cursor is not None:
        query = query.where(RequestLog.created_at < cursor)
    if verdict is not None:
        query = query.where(RequestLog.verdict == verdict)
    if principal_id is not None:
        query = query.where(RequestLog.principal_id == principal_id)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_analytics_summary(db: AsyncSession, principal_id: str | None = None) -> dict[str, float | int]:
    conditions = [RequestLog.principal_id == principal_id] if principal_id else []
    query = select(
        func.count(RequestLog.id).label("total"),
        func.coalesce(func.avg(RequestLog.latency_ms), 0.0).label("latency"),
        func.coalesce(func.sum(RequestLog.cost_usd), 0.0).label("cost"),
        func.coalesce(func.sum(RequestLog.savings_usd), 0.0).label("savings"),
        func.coalesce(func.sum(RequestLog.tokens_saved), 0).label("tokens"),
        func.coalesce(func.sum(case((RequestLog.verdict == Verdict.BLOCK, 1), else_=0)), 0).label("blocked"),
        func.coalesce(func.sum(case((RequestLog.verdict == Verdict.REVIEW, 1), else_=0)), 0).label("reviews"),
        func.coalesce(func.sum(case((RequestLog.cache_hit.is_(True), 1), else_=0)), 0).label("hits"),
    ).where(*conditions)
    row = (await db.execute(query)).one()
    total = int(row.total or 0)
    return {
        "total_requests": total, "blocked_requests": int(row.blocked or 0), "review_requests": int(row.reviews or 0),
        "block_rate": (row.blocked or 0) / total if total else 0.0, "avg_latency_ms": float(row.latency or 0.0),
        "total_cost_usd": float(row.cost or 0.0), "cost_saved_usd": float(row.savings or 0.0),
        "cost_saved_by_routing_usd": 0.0, "tokens_saved": int(row.tokens or 0), "cache_hits": int(row.hits or 0),
        "cache_hit_rate": (row.hits or 0) / total if total else 0.0,
    }


class RequestLogRepository:
    async def list_recent(self, db: AsyncSession, principal_id: str | None = None, limit: int = 100) -> list[RequestLog]:
        return await list_requests(db, principal_id=principal_id, limit=limit)

    async def summary(self, db: AsyncSession, principal_id: str | None = None) -> dict[str, float | int]:
        return await get_analytics_summary(db, principal_id)


request_log_repository = RequestLogRepository()
