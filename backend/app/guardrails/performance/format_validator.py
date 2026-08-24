"""Deterministic output format validation."""

from __future__ import annotations

import json
import re

from app.guardrails.contracts import CheckResult

SUPPORTED_FORMATS = frozenset({"text", "json", "email", "number", "non_empty"})


def validate_format(response: str, expected_format: str | None = None) -> CheckResult:
    """Validate a response as text, JSON, or with no format requirement."""
    content = response
    empty = not content or not content.strip()
    normalized_format = expected_format.strip().casefold() if expected_format else None

    if normalized_format is None:
        return CheckResult(
            name="format",
            risk_score=0.70 if empty else 0.0,
            reasons=["empty_response"] if empty else [],
            metadata={"expected_format": None, "valid": not empty},
        )

    if normalized_format not in SUPPORTED_FORMATS:
        return CheckResult(
            name="format",
            risk_score=0.70,
            reasons=["unsupported_expected_format"],
            metadata={"expected_format": normalized_format, "supported_formats": sorted(SUPPORTED_FORMATS), "valid": False},
        )

    if empty:
        return CheckResult(
            name="format",
            risk_score=0.70,
            reasons=["empty_response"],
            metadata={"expected_format": normalized_format, "valid": False},
        )

    if normalized_format in {"text", "non_empty"}:
        return CheckResult(
            name="format",
            metadata={"expected_format": "text", "valid": True},
        )

    if normalized_format == "email":
        valid = re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", content.strip()) is not None
        return CheckResult(
            name="format",
            risk_score=0.0 if valid else 0.65,
            reasons=[] if valid else ["invalid_email_format"],
            metadata={"expected_format": "email", "valid": valid},
        )

    if normalized_format == "number":
        try:
            float(content.strip())
            valid = True
        except ValueError:
            valid = False
        return CheckResult(
            name="format",
            risk_score=0.0 if valid else 0.65,
            reasons=[] if valid else ["invalid_number_format"],
            metadata={"expected_format": "number", "valid": valid},
        )

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return CheckResult(
            name="format",
            risk_score=0.70,
            reasons=["invalid_json_response"],
            metadata={"expected_format": "json", "valid": False},
        )

    return CheckResult(
        name="format",
        metadata={
            "expected_format": "json",
            "valid": True,
            "json_type": type(parsed).__name__,
        },
    )
