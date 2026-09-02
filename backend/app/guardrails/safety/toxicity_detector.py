"""Small deterministic toxicity detector for the cheap first-pass guardrail."""
from __future__ import annotations

import re

from app.guardrails.contracts import CheckResult

_HIGH_RISK_TERMS = frozenset({"kill yourself", "go die", "subhuman", "exterminate"})
_ABUSE_TERMS = frozenset({"worthless", "idiot", "moron", "scumbag", "pathetic"})
_THREAT_PATTERN = re.compile(
    r"\b(?:i(?:'ll| will)|we(?:'ll| will)|you(?:'re going to|will))\s+"
    r"(?:kill|hurt|attack|shoot|stab)\b",
    re.IGNORECASE,
)


def check_toxicity(content: str) -> CheckResult:
    """Detect possible toxicity; policy and final enforcement are handled elsewhere."""
    if not content or not content.strip():
        return CheckResult("toxicity")

    lowered = content.casefold()
    high_risk_matches = sorted(term for term in _HIGH_RISK_TERMS if term in lowered)
    abuse_matches = sorted(term for term in _ABUSE_TERMS if term in lowered)
    has_threat = bool(_THREAT_PATTERN.search(content))

    reasons = [f"toxic_content:{term}" for term in high_risk_matches]
    reasons.extend(f"abusive_content:{term}" for term in abuse_matches)
    if has_threat:
        reasons.append("credible_threat")

    if has_threat:
        score = 1.0
    elif high_risk_matches:
        score = 0.90
    elif abuse_matches:
        score = 0.65
    else:
        score = 0.0

    return CheckResult("toxicity", score, reasons)
