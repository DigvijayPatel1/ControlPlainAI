"""Internal data contracts for the bias guardrail."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class BiasDetection(BaseModel):
    model_config = ConfigDict(frozen=True)
    category: str
    severity: Literal["medium", "high"]
    score: float = Field(ge=0.0, le=1.0)
    reason: str
    start: int = Field(ge=0)
    end: int = Field(ge=0)


class BiasResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    passed: bool
    detections: list[BiasDetection]
    uncertain: bool

    @property
    def count(self) -> int:
        return len(self.detections)
