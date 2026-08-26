"""Provider-independent token and cost estimates used for budget enforcement."""

from __future__ import annotations

import re

from app.guardrails.contracts import UsageEstimate


_TOKEN = re.compile(r"\w+|[^\w\s]", re.UNICODE)


# USD per 1,000 estimated tokens.
#
# These are development estimates for dashboard/budget calculations.
# Verify current provider pricing before using this for production billing.
MODEL_PRICING: dict[str, tuple[float, float]] = {
    "gpt-4o-mini": (0.00015, 0.00060),
    "gpt-4o": (0.00300, 0.01200),

    # Used when the request specifies model="auto".
    # Currently using the gpt-4o-mini estimate as the development fallback.
    "auto": (0.00015, 0.00060),
}


DEFAULT_MODEL = "gpt-4o-mini"


def _get_model_pricing(model: str) -> tuple[float, float]:
    """Return input/output pricing for a model.

    Unknown models fall back to the configured development default
    instead of raising a KeyError.
    """
    return MODEL_PRICING.get(model, MODEL_PRICING[DEFAULT_MODEL])


def estimate_cost(
    *,
    prompt_tokens: int,
    completion_tokens: int,
    model: str,
) -> float:
    """Estimate request cost in USD."""
    input_rate, output_rate = _get_model_pricing(model)

    return round(
        (
            prompt_tokens * input_rate
            + completion_tokens * output_rate
        )
        / 1_000,
        8,
    )


def estimate_request_cost(
    *,
    optimized_prompt_tokens: int,
    max_completion_tokens: int,
    model: str,
) -> float:
    """Estimate the maximum expected cost of a request."""
    return estimate_cost(
        prompt_tokens=optimized_prompt_tokens,
        completion_tokens=max_completion_tokens,
        model=model,
    )


def estimate_tokens(content: str) -> int:
    """Return a stable local approximation of token count."""
    if not content:
        return 0

    return len(_TOKEN.findall(content))


def estimate_usage(
    prompt: str,
    completion: str,
    model: str,
    *,
    original_prompt: str | None = None,
) -> UsageEstimate:
    """Estimate actual usage and optional prompt-optimization savings."""

    prompt_tokens = estimate_tokens(prompt)
    completion_tokens = estimate_tokens(completion)

    input_rate, _output_rate = _get_model_pricing(model)

    cost = estimate_cost(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        model=model,
    )

    original_prompt_tokens = (
        estimate_tokens(original_prompt)
        if original_prompt is not None
        else prompt_tokens
    )

    optimized_prompt_tokens = prompt_tokens

    tokens_saved = max(
        0,
        original_prompt_tokens - optimized_prompt_tokens,
    )

    savings_usd = tokens_saved * input_rate / 1_000

    return UsageEstimate(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost_usd=round(cost, 8),
        original_prompt_tokens=original_prompt_tokens,
        optimized_prompt_tokens=optimized_prompt_tokens,
        tokens_saved=tokens_saved,
        savings_usd=round(savings_usd, 8),
    )