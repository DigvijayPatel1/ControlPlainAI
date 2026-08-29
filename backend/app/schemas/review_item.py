from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.common import ReviewAction


class ReviewItem(BaseModel):
    """Public shape of a ReviewItem row, returned by /v1/review/queue.
    from_attributes=True lets this be built directly from the ORM object,
    e.g. ReviewItem.model_validate(row)."""

    model_config = ConfigDict(from_attributes=True)

    review_id: UUID = Field(validation_alias="id")
    prompt: str
    proposed_response: str
    flagged_reason: str
    risk_score: float
    created_at: datetime


class ReviewDecisionRequest(BaseModel):
    action: ReviewAction
    edited_content: Optional[str] = None

    @model_validator(mode="after")
    def edited_content_required_for_edit_or_override(self) -> "ReviewDecisionRequest":
        if self.action in (ReviewAction.EDIT, ReviewAction.OVERRIDE) and not self.edited_content:
            raise ValueError("edited_content is required when action is 'edit' or 'override'")
        return self


class ReviewDecisionResult(BaseModel):
    review_id: UUID
    action_taken: ReviewAction
    final_response: str
    resolved_by: str

class ReviewItemResponse(BaseModel):
    id: UUID
    request_log_id: UUID
    prompt: str
    proposed_response: Optional[str] = None
    flagged_reason: Optional[str] = None
    risk_score: float
    resolved: bool
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    action_taken: Any = None # Tip: Replace 'Any' with your actual Enum type if you have one
    final_response: Optional[str] = None
    created_at: datetime

    # Instructs Pydantic to read properties from the SQLAlchemy ORM model
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

class ReviewListResponse(BaseModel):
    items: List[ReviewItemResponse]
    count: int