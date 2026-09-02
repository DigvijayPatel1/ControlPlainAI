from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.common import PrincipalType


class BudgetCreate(BaseModel):
    principal_id: str
    principal_type: PrincipalType
    parent_principal_id: Optional[str] = None  # resolved to parent_budget_id server-side
    monthly_limit_usd: float = Field(gt=0)


class BudgetUpdate(BaseModel):
    monthly_limit_usd: Optional[float] = Field(default=None, gt=0)


class BudgetResponse(BaseModel):
    """from_attributes=True lets this be built directly from the ORM object;
    remaining_usd is computed, not stored, so it's added after validation."""

    model_config = ConfigDict(from_attributes=True)

    principal_id: str
    principal_type: PrincipalType
    monthly_limit_usd: float
    spent_usd: float
    request_count: int
    blocked_count: int
    period_end: Optional[datetime] = None

    @property
    def remaining_usd(self) -> float:
        return self.monthly_limit_usd - self.spent_usd