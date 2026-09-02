"""Combine guardrail findings into one enforcement verdict."""

from __future__ import annotations

from app.guardrails.contracts import CheckResult
from app.guardrails.schemas.pii import PIIDetection
from app.guardrails.safety.pii_policy import PIIAction, classify_pii
from app.models.common import SecurityPolicy, Verdict


def decide(
    findings: list[CheckResult],
    policy: SecurityPolicy = SecurityPolicy.MONITOR,
) -> tuple[Verdict, float, list[str]]:
    """Return the highest-priority enforcement action for all findings."""
    risk_score = max((finding.risk_score for finding in findings), default=0.0)
    reasons = [reason for finding in findings for reason in finding.reasons]

    has_policy_violation = any(
        finding.name == "policy" and finding.risk_score >= 1.0
        for finding in findings
    )
    pii_action = classify_pii(_extract_pii_detections(findings))
    bias_requires_review = any(
        finding.name == "bias" and finding.risk_score > 0.0
        for finding in findings
    )

    if has_policy_violation or pii_action is PIIAction.BLOCK or risk_score >= 0.90:
        return Verdict.BLOCK, risk_score, reasons

    if (
        pii_action is PIIAction.REVIEW
        or bias_requires_review
        or _has_performance_review_signal(findings)
        or risk_score >= 0.40
    ):
        return Verdict.REVIEW, risk_score, reasons

    if pii_action is PIIAction.MASK:
        if policy is SecurityPolicy.BLOCK:
            return Verdict.BLOCK, risk_score, reasons
        return Verdict.MASK, risk_score, reasons

    return Verdict.PASS, risk_score, reasons


def _extract_pii_detections(findings: list[CheckResult]) -> list[PIIDetection]:
    detections: list[PIIDetection] = []
    for finding in findings:
        if finding.name != "pii":
            continue
        detections.extend(
            detection
            for detection in finding.metadata.get("detections", [])
            if isinstance(detection, PIIDetection)
        )
    return detections


def _has_performance_review_signal(findings: list[CheckResult]) -> bool:
    for finding in findings:
        if finding.name == "hallucination" and finding.metadata.get("status") in {
            "unverified",
            "contradicted",
        }:
            return True
        if finding.name == "drift" and finding.metadata.get("status") == "possible_drift":
            return True
        if finding.name == "format" and finding.risk_score > 0.0:
            return True
    return False
