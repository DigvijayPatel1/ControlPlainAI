"""Shared, dependency-free contracts for the runtime guardrail pipeline."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.models.common import Verdict


@dataclass(slots=True)
class CheckResult:
    name: str
    risk_score: float = 0.0
    reasons: list[str] = field(default_factory=list)
    corrections: list[str] = field(default_factory=list)
    content: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.risk_score = max(0.0, min(1.0, float(self.risk_score)))


@dataclass(slots=True)
class UsageEstimate:
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    original_prompt_tokens: int = 0
    optimized_prompt_tokens: int = 0
    tokens_saved: int = 0
    savings_usd: float = 0.0


@dataclass(slots=True)
class PipelineResult:
    verdict: Verdict
    content: str
    risk_score: float
    reasons: list[str]
    corrections_applied: list[str]
    checks: list[CheckResult]
    model_used: str
    usage: UsageEstimate
    cache_hit: bool = False
    proposed_content: str | None = None

