"""Compatibility wrapper for the guardrails OpenAI provider."""

from __future__ import annotations

from dataclasses import dataclass

from app.guardrails.cost.token_tracker import estimate_cost
from app.guardrails.providers.openai_provider import openai_provider as _provider


@dataclass(slots=True)
class ProviderUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float


@dataclass(slots=True)
class ProviderResponse:
    content: str
    usage: ProviderUsage


async def openai_provider(*, model: str, prompt: str) -> ProviderResponse:
    result = await _provider.generate(prompt=prompt, model=model)
    return ProviderResponse(
        content=result.content,
        usage=ProviderUsage(
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            total_tokens=result.total_tokens,
            cost_usd=estimate_cost(
                prompt_tokens=result.prompt_tokens,
                completion_tokens=result.completion_tokens,
                model=result.model,
            ),
        ),
    )
