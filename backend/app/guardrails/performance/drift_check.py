"""Low-cost lexical relevance check for supplied grounding context.

This check does not measure statistical model drift or prove factual correctness.
It provides a cheap signal when a response appears unrelated to its context.
"""

from __future__ import annotations

import re

from app.guardrails.contracts import CheckResult

_WORD = re.compile(r"[a-zA-Z][a-zA-Z0-9_-]{2,}")
_STOPWORDS = frozenset(
    {
        "the", "and", "for", "that", "with", "this", "from", "are", "was",
        "were", "you", "your", "have", "has", "had", "into", "about", "there",
        "their", "they", "them", "what", "when", "where", "which", "will",
        "would", "could", "should",
    }
)


def _terms(value: str) -> set[str]:
    return {
        word.casefold()
        for word in _WORD.findall(value)
        if word.casefold() not in _STOPWORDS
    }


def check_drift(response: str, context: str | None) -> CheckResult:
    """Check whether a response appears lexically unrelated to its context."""
    if not response or not response.strip():
        return CheckResult(
            name="drift",
            metadata={"checked": False, "reason": "empty_response"},
        )

    if not context or not context.strip():
        return CheckResult(
            name="drift",
            metadata={"checked": False, "reason": "no_context_available"},
        )

    response_terms = _terms(response)
    context_terms = _terms(context)
    if not response_terms:
        return CheckResult(
            name="drift",
            metadata={"checked": False, "reason": "no_response_terms"},
        )
    if not context_terms:
        return CheckResult(
            name="drift",
            metadata={"checked": False, "reason": "no_context_terms"},
        )

    shared_terms = response_terms & context_terms
    overlap = len(shared_terms) / len(response_terms)
    response_term_count = len(response_terms)
    base_metadata = {
        "checked": True,
        "overlap": round(overlap, 4),
        "response_terms": response_term_count,
        "context_terms": len(context_terms),
        "shared_terms": sorted(shared_terms),
    }

    if response_term_count < 8:
        return CheckResult(
            name="drift",
            metadata={**base_metadata, "status": "insufficient_length"},
        )

    if overlap < 0.08:
        return CheckResult(
            name="drift",
            risk_score=0.65,
            reasons=["response_off_grounding_context"],
            metadata={**base_metadata, "status": "possible_drift"},
        )

    return CheckResult(
        name="drift",
        metadata={**base_metadata, "status": "aligned"},
    )
