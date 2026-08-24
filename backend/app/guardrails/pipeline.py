"""Direction-aware, deterministic guardrail orchestration for extension traffic."""

from __future__ import annotations

from dataclasses import replace

from app.guardrails.contracts import CheckResult, PipelineResult
from app.guardrails.cost.cache_manager import cache
from app.guardrails.cost.model_router import select_model
from app.guardrails.cost.prompt_optimizer import optimize_prompt
from app.guardrails.cost.token_tracker import estimate_cost, estimate_tokens, estimate_usage
from app.guardrails.decision_engine import decide
from app.guardrails.judge.llm_judge import judge_response
from app.guardrails.performance.drift_check import check_drift
from app.guardrails.performance.format_validator import validate_format
from app.guardrails.performance.hallucination_check import check_hallucination
from app.guardrails.safety.bias_detector import check_bias
from app.guardrails.safety.pii_detector import PIIDetector
from app.guardrails.safety.pii_redactor import redact_pii
from app.guardrails.safety.policy_checker import check_policy
from app.guardrails.safety.toxicity_detector import check_toxicity
from app.guardrails.schemas.pii import PIIResult
from app.models.common import SecurityPolicy, Verdict


BLOCKED_INPUT_MESSAGE = (
    "This message was blocked by the configured safety policy."
)

BLOCKED_OUTPUT_MESSAGE = (
    "This response was blocked by the configured safety policy."
)

REVIEW_MESSAGE = "This content is awaiting human review."

_pii_detector = PIIDetector()


def _pii_check(content: str) -> tuple[CheckResult, PIIResult]:
    """Run PII detection without storing detected values in the check result."""

    result = _pii_detector.detect(content)

    check = CheckResult(
        name="pii",
        risk_score=(
            min(1.0, 0.35 + 0.15 * result.count)
            if not result.passed
            else 0.0
        ),
        reasons=[
            f"pii_{item.entity_type.casefold()}_detected"
            for item in result.detections
        ],
        metadata={
            "detections": result.detections,
        },
    )

    return check, result


def _safety_checks(
    content: str,
) -> tuple[list[CheckResult], PIIResult]:

    pii_check, pii_result = _pii_check(content)

    return [
        pii_check,
        check_policy(content),
        check_toxicity(content),
        check_bias(content),
    ], pii_result


def _enforced_content(
    *,
    original: str,
    pii_result: PIIResult,
    verdict: Verdict,
    blocked_message: str,
) -> tuple[str, list[str], str | None]:

    if verdict is Verdict.BLOCK:
        return blocked_message, [], None

    if verdict is Verdict.REVIEW:
        return REVIEW_MESSAGE, [], original

    if verdict is Verdict.MASK:
        return (
            redact_pii(original, pii_result),
            ["pii_redacted"],
            None,
        )

    return original, [], None


def cache_key_for(
    *,
    prompt: str,
    context: str | None,
    model: str,
    expected_format: str | None,
) -> str:
    """Stable cache key for a route/proxy to check before an LLM call."""

    return cache.key_for(
        model,
        prompt,
        context,
        expected_format,
    )


def apply_provider_usage(
    result: PipelineResult,
    *,
    prompt_tokens: int,
    completion_tokens: int,
    cost_usd: float,
) -> PipelineResult:

    result.usage = replace(
        result.usage,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost_usd=cost_usd,
    )

    return result


async def get_cached_response(
    *,
    prompt: str,
    context: str | None,
    model: str,
    expected_format: str | None,
) -> str | None:

    """Return a previously guardrailed response before an expensive provider call."""

    key = cache_key_for(
        prompt=prompt,
        context=context,
        model=model,
        expected_format=expected_format,
    )

    return await cache.get(key)


