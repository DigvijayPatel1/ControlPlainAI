"""Low-cost deterministic prompt optimization.

Safety checks must run before optimization. This module only removes
conservative, redundant wording and preserves the original prompt for metrics.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OptimizationResult:
    original_prompt: str
    optimized_prompt: str
    original_tokens: int
    optimized_tokens: int
    tokens_saved: int
    optimization_ratio: float
    corrections: list[str]


_REDUNDANT_PHRASES: tuple[tuple[str, str], ...] = (
    ("please provide me with", "provide"),
    ("please provide", "provide"),
    ("please explain to me", "explain"),
    ("i would like you to", ""),
    ("i want you to", ""),
    ("can you please", ""),
    ("could you please", ""),
    ("would you please", ""),
    ("in order to", "to"),
    ("at this point in time", "now"),
    ("due to the fact that", "because"),
    ("for the purpose of", "for"),
    ("a large number of", "many"),
    ("a small number of", "few"),
)
_WHITESPACE = re.compile(r"[ \t]+")
_MULTIPLE_NEWLINES = re.compile(r"\n{3,}")
_TOKEN = re.compile(r"\w+|[^\w\s]", re.UNICODE)


def estimate_tokens(content: str) -> int:
    """Use the same lightweight token approximation as the tracker."""
    return len(_TOKEN.findall(content)) if content else 0


def optimize_prompt(prompt: str) -> OptimizationResult:
    """Remove only obvious redundant phrases and excessive whitespace."""
    if not prompt or not prompt.strip():
        return OptimizationResult(prompt, prompt, 0, 0, 0, 0.0, [])

    optimized = prompt.strip()
    corrections: list[str] = []

    for phrase, replacement in _REDUNDANT_PHRASES:
        optimized, count = re.subn(re.escape(phrase), replacement, optimized, flags=re.IGNORECASE)
        if count:
            corrections.append(f"removed_or_simplified:{phrase}")

    new_value = _WHITESPACE.sub(" ", optimized)
    if new_value != optimized:
        optimized = new_value
        corrections.append("normalized_whitespace")

    new_value = _MULTIPLE_NEWLINES.sub("\n\n", optimized)
    if new_value != optimized:
        optimized = new_value
        corrections.append("removed_excessive_blank_lines")

    optimized = optimized.strip()
    original_tokens = estimate_tokens(prompt)
    optimized_tokens = estimate_tokens(optimized)
    tokens_saved = max(0, original_tokens - optimized_tokens)
    ratio = tokens_saved / original_tokens if original_tokens else 0.0

    return OptimizationResult(
        original_prompt=prompt,
        optimized_prompt=optimized,
        original_tokens=original_tokens,
        optimized_tokens=optimized_tokens,
        tokens_saved=tokens_saved,
        optimization_ratio=round(ratio, 4),
        corrections=corrections,
    )
