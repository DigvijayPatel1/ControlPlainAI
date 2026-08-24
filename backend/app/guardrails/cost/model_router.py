"""Deterministic model routing for the OpenAI provider."""
from __future__ import annotations

from app.guardrails.cost.token_tracker import estimate_tokens

SMALL_MODEL = "gpt-4o-mini"
LARGE_MODEL = "gpt-4o"


def select_model(requested_model: str, prompt: str, *, needs_reasoning: bool = False) -> str:
    """Select a provider model while retaining a future routing interface."""
    if requested_model and requested_model != "auto":
        return requested_model
    if needs_reasoning or estimate_tokens(prompt) > 500:
        return LARGE_MODEL
    return SMALL_MODEL
