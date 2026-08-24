"""Deterministic bias detection; enforcement remains in the decision engine."""
from __future__ import annotations

import re

from app.guardrails.contracts import CheckResult
from app.guardrails.schemas.bias import BiasDetection, BiasResult

_GROUPS = (
    r"women|woman|men|man|female|male|girls?|boys?|"
    r"black people|white people|black|white|asian people|asian|"
    r"muslims?|christians?|jews?|hindus?|sikhs?|"
    r"elderly people|elderly|old people|young people|young|seniors?|"
    r"disabled people|disabled|people with disabilities|"
    r"immigrants?|foreigners?|refugees?|"
    r"gay people|gay|lesbians?|bisexual people|bisexual|transgender people|transgender"
)
_HARMFUL_TRAITS = r"stupid|lazy|inferior|unintelligent|incompetent|dangerous|violent|untrustworthy|dishonest|criminal|incapable|weak"

_PATTERNS: tuple[tuple[str, re.Pattern[str], float, str], ...] = (
    ("harmful_generalisation", re.compile(rf"\b(?:all|every|most)\s+(?:{_GROUPS})\b.{{0,60}}\b(?:are|is|always|never|can't|cannot)\b.{{0,80}}\b(?:{_HARMFUL_TRAITS})\b", re.IGNORECASE), 0.90, "high"),
    ("group_exclusion", re.compile(rf"\b(?:don't hire|do not hire|shouldn't hire|should not hire|reject|exclude|ban|deny|fire|do not allow|don't allow|keep out)\b.{{0,80}}\b(?:{_GROUPS})\b", re.IGNORECASE), 0.95, "high"),
    ("group_inferiority", re.compile(rf"\b(?:{_GROUPS})\b.{{0,60}}\b(?:are|is)\b.{{0,50}}\b(?:inferior|stupid|lazy|incapable|incompetent|less intelligent|not good at|bad at)\b", re.IGNORECASE), 0.92, "high"),
    ("negative_stereotype", re.compile(rf"\b(?:{_GROUPS})\b.{{0,40}}\b(?:tend to|usually|typically|often|generally)\b.{{0,50}}\b(?:lazy|violent|dangerous|untrustworthy|dishonest|emotional|weak|incompetent)\b", re.IGNORECASE), 0.82, "medium"),
)
_UNCERTAIN_PATTERN = re.compile(rf"\b(?:hire|reject|promote|fire|exclude|approve|deny)\b.{{0,80}}\b(?:{_GROUPS})\b", re.IGNORECASE)
_REASONS = {
    "harmful_generalisation": "Potential harmful generalisation about a protected group.",
    "group_exclusion": "Potential discriminatory exclusion or targeting of a protected group.",
    "group_inferiority": "Potential claim that a protected group is inferior or incapable.",
    "negative_stereotype": "Potential negative stereotype associated with a protected group.",
}


class BiasDetector:
    """Detects bias signals only; it never modifies text or selects a verdict."""

    name = "bias"
    stage = "pre"

    def detect(self, text: str) -> BiasResult:
        if not text or not text.strip():
            return BiasResult(passed=True, detections=[], uncertain=False)
        detections = self._remove_overlaps([
            BiasDetection(category=category, severity=severity, score=score, reason=_REASONS[category], start=match.start(), end=match.end())
            for category, pattern, score, severity in _PATTERNS
            for match in pattern.finditer(text)
        ])
        uncertain = not detections and bool(_UNCERTAIN_PATTERN.search(text))
        return BiasResult(passed=not detections and not uncertain, detections=detections, uncertain=uncertain)

    @staticmethod
    def _remove_overlaps(detections: list[BiasDetection]) -> list[BiasDetection]:
        ordered = sorted(detections, key=lambda item: (item.start, -(item.end - item.start), -item.score))
        accepted: list[BiasDetection] = []
        for current in ordered:
            if not any(current.start < existing.end and current.end > existing.start for existing in accepted):
                accepted.append(current)
        return accepted


_detector = BiasDetector()


def check_bias(content: str) -> CheckResult:
    """Pipeline adapter that exposes detection metadata without raw sensitive text."""
    result = _detector.detect(content)
    risk_score = max((item.score for item in result.detections), default=0.45 if result.uncertain else 0.0)
    reasons = [item.reason for item in result.detections]
    if result.uncertain:
        reasons.append("Potential protected-group decision requires contextual review.")
    return CheckResult("bias", risk_score, reasons, metadata={"detections": result.detections, "uncertain": result.uncertain})
