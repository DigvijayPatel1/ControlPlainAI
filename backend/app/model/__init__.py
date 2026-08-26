"""Backward-compatible alias for the legacy singular model package."""

from app.models import ApiKey, Budget, RequestLog, ReviewItem, User

__all__ = ["ApiKey", "Budget", "RequestLog", "ReviewItem", "User"]
