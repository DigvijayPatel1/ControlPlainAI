from datetime import datetime
from typing import Optional, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.common import Verdict


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = "auto"                      # "auto" lets the model router decide
    messages: list[ChatMessage]
    context: Optional[str] = None             # grounding context for hallucination checks
    stream: bool = False


class UsageOut(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float


class ChatCompletionResponse(BaseModel):
    id: UUID
    verdict: Verdict
    model_used: str
    content: str
    corrections_applied: list[str] = Field(default_factory=list)
    usage: UsageOut


class PendingReviewResponse(BaseModel):
    review_id: UUID
    status: Literal["pending_review"] = "pending_review"
    reason: str


class BlockedResponse(BaseModel):
    verdict: Literal[Verdict.BLOCK] = Verdict.BLOCK
    reason: str
    replacement_message: str


class RequestLogEntry(BaseModel):
    """Public shape of a RequestLog row, returned by /v1/admin/requests.
    from_attributes=True lets this be built directly from the ORM object,
    e.g. RequestLogEntry.model_validate(row)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    timestamp: datetime = Field(validation_alias="created_at")
    principal_id: str
    prompt: str
    response: str = Field(validation_alias="response_final")
    verdict: Verdict
    latency_ms: int
    cost_usd: float


class AnalyticsSummary(BaseModel):
    total_requests: int
    block_rate: float
    avg_latency_ms: float
    total_cost_usd: float
    cost_saved_by_routing_usd: float
    cache_hit_rate: float