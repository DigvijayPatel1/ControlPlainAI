from app.guardrails.safety.pii_policy import PIIAction, classify_pii
from app.guardrails.schemas.pii import PIIDetection


def test_email_is_masked():
    detections = [PIIDetection(entity_type="EMAIL", start=0, end=10, score=0.99)]
    assert classify_pii(detections) is PIIAction.MASK


def test_credit_card_is_blocked():
    detections = [PIIDetection(entity_type="CREDIT_CARD", start=0, end=16, score=0.99)]
    assert classify_pii(detections) is PIIAction.BLOCK
