from app.guardrails.contracts import CheckResult
from app.guardrails.decision_engine import decide
from app.guardrails.performance.drift_check import check_drift
from app.guardrails.performance.format_validator import validate_format
from app.guardrails.performance.hallucination_check import (
    check_hallucination,
)
from app.models.common import SecurityPolicy, Verdict


def test_drift_with_matching_context():
    result = check_drift(
        "Python is a programming language used for software development.",
        "Python is a programming language used for software development.",
    )

    assert result.name == "drift"
    assert result.risk_score == 0.0


def test_drift_with_unrelated_response():
    result = check_drift(
        "The ocean contains many different species of marine animals and plants.",
        "Python is a programming language used for software development.",
    )

    assert result.risk_score > 0


def test_no_context_does_not_claim_drift():
    assert (
        check_drift(
            "Hello world.",
            None,
        ).risk_score
        == 0.0
    )


def test_hallucination_check_exists():
    result = check_hallucination(
        "Python is useful.",
        "Python is a programming language.",
    )

    assert result.name == "hallucination"


def test_no_grounding_context_does_not_force_review():
    result = check_hallucination(
        "Hello world.",
        None,
    )

    assert result.risk_score == 0.0
    assert result.metadata["status"] == "skipped"


def test_no_grounding_context_allows_normal_response():
    result = check_hallucination(
        "Hello world.",
        None,
    )

    verdict, risk, reasons = decide(
        [result],
        SecurityPolicy.MONITOR,
    )

    assert verdict is Verdict.PASS
    assert risk == 0.0
    assert reasons == []


def test_format_without_requirement():
    result = validate_format(
        response="Hello world.",
        expected_format=None,
    )

    assert result.risk_score == 0.0


def test_low_risk_passes():
    assert (
        decide(
            [CheckResult(name="toxicity")],
            SecurityPolicy.MONITOR,
        )[0]
        is Verdict.PASS
    )


def test_high_risk_blocks():
    verdict, risk, reasons = decide(
        [
            CheckResult(
                "hallucination",
                0.90,
                ["unsupported_claim"],
            )
        ]
    )

    assert verdict is Verdict.BLOCK
    assert risk == 0.90
    assert "unsupported_claim" in reasons


def test_medium_risk_requires_review():
    assert (
        decide(
            [CheckResult("drift", 0.50)],
            SecurityPolicy.MONITOR,
        )[0]
        is Verdict.REVIEW
    )

