
"""Low-cost grounding check for claims in generated responses."""

from __future__ import annotations

import re

from app.guardrails.contracts import CheckResult


# Numbers such as 1960, 3.14, 45%, and 25k.
_NUMBER_PATTERN = re.compile(
    r"\b(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?:%|[kKmMbB])?(?![A-Za-z0-9])"
)

# Deliberately conservative: this is not a full NLP claim parser.
_SIMPLE_CLAIM_PATTERN = re.compile(
    r"\b"
    r"([A-Za-z][A-Za-z0-9 ,.'-]{1,80}?)"
    r"\s+"
    r"(is|was|are|were|has|had)"
    r"\s+"
    r"([A-Za-z0-9][A-Za-z0-9 ,.'%$-]{1,100})"
    r"[.!?]",
    re.IGNORECASE,
)


def check_hallucination(response: str, context: str | None) -> CheckResult:
    """Classify simple response claims as supported, unverified, or contradicted."""

    if not response or not response.strip():
        return CheckResult(
            name="hallucination",
            metadata={
                "checked": False,
                "status": "unverified",
                "reason": "empty_response",
            },
        )

    if not context or not context.strip():
        # Missing grounding context means this check cannot run.
        #
        # It must NOT create a medium-risk finding because the decision
        # engine treats medium risk as REVIEW. Otherwise every ordinary
        # response without explicit grounding context would be sent to
        # human review.
        return CheckResult(
            name="hallucination",
            risk_score=0.0,
            reasons=[],
            metadata={
                "checked": False,
                "status": "skipped",
                "reason": "no_context_available",
            },
        )

    context_normalized = _normalize(context)
    claims = _extract_claims(response)

    supported_claims: list[str] = []
    unsupported_claims: list[str] = []
    contradicted_claims: list[str] = []

    for claim in claims:
        normalized_claim = _normalize(claim)

        if (
            normalized_claim in context_normalized
            or _claim_supported(claim, context_normalized)
        ):
            supported_claims.append(claim)

        elif _claim_contradicted(claim, context_normalized):
            contradicted_claims.append(claim)

        else:
            unsupported_claims.append(claim)

    response_numbers = set(_NUMBER_PATTERN.findall(response))
    context_numbers = set(_NUMBER_PATTERN.findall(context))

    unsupported_numbers = sorted(
        response_numbers - context_numbers
    )

    if contradicted_claims:
        status = "contradicted"
        risk = 0.90
        reasons = ["claims_contradict_context"]

    elif unsupported_claims:
        status = "unverified"
        risk = 0.55
        reasons = ["claims_not_supported_by_context"]

    elif len(unsupported_numbers) >= 2:
        status = "unverified"
        risk = 0.55
        reasons = ["unsupported_numeric_claims"]

    else:
        status = "supported"
        risk = 0.0
        reasons = []

    return CheckResult(
        name="hallucination",
        risk_score=risk,
        reasons=reasons,
        metadata={
            "checked": True,
            "status": status,
            "claims_checked": len(claims),
            "supported_claims": supported_claims,
            "unsupported_claims": unsupported_claims,
            "contradicted_claims": contradicted_claims,
            "unsupported_numbers": unsupported_numbers,
        },
    )


def _extract_claims(text: str) -> list[str]:
    return [
        match.group(0).strip()
        for match in _SIMPLE_CLAIM_PATTERN.finditer(text)
    ]


def _claim_supported(claim: str, context: str) -> bool:
    claim_numbers = set(_NUMBER_PATTERN.findall(claim))
    context_numbers = set(_NUMBER_PATTERN.findall(context))

    if claim_numbers and not claim_numbers.issubset(context_numbers):
        return False

    claim_tokens = _important_tokens(claim)

    if not claim_tokens:
        return False

    matched = sum(
        token in context
        for token in claim_tokens
    )

    return matched / len(claim_tokens) >= 0.75


def _claim_contradicted(claim: str, context: str) -> bool:
    claim_numbers = set(_NUMBER_PATTERN.findall(claim))

    if not claim_numbers:
        return False

    context_numbers = set(_NUMBER_PATTERN.findall(context))

    claim_tokens = _important_tokens(claim)
    context_tokens = _important_tokens(context)

    claim_words = claim_tokens - claim_numbers
    context_words = context_tokens - context_numbers

    overlap = len(claim_words & context_words) / max(
        len(claim_words),
        1,
    )

    return (
        overlap >= 0.75
        and not claim_numbers.issubset(context_numbers)
        and bool(context_numbers)
    )


def _normalize(text: str) -> str:
    return " ".join(
        text.casefold().split()
    )


def _important_tokens(text: str) -> set[str]:
    normalized = _normalize(text)

    tokens = _NUMBER_PATTERN.findall(normalized)

    tokens.extend(
        re.findall(
            r"\b[a-z]{3,}\b",
            normalized,
        )
    )

    stop_words = {
        "the",
        "and",
        "was",
        "were",
        "are",
        "has",
        "had",
        "with",
        "that",
        "this",
        "from",
        "into",
        "for",
        "its",
        "have",
        "been",
    }

    return {
        token
        for token in tokens
        if token not in stop_words
    }