async def evaluate_input(
    *,
    prompt: str,
    requested_model: str = "auto",
    policy: SecurityPolicy = SecurityPolicy.MONITOR,
) -> PipelineResult:
    """
    Check and safely optimize an incoming extension prompt.

    Flow:

        prompt
          ↓
        safety checks
          ↓
        policy decision
          ↓
        BLOCK / REVIEW / MASK / PASS
          ↓
        prompt optimization
          ↓
        token + cost estimation
    """

    # ---------------------------------------------------------
    # 1. Safety checks
    # ---------------------------------------------------------

    checks, pii_result = _safety_checks(prompt)

    # ---------------------------------------------------------
    # 2. Decide what to do with the input
    # ---------------------------------------------------------

    verdict, risk_score, reasons = decide(
        checks,
        policy,
    )

    content, corrections, proposed_content = _enforced_content(
        original=prompt,
        pii_result=pii_result,
        verdict=verdict,
        blocked_message=BLOCKED_INPUT_MESSAGE,
    )

    # ---------------------------------------------------------
    # 3. Select model
    # ---------------------------------------------------------

    model_used = select_model(
        requested_model,
        content,
    )

    # ---------------------------------------------------------
    # 4. BLOCK / REVIEW
    # ---------------------------------------------------------

    if verdict in {
        Verdict.BLOCK,
        Verdict.REVIEW,
    }:

        usage = estimate_usage(
            prompt,
            "",
            model_used,
        )

        return PipelineResult(
            verdict=verdict,
            content=content,
            risk_score=risk_score,
            reasons=reasons,
            corrections_applied=corrections,
            checks=checks,
            model_used=model_used,
            usage=usage,
            proposed_content=proposed_content,
        )

    # ---------------------------------------------------------
    # 5. Calculate optimization candidate
    # ---------------------------------------------------------

    optimization = optimize_prompt(content)

    checks.append(
        CheckResult(
            name="prompt_optimization",
            corrections=optimization.corrections,
            metadata={
                "original_tokens": optimization.original_tokens,
                "optimized_tokens": optimization.optimized_tokens,
                "tokens_saved": optimization.tokens_saved,
                "optimization_ratio": optimization.optimization_ratio,
            },
        )
    )

    # ---------------------------------------------------------
    # 6. Estimate usage
    #
    # IMPORTANT:
    # We return the optimized prompt as the current pipeline
    # content because the existing /v1/chat/completions flow
    # already uses the optimized prompt.
    #
    # The extension can display the savings and later let the
    # user decide whether to use it.
    # ---------------------------------------------------------

    usage = estimate_usage(
        optimization.optimized_prompt,
        "",
        model_used,
        original_prompt=prompt,
    )

    # ---------------------------------------------------------
    # 7. Return complete input decision
    # ---------------------------------------------------------

    return PipelineResult(
        verdict=verdict,
        content=optimization.optimized_prompt,
        risk_score=risk_score,
        reasons=reasons,
        corrections_applied=(
            corrections + optimization.corrections
        ),
        checks=checks,
        model_used=model_used,
        usage=usage,
        proposed_content=proposed_content,
    )


async def evaluate_output(
    *,
    prompt: str,
    response: str,
    context: str | None = None,
    original_prompt: str | None = None,
    requested_model: str = "auto",
    policy: SecurityPolicy = SecurityPolicy.MONITOR,
    expected_format: str | None = None,
    cache_hit: bool = False,
    store_in_cache: bool = True,
) -> PipelineResult:
    """
    Check LLM output before the extension displays it to the user.

    Flow:

        LLM response
             ↓
        safety checks
             ↓
        performance checks
             ↓
        decision
             ↓
        ALLOW / MASK / BLOCK / REVIEW
    """

    # ---------------------------------------------------------
    # 1. Select model
    # ---------------------------------------------------------

    model_used = select_model(
        requested_model,
        prompt,
        needs_reasoning=bool(context),
    )

    # ---------------------------------------------------------
    # 2. Safety checks
    # ---------------------------------------------------------

    checks, pii_result = _safety_checks(response)

    # ---------------------------------------------------------
    # 3. Performance / quality checks
    # ---------------------------------------------------------

    checks.extend(
        [
            check_drift(response, context),
            check_hallucination(response, context),
            validate_format(response, expected_format),
        ]
    )

    # ---------------------------------------------------------
    # 4. Optional semantic judge
    # ---------------------------------------------------------

    preliminary_verdict, _, _ = decide(
        checks,
        policy,
    )

    if preliminary_verdict is Verdict.REVIEW:
        checks.append(
            judge_response(
                response,
                context,
            )
        )

    # ---------------------------------------------------------
    # 5. Final decision
    # ---------------------------------------------------------

    verdict, risk_score, reasons = decide(
        checks,
        policy,
    )

    # ---------------------------------------------------------
    # 6. Enforce decision
    # ---------------------------------------------------------

    content, corrections, proposed_content = _enforced_content(
        original=response,
        pii_result=pii_result,
        verdict=verdict,
        blocked_message=BLOCKED_OUTPUT_MESSAGE,
    )

    # ---------------------------------------------------------
    # 7. Usage calculation
    # ---------------------------------------------------------

    usage = estimate_usage(
        prompt,
        content,
        model_used,
        original_prompt=original_prompt,
    )

    result = PipelineResult(
        verdict=verdict,
        content=content,
        risk_score=risk_score,
        reasons=reasons,
        corrections_applied=corrections,
        checks=checks,
        model_used=model_used,
        usage=usage,
        cache_hit=cache_hit,
        proposed_content=proposed_content,
    )

    # ---------------------------------------------------------
    # 8. Cache safe output
    # ---------------------------------------------------------

    if (
        store_in_cache
        and not cache_hit
        and verdict in (
            Verdict.PASS,
            Verdict.MASK,
        )
    ):
        key = cache_key_for(
            prompt=prompt,
            context=context,
            model=model_used,
            expected_format=expected_format,
        )

        await cache.set(
            key,
            content,
        )

    return result


async def evaluate_response(
    **kwargs: object,
) -> PipelineResult:
    """Backward-compatible output evaluation name."""

    return await evaluate_output(
        **kwargs,
    )  # type: ignore[arg-type]