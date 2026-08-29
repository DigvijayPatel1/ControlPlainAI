"""ChatGPT-compatible guarded proxy endpoint."""

from __future__ import annotations

import time
import uuid
from dataclasses import replace

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import enforce_budget
from app.core.config import settings
from app.core.database import get_db
from app.guardrails.contracts import PipelineResult
from app.guardrails.cost.token_tracker import estimate_request_cost
from app.guardrails.pipeline import apply_provider_usage, evaluate_input, evaluate_output, get_cached_response
from app.llm.openai_provider import openai_provider
from app.models.api_key import ApiKey
from app.models.check_result import RequestCheck
from app.models.common import Verdict
from app.schemas.request_log import ChatCompletionRequest, ChatCompletionResponse, ChatMessage, UsageOut
from app.services.audit_service import audit_service
from app.services.budget_service import BudgetExceededError, BudgetNotFoundError, budget_service
from app.services.notification_service import notification_service
from app.services.review_service import review_service

router = APIRouter(prefix="/v1", tags=["chat"])


def _json_safe(value):
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    return value


def _messages_to_prompt(messages: list[ChatMessage]) -> str:
    return "\n".join(f"{message.role}: {message.content}" for message in messages)


def _to_response(request_id: uuid.UUID, result: PipelineResult) -> ChatCompletionResponse:
    usage = result.usage
    return ChatCompletionResponse(
        id=request_id,
        verdict=result.verdict,
        model_used=result.model_used,
        content=result.content,
        corrections_applied=result.corrections_applied,
        usage=UsageOut(
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            cost_usd=usage.cost_usd,
            original_prompt_tokens=usage.original_prompt_tokens,
            optimized_prompt_tokens=usage.optimized_prompt_tokens,
            tokens_saved=usage.tokens_saved,
            savings_usd=usage.savings_usd,
        ),
    )


async def _audit(db: AsyncSession, principal: ApiKey, original_prompt: str, context: str | None, raw_response: str, result: PipelineResult, latency_ms: int):
    log = await audit_service.record_request(
        db=db, principal_id=principal.principal_id, principal_type=principal.principal_type,
        prompt=original_prompt, context=context, response_raw=raw_response, result=result,
        latency_ms=latency_ms, chatbot_category=principal.chatbot_category,
    )
    for check in result.checks:
        metadata = _json_safe(check.metadata)
        db.add(RequestCheck(
            request_log_id=log.id, direction="output", check_name=check.name,
            risk_score=check.risk_score, reasons=check.reasons,
            corrections=check.corrections, metadata_json=metadata,
        ))
    await db.flush()
    await db.commit()
    return log


@router.post("/chat/completions", response_model=ChatCompletionResponse)
async def chat_completion(
    request: ChatCompletionRequest,
    db: AsyncSession = Depends(get_db),
    principal: ApiKey = Depends(enforce_budget),
) -> ChatCompletionResponse:
    started_at = time.perf_counter()
    if not request.messages:
        raise HTTPException(status_code=400, detail="messages cannot be empty.")
    if request.stream:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Streaming is not implemented yet.")

    original_prompt = _messages_to_prompt(request.messages)
    input_result = await evaluate_input(
        prompt=original_prompt, requested_model=request.model, policy=principal.security_policy,
    )
    if input_result.verdict in {Verdict.BLOCK, Verdict.REVIEW}:
        log = await _audit(db, principal, original_prompt, request.context, "", input_result, int((time.perf_counter() - started_at) * 1000))
        if input_result.verdict is Verdict.BLOCK:
            try:
                await budget_service.record_blocked_request(db=db, principal_id=principal.principal_id)
                await db.commit()
            except BudgetNotFoundError:
                pass
        elif input_result.proposed_content:
            review = await review_service.create_review(
                db=db, request_log_id=log.id, prompt=original_prompt,
                proposed_response=input_result.proposed_content, result=input_result,
            )
            await db.commit()
            await notification_service.notify_review(
                review_id=str(review.id), principal_id=principal.principal_id,
                reason="; ".join(input_result.reasons), risk_score=input_result.risk_score,
            )
        return _to_response(log.id, input_result)

    optimized_prompt = input_result.content
    model = input_result.model_used
    cached = await get_cached_response(
        prompt=optimized_prompt, context=request.context, model=model,
        expected_format=request.expected_format,
    )
    if cached is not None:
        result = await evaluate_output(
            prompt=optimized_prompt, original_prompt=original_prompt, response=cached,
            context=request.context, requested_model=model, policy=principal.security_policy,
            expected_format=request.expected_format, cache_hit=True, store_in_cache=False,
        )
        result.usage = replace(result.usage, cost_usd=0.0)
        log = await _audit(db, principal, original_prompt, request.context, cached, result, int((time.perf_counter() - started_at) * 1000))
        await db.commit()
        return _to_response(log.id, result)

    estimated_cost = estimate_request_cost(
        optimized_prompt_tokens=input_result.usage.optimized_prompt_tokens,
        max_completion_tokens=settings.MAX_COMPLETION_TOKENS,
        model=model,
    )
    try:
        await budget_service.enforce_budget(db=db, principal_id=principal.principal_id, estimated_cost_usd=estimated_cost)
    except BudgetNotFoundError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except BudgetExceededError:
        blocked = PipelineResult(
            verdict=Verdict.BLOCK, content="This request exceeds the configured budget.",
            risk_score=1.0, reasons=["budget_exceeded"], corrections_applied=[], checks=[],
            model_used=model, usage=input_result.usage,
        )
        log = await _audit(db, principal, original_prompt, request.context, "", blocked, int((time.perf_counter() - started_at) * 1000))
        await db.commit()
        return _to_response(log.id, blocked)

    try:
        provider_response = await openai_provider(model=model, prompt=optimized_prompt)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="LLM provider request failed.") from exc

    result = await evaluate_output(
        prompt=optimized_prompt, original_prompt=original_prompt, response=provider_response.content,
        context=request.context, requested_model=model, policy=principal.security_policy,
        expected_format=request.expected_format,
    )
    result = apply_provider_usage(
        result, prompt_tokens=provider_response.usage.prompt_tokens,
        completion_tokens=provider_response.usage.completion_tokens,
        cost_usd=provider_response.usage.cost_usd,
    )
    await budget_service.record_spend(db=db, principal_id=principal.principal_id, cost_usd=result.usage.cost_usd)
    log = await _audit(db, principal, original_prompt, request.context, provider_response.content, result, int((time.perf_counter() - started_at) * 1000))
    await db.commit()
    if result.verdict is Verdict.REVIEW:
        review = await review_service.create_review(
            db=db, request_log_id=log.id, prompt=original_prompt,
            proposed_response=result.proposed_content or provider_response.content, result=result,
        )
        await db.commit()
        await notification_service.notify_review(
            review_id=str(review.id), principal_id=principal.principal_id,
            reason="; ".join(result.reasons), risk_score=result.risk_score,
        )
    await notification_service.notify_request(
        principal_id=principal.principal_id, request_id=str(log.id), verdict=result.verdict.value,
        risk_score=result.risk_score, tokens_saved=result.usage.tokens_saved, savings_usd=result.usage.savings_usd,
    )
    return _to_response(log.id, result)
