"""PII sensitivity policy. It classifies findings but does not enforce them."""
from __future__ import annotations

from enum import Enum

from app.guardrails.schemas.pii import PIIDetection


class PIIAction(str, Enum):
    ALLOW = "allow"
    MASK = "mask"
    BLOCK = "block"
    REVIEW = "review"


MASK_ENTITY_TYPES = frozenset({
    "PERSON",
    "EMAIL",
    "EMAIL_ADDRESS",
    "PHONE",
    "PHONE_NUMBER",
    "IN_PHONE_NUMBER",
    "LOCATION",
    "DATE_TIME",
    "IP_ADDRESS",
    "URL",
})

BLOCK_ENTITY_TYPES = frozenset({
    "CREDIT_CARD",
    "US_SSN",
    "SSN",
    "US_BANK_NUMBER",
    "IBAN_CODE",
    "US_DRIVER_LICENSE",
    "US_PASSPORT",
    "IN_PAN",
    "IN_AADHAAR",
    "IN_PASSPORT",
    "API_KEY",
    "JWT",
    "SECRET",
    "PASSWORD",
})


def classify_pii(detections: list[PIIDetection]) -> PIIAction:
    """Return the strictest PII action; unknown types are safely reviewed."""
    entity_types = {item.entity_type.upper() for item in detections}
    if entity_types & BLOCK_ENTITY_TYPES:
        return PIIAction.BLOCK
    if entity_types - MASK_ENTITY_TYPES:
        return PIIAction.REVIEW
    if entity_types:
        return PIIAction.MASK
    return PIIAction.ALLOW
