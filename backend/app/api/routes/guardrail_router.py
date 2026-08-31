"""Guardrail endpoints used by the ControlPlane browser extension."""

from __future__ import annotations

import time
from dataclasses import replace
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_principal
from app.core.database import get_db
from app.guardrails.pipeline import evaluate_input, evaluate_output
from app.models.api_key import ApiKey
from app.models.common import SecurityPolicy, Verdict
from app.services.audit_service import audit_service
from app.services.notification_service import notification_service
from app.services.review_service import review_service


router = APIRouter(
    prefix="/guardrails",
    tags=["guardrails"],
)


class InputGuardrailRequest(BaseModel):
    prompt: str = Field(min_length=1)
    model: str = "auto"


class InputGuardrailResponse(BaseModel):
    verdict: str
    content: str
    model_used: str
    risk_score: float
    reasons: list[str]
    corrections_applied: list[str]

    original_tokens: int
    optimized_tokens: int
    tokens_saved: int

    estimated_cost_usd: float
    savings_usd: float

    optimized_content: str | None = None
    review_id: UUID | None = None


class OutputGuardrailRequest(BaseModel):
    prompt: str = Field(default="")
    response: str = Field(min_length=1)
    model: str = "auto"


class OutputGuardrailResponse(BaseModel):
    verdict: str
    content: str
    model_used: str
    risk_score: float
    reasons: list[str]
    corrections_applied: list[str]
    review_id: UUID | None = None


class ReviewStatusResponse(BaseModel):
    resolved: bool
    final_response: str | None = None


@router.post(
    "/input",
    response_model=InputGuardrailResponse,
)
async def check_input(
    request: InputGuardrailRequest,
    db: AsyncSession = Depends(get_db),
    principal: ApiKey = Depends(get_current_principal),
) -> InputGuardrailResponse:

    started_at = time.perf_counter()

    result = await evaluate_input(
        prompt=request.prompt,
        requested_model=request.model,
        policy=principal.security_policy,
    )

    if result.verdict is Verdict.REVIEW:
        approved_final = await review_service.get_approved_prompt_response(
            db=db,
            prompt=request.prompt,
        )
        if approved_final is not None:
            # Use what the reviewer actually approved/edited — NOT the raw
            # original prompt. Previously this substituted request.prompt
            # itself, which meant an approved review sent the unmodified
            # sensitive content through verbatim, defeating the point of
            # having it reviewed at all.
            result = replace(
                result,
                verdict=Verdict.PASS,
                content=approved_final,
                proposed_content=None,
            )

    log = await audit_service.record_request(
        db=db,
        principal_id=principal.principal_id,
        principal_type=principal.principal_type,
        prompt=request.prompt,
        context=None,
        response_raw="",
        result=result,
        latency_ms=int((time.perf_counter() - started_at) * 1000),
        chatbot_category=principal.chatbot_category,
    )

    review_id = None
    if result.verdict is Verdict.REVIEW and result.proposed_content:
        review = await review_service.create_review(
            db=db,
            request_log_id=log.id,
            prompt=request.prompt,
            proposed_response=result.proposed_content,
            result=result,
        )
        review_id = review.id
        await notification_service.notify_review(
            review_id=str(review.id),
            principal_id=principal.principal_id,
            reason="; ".join(result.reasons),
            risk_score=result.risk_score,
        )

    await db.commit()

    usage = result.usage

    # `result.content` is the enforced/sanitized version (PII already
    # redacted for MASK verdicts, optimized for others). It must always be
    # what we hand back to the extension — echoing the raw request prompt
    # here would defeat masking entirely.
    optimized_content = None

    if result.verdict.value == "mask":
        # Always expose the redacted text for MASK verdicts, regardless of
        # whether redaction also happened to save tokens.
        optimized_content = result.content
    elif (
        result.verdict.value not in {"block", "review"}
        and result.usage.tokens_saved > 0
    ):
        optimized_content = result.content

    return InputGuardrailResponse(
        verdict=result.verdict.value,
        content=result.content,
        model_used=result.model_used,
        risk_score=result.risk_score,
        reasons=result.reasons,
        corrections_applied=result.corrections_applied,
        original_tokens=usage.original_prompt_tokens,
        optimized_tokens=usage.optimized_prompt_tokens,
        tokens_saved=usage.tokens_saved,
        estimated_cost_usd=usage.cost_usd,
        savings_usd=usage.savings_usd,
        optimized_content=optimized_content,
        review_id=review_id,
    )


@router.post(
    "/output",
    response_model=OutputGuardrailResponse,
)
async def check_output(
    request: OutputGuardrailRequest,
    db: AsyncSession = Depends(get_db),
    principal: ApiKey = Depends(get_current_principal),
) -> OutputGuardrailResponse:

    started_at = time.perf_counter()

    result = await evaluate_output(
        prompt=request.prompt,
        response=request.response,
        requested_model=request.model,
        policy=principal.security_policy,
    )

    if result.verdict is Verdict.REVIEW:
        approved_final = await review_service.get_approved_response(
            db=db,
            response=request.response,
        )
        if approved_final is not None:
            # This exact response was already reviewed and resolved before
            # (most commonly: the user refreshed the page, which re-renders
            # every historical message and re-triggers a fresh output check
            # on each one). Without this, every refresh would create a new
            # review item for content that's already been approved.
            result = replace(
                result,
                verdict=Verdict.PASS,
                content=approved_final,
                proposed_content=None,
            )

    log = await audit_service.record_request(
        db=db,
        principal_id=principal.principal_id,
        principal_type=principal.principal_type,
        prompt=request.prompt,
        context=None,
        response_raw=request.response,
        result=result,
        latency_ms=int((time.perf_counter() - started_at) * 1000),
        chatbot_category=principal.chatbot_category,
    )

    review_id = None
    if result.verdict is Verdict.REVIEW:
        review = await review_service.create_review(
            db=db,
            request_log_id=log.id,
            prompt=request.prompt,
            proposed_response=request.response,
            result=result,
        )
        review_id = review.id

    await db.commit()

    return OutputGuardrailResponse(
        verdict=result.verdict.value,
        content=result.content,
        model_used=result.model_used,
        risk_score=result.risk_score,
        reasons=result.reasons,
        corrections_applied=result.corrections_applied,
        review_id=review_id,
    )


@router.get(
    "/reviews/{review_id}",
    response_model=ReviewStatusResponse,
)
async def get_review_status(
    review_id: UUID,
    db: AsyncSession = Depends(get_db),
    principal: ApiKey = Depends(get_current_principal),
) -> ReviewStatusResponse:
    review = await review_service.get_review(db=db, review_id=review_id)
    return ReviewStatusResponse(
        resolved=review.resolved,
        final_response=review.final_response,
    )