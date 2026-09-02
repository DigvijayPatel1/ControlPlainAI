"""Internal data contracts shared by the PII guardrail modules."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PIIDetection(BaseModel):
    """PII metadata only; the sensitive substring is never stored here."""

    model_config = ConfigDict(frozen=True)

    entity_type: str
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    score: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def end_must_not_precede_start(self) -> "PIIDetection":
        if self.end < self.start:
            raise ValueError("end must be greater than or equal to start")
        return self


class PIIResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    passed: bool
    detections: list[PIIDetection]

    @property
    def count(self) -> int:
        return len(self.detections)

    @property
    def has_pii(self) -> bool:
        return bool(self.detections)
