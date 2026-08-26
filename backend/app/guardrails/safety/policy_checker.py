"""Deterministic policy detector; the decision engine owns final enforcement."""
from __future__ import annotations

import re

from app.guardrails.contracts import CheckResult

_HIGH_RISK_PATTERNS: dict[str, re.Pattern[str]] = {
    "credential_exfiltration": re.compile(
        r"\b(?:steal|extract|reveal|show|dump|expose|retrieve)\b.{0,60}"
        r"\b(?:password|api[ _-]?key|secret|access[ _-]?token|auth[ _-]?token|private[ _-]?key|credential)\b",
        re.IGNORECASE,
    ),
    "prompt_injection": re.compile(
        r"\b(?:ignore|bypass|override|disregard|forget)\b.{0,60}"
        r"\b(?:previous|prior|system|developer|safety|security|instructions?|rules?|policies?)\b",
        re.IGNORECASE,
    ),
    "system_prompt_extraction": re.compile(
        r"\b(?:reveal|show|print|output|tell me|give me)\b.{0,60}"
        r"\b(?:system prompt|system message|developer prompt|hidden instructions?|hidden prompt)\b",
        re.IGNORECASE,
    ),
    "secret_exfiltration": re.compile(
        r"\b(?:show|print|dump|read|reveal|extract)\b.{0,60}"
        r"\b(?:\.env|environment variables?|environment secrets?|secret files?)\b",
        re.IGNORECASE,
    ),
    "violent_wrongdoing": re.compile(
        r"\b(?:build|make|assemble|construct|create)\b.{0,50}\b(?:bomb|explosive|weapon)\b",
        re.IGNORECASE,
    ),
    "malicious_credential_theft": re.compile(
        r"\b(?:steal|harvest|capture|exfiltrate)\b.{0,60}"
        r"\b(?:passwords?|credentials?|cookies?|session tokens?|auth tokens?)\b",
        re.IGNORECASE,
    ),
}

_REVIEW_PATTERNS: dict[str, re.Pattern[str]] = {
    "hidden_information_request": re.compile(
        r"\b(?:show|reveal|tell me|give me)\b.{0,50}\b(?:hidden|internal|private|secret)\b"
        r".{0,50}\b(?:instructions?|configuration|settings?|context)\b",
        re.IGNORECASE,
    ),
}


def check_policy(content: str) -> CheckResult:
    """Detect high-risk and review-worthy policy signals without modifying text."""
    if not content or not content.strip():
        return CheckResult("policy", metadata={"violations": [], "review_flags": [], "high_risk": False})

    violations = [name for name, pattern in _HIGH_RISK_PATTERNS.items() if pattern.search(content)]
    review_flags = [name for name, pattern in _REVIEW_PATTERNS.items() if pattern.search(content)]
    risk_score = 1.0 if violations else 0.70 if review_flags else 0.0
    reasons = [f"policy_violation:{name}" for name in violations]
    reasons.extend(f"policy_review:{name}" for name in review_flags)
    return CheckResult(
        name="policy",
        risk_score=risk_score,
        reasons=reasons,
        metadata={"violations": violations, "review_flags": review_flags, "high_risk": bool(violations)},
    )
