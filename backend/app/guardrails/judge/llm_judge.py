"""Transparent fallback judge until an approved model provider is connected."""

from __future__ import annotations

from app.guardrails.contracts import CheckResult


_MAX_REVIEW_LENGTH = 4_000


def judge_response(response: str, context: str | None = None) -> CheckResult:
    """Return a manual-review signal without claiming semantic model assessment."""
    response_length = len(response.strip())
    metadata = {
        "mode": "fallback",
        "status": "manual_review",
        "provider": None,
        "response_length": response_length,
    }

    if not context or not context.strip():
        return CheckResult(
            name="judge",
            risk_score=0.55,
            reasons=["no_semantic_judge_available"],
            metadata={**metadata, "reason": "no_context_available"},
        )

    if response_length > _MAX_REVIEW_LENGTH:
        return CheckResult(
            name="judge",
            risk_score=0.55,
            reasons=["response_requires_manual_grounding_review"],
            metadata=metadata,
        )

    return CheckResult(
        name="judge",
        risk_score=0.40,
        reasons=["semantic_judge_not_configured"],
        metadata=metadata,
    )
