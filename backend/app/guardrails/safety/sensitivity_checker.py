"""Detects disclosure of sensitive *content* — as opposed to policy_checker,
which detects jailbreak/exfiltration *phrasing*, and pii_detector, which only
catches structured formats (emails, SSNs, etc). This module is what catches
a user pasting confidential business text, health info, or financial
disclosures that don't match any regex but are still sensitive.

This is intentionally a keyword/pattern net, not a classifier — it will miss
paraphrased disclosures. It exists to close the specific, confirmed gap
where free-text sensitive content sailed through as a `pass` verdict.
"""
from __future__ import annotations

import re

from app.guardrails.contracts import CheckResult

_CONFIDENTIALITY_MARKERS: re.Pattern[str] = re.compile(
    r"\b(?:confidential|proprietary|trade secret|internal[- ]only|internal use only|"
    r"do not (?:share|distribute|forward)|not for distribution|under nda|"
    r"non[- ]disclosure|classified|restricted access|unreleased|embargoed)\b",
    re.IGNORECASE,
)

_FINANCIAL_DISCLOSURE: re.Pattern[str] = re.compile(
    r"\b(?:our|my|the company'?s|internal)\b.{0,40}"
    r"\b(?:revenue|salary|payroll|valuation|financials?|budget|profit margin)\b.{0,40}"
    r"(?:is|are|was|were|of)\b.{0,20}[\$\u20ac\u00a3]?\d",
    re.IGNORECASE,
)

_HEALTH_DISCLOSURE: re.Pattern[str] = re.compile(
    r"\b(?:i have|i was diagnosed with|my (?:patient|client) has)\b.{0,40}"
    r"\b(?:condition|diagnosis|disease|disorder|hiv|cancer|depression|anxiety)\b",
    re.IGNORECASE,
)

# Very light heuristic NER fallback for when spaCy isn't installed: two or
# more consecutive capitalized words not at the start of a sentence, which
# is a common shape for a person's full name in free text. Deliberately
# conservative — false negatives are fine here since this is a last-resort
# fallback, not the primary detection path (see pii_detector.py for the
# real NER integration).
_CAPITALIZED_NAME_HEURISTIC: re.Pattern[str] = re.compile(
    r"(?<!^)(?<![.!?]\s)\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\b"
)


def check_sensitivity(content: str) -> CheckResult:
    """Flags confidentiality markers and common sensitive-disclosure shapes.
    Runs independently of pii_detector so it still catches content that has
    no structured PII in it at all."""
    if not content or not content.strip():
        return CheckResult("sensitivity", metadata={"markers": []})

    markers: list[str] = []
    if _CONFIDENTIALITY_MARKERS.search(content):
        markers.append("confidentiality_marker")
    if _FINANCIAL_DISCLOSURE.search(content):
        markers.append("financial_disclosure")
    if _HEALTH_DISCLOSURE.search(content):
        markers.append("health_disclosure")

    if not markers:
        return CheckResult("sensitivity", metadata={"markers": []})

    # Any confidentiality marker is a hard stop; financial/health disclosure
    # shapes are review-worthy but not an automatic block, since they can be
    # legitimate (e.g. asking for help drafting a disclosure you're allowed
    # to make).
    risk_score = 1.0 if "confidentiality_marker" in markers else 0.70
    reasons = [f"sensitivity_{marker}" for marker in markers]
    return CheckResult(
        name="sensitivity",
        risk_score=risk_score,
        reasons=reasons,
        metadata={"markers": markers},
    )