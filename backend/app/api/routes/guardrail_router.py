"""Guardrail endpoints used by the ControlPlane browser extension."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.deps import get_current_principal
from app.guardrails.pipeline import evaluate_input, evaluate_output
from app.models.api_key import ApiKey
from app.models.common import SecurityPolicy


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


class OutputGuardrailRequest(BaseModel):
    prompt: str = Field(min_length=1)
    response: str = Field(min_length=1)
    model: str = "auto"


class OutputGuardrailResponse(BaseModel):
    verdict: str
    content: str
    model_used: str
    risk_score: float
    reasons: list[str]
    corrections_applied: list[str]


@router.post(
    "/input",
    response_model=InputGuardrailResponse,
)
async def check_input(
    request: InputGuardrailRequest,
    principal: ApiKey = Depends(get_current_principal),
) -> InputGuardrailResponse:

    result = await evaluate_input(
        prompt=request.prompt,
        requested_model=request.model,
        policy=principal.security_policy,
    )

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
    )


@router.post(
    "/output",
    response_model=OutputGuardrailResponse,
)
async def check_output(
    request: OutputGuardrailRequest,
    principal: ApiKey = Depends(get_current_principal),
) -> OutputGuardrailResponse:

    result = await evaluate_output(
        prompt=request.prompt,
        response=request.response,
        requested_model=request.model,
        policy=principal.security_policy,
    )

    return OutputGuardrailResponse(
        verdict=result.verdict.value,
        content=result.content,
        model_used=result.model_used,
        risk_score=result.risk_score,
        reasons=result.reasons,
        corrections_applied=result.corrections_applied,
    )