"""Persist guardrailed request telemetry without committing transactions."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.guardrails.contracts import PipelineResult
from app.models.common import ChatbotCategory, PrincipalType
from app.repositories.request_log_repositories import create_request_log


class AuditService:
    async def record_request(
        self,
        *,
        db: AsyncSession,
        principal_id: str,
        principal_type: PrincipalType,
        prompt: str,
        context: str | None,
        response_raw: str,
        result: PipelineResult,
        latency_ms: int,
        chatbot_category: ChatbotCategory | None = None,
    ):
        usage = result.usage
        return await create_request_log(
            db,
            principal_id=principal_id,
            principal_type=principal_type,
            chatbot_category=chatbot_category,
            prompt=prompt,
            context=context,
            response_raw=response_raw,
            response_final=result.content,
            verdict=result.verdict,
            corrections_applied=result.corrections_applied,
            flagged_reasons=result.reasons,
            risk_score=result.risk_score,
            model_used=result.model_used,
            latency_ms=latency_ms,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            cost_usd=usage.cost_usd,
            original_prompt_tokens=usage.original_prompt_tokens,
            optimized_prompt_tokens=usage.optimized_prompt_tokens,
            tokens_saved=usage.tokens_saved,
            savings_usd=usage.savings_usd,
            cache_hit=result.cache_hit,
        )


audit_service = AuditService()
