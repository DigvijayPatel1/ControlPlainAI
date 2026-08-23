from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.common import ChatbotCategory, PrincipalType, Verdict
from app.models.request_log import RequestLog


#----------------------------------------------------------
# RequestLog repository functions
#----------------------------------------------------------

async def create_request_log(
    db: AsyncSession,
    *,
    # Identity
    principal_id: str,
    principal_type: PrincipalType,
    chatbot_category: ChatbotCategory | None = None,
    
    # Payload
    prompt: str,
    response_raw: str,
    response_final: str,
    context: str | None = None,
    
    # Guardrails
    verdict: Verdict,
    corrections_applied: list[str] | None = None,
    flagged_reasons: list[str] | None = None,
    risk_score: float = 0.0,
    
    # Telemetry
    model_used: str,
    latency_ms: int,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    cost_usd: float = 0.0,
    cache_hit: bool = False,
) -> RequestLog:
    
    log = RequestLog(
        principal_id=principal_id,
        principal_type=principal_type,
        chatbot_category=chatbot_category,
        prompt=prompt,
        context=context,
        response_raw=response_raw,
        response_final=response_final,
        verdict=verdict,
        corrections_applied=corrections_applied or [],
        flagged_reasons=flagged_reasons or [],
        risk_score=risk_score,
        model_used=model_used,
        latency_ms=latency_ms,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost_usd=cost_usd,
        cache_hit=cache_hit,
    )
    
    db.add(log)
    await db.flush()      # Populates log.id and log.created_at before returning
    await db.refresh(log)
    
    return log


#----------------------------------------------------------
# RequestLog repository functions
#----------------------------------------------------------

async def get_by_id(
    db: AsyncSession, 
    request_id: UUID
) -> RequestLog | None:
    
    stmt = select(RequestLog).where(RequestLog.id == request_id)
    result = await db.execute(stmt)
    
    return result.scalar_one_or_none()


#----------------------------------------------------------
# RequestLog repository functions
#----------------------------------------------------------

async def list_requests(
    db: AsyncSession,
    *,
    limit: int = 50,
    cursor: datetime | None = None,  # Pass the created_at of the last row seen
    verdict: Verdict | None = None,
    principal_id: str | None = None,
) -> list[RequestLog]:
    
    stmt = select(RequestLog).order_by(RequestLog.created_at.desc()).limit(limit)

    if cursor is not None:
        stmt = stmt.where(RequestLog.created_at < cursor)
        
    if verdict is not None:
        stmt = stmt.where(RequestLog.verdict == verdict)
        
    if principal_id is not None:
        stmt = stmt.where(RequestLog.principal_id == principal_id)

    result = await db.execute(stmt)
    
    return list(result.scalars().all())

#----------------------------------------------------------
# RequestLog repository functions
#----------------------------------------------------------

async def get_analytics_summary(
    db: AsyncSession
) -> dict[str, float | int]:
    """Single aggregate query for the Security Centre dashboard summary."""
    
    stmt = select(
        func.count(RequestLog.id).label("total_requests"),
        func.coalesce(func.avg(RequestLog.latency_ms), 0.0).label("avg_latency_ms"),
        func.coalesce(func.sum(RequestLog.cost_usd), 0.0).label("total_cost_usd"),
        func.coalesce(
            func.sum(case((RequestLog.verdict == Verdict.BLOCK, 1), else_=0)), 0
        ).label("blocked_count"),
        func.coalesce(
            func.sum(case((RequestLog.cache_hit.is_(True), 1), else_=0)), 0
        ).label("cache_hits"),
    )
    
    row = (await db.execute(stmt)).one()

    # Avoid divide-by-zero when the table is completely empty
    total = row.total_requests or 1  
    
    return {
        "total_requests": int(row.total_requests),
        "block_rate": float(row.blocked_count / total),
        "avg_latency_ms": float(row.avg_latency_ms),
        "total_cost_usd": float(row.total_cost_usd),
        "cache_hit_rate": float(row.cache_hits / total),
    }