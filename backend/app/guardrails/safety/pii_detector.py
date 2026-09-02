"""PII detection only. This module never alters content or selects a verdict.

Two detection layers:
  1. Regex recognizers — structured formats (email, phone, SSN, credit card,
     API keys). Fast, precise, zero setup.
  2. spaCy NER — free-text entities (PERSON, GPE/LOCATION, ORG) that regex
     structurally cannot catch. This is what makes pii_policy.py's PERSON
     and LOCATION mask rules actually fire; previously those rules existed
     but nothing ever produced those entity types.

If spaCy or its model isn't installed, NER is skipped and a conservative
capitalized-name heuristic is used instead so detection doesn't silently
do nothing — see _fallback_person_heuristic. Install spaCy properly with:

    uv add spacy
    uv run python -m spacy download en_core_web_sm
"""
from __future__ import annotations

import re
from functools import lru_cache

from app.guardrails.schemas.pii import PIIDetection, PIIResult

try:
    import spacy  # type: ignore[import-untyped]
except ImportError:
    spacy = None  # NER layer degrades to the regex-only heuristic below


@lru_cache(maxsize=1)
def _load_nlp():
    """Loaded once per process. Returns None if spaCy or the model isn't
    available — callers must handle that, not crash on it."""
    if spacy is None:
        return None
    try:
        return spacy.load("en_core_web_sm", disable=["parser", "lemmatizer"])
    except OSError:
        # spaCy is installed but the model wasn't downloaded
        return None


_SPACY_LABEL_MAP = {
    "PERSON": "PERSON",
    "GPE": "LOCATION",
    "LOC": "LOCATION",
    "ORG": "ORG",
}

# Fallback used only when spaCy/the model isn't available: two-or-more
# consecutive capitalized words, not at a sentence start. Deliberately
# conservative (some false negatives) since it's a stopgap, not the primary
# path — get the real model installed for production use.
_FALLBACK_PERSON_PATTERN = re.compile(
    r"(?<!^)(?<![.!?]\s)\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\b"
)


class PIIDetector:
    """Detect common PII and credentials with existing project dependencies.

    It returns entity types, confidence scores, and character ranges only.
    Redaction belongs in ``pii_redactor.py``; the decision engine decides
    whether a request is allowed, masked, blocked, or reviewed.
    """

    name = "pii"
    stage = "pre"

    _recognizers: tuple[tuple[str, re.Pattern[str], float], ...] = (
        ("EMAIL", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE), 0.95),
        ("PHONE_NUMBER", re.compile(r"(?<!\d)(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?){2,3}\d{3,4}(?!\d)"), 0.80),
        ("US_SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), 0.95),
        ("CREDIT_CARD", re.compile(r"\b(?:\d[ -]*?){13,19}\b"), 0.85),
        ("IP_ADDRESS", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), 0.70),
        ("IN_PAN", re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"), 0.85),
        ("IN_AADHAAR", re.compile(r"\b[2-9]\d{3}[ -]?\d{4}[ -]?\d{4}\b"), 0.75),
        ("IN_PASSPORT", re.compile(r"\b[A-Z]\d{7}\b"), 0.65),
        ("IN_PHONE_NUMBER", re.compile(r"(?<!\d)(?:\+91[\s-]?)?[6-9]\d{9}(?!\d)"), 0.80),
        ("API_KEY", re.compile(r"\b(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16})\b"), 0.95),
        ("JWT", re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"), 0.95),
        ("SECRET", re.compile(r"(?i)\b(?:password|secret|token|api_key)\s*[:=]\s*['\"]?[^'\"\s]{6,}['\"]?"), 0.75),
    )

    def __init__(self, score_threshold: float = 0.50) -> None:
        self.score_threshold = score_threshold

    def detect(self, text: str) -> PIIResult:
        if not text or not text.strip():
            return PIIResult(passed=True, detections=[])

        detections = [
            PIIDetection(
                entity_type=entity_type,
                start=match.start(),
                end=match.end(),
                score=score,
            )
            for entity_type, pattern, score in self._recognizers
            if score >= self.score_threshold
            for match in pattern.finditer(text)
        ]
        detections.extend(self._detect_free_text_entities(text))
        detections = self._remove_overlaps(detections)
        return PIIResult(passed=not detections, detections=detections)

    def _detect_free_text_entities(self, text: str) -> list[PIIDetection]:
        """PERSON/LOCATION/ORG — the layer regex structurally can't do."""
        nlp = _load_nlp()
        if nlp is not None:
            doc = nlp(text)
            return [
                PIIDetection(
                    entity_type=_SPACY_LABEL_MAP[ent.label_],
                    start=ent.start_char,
                    end=ent.end_char,
                    score=0.75,
                )
                for ent in doc.ents
                if ent.label_ in _SPACY_LABEL_MAP
            ]

        # Fallback heuristic — lower confidence, PERSON only.
        return [
            PIIDetection(
                entity_type="PERSON",
                start=match.start(1),
                end=match.end(1),
                score=0.55,
            )
            for match in _FALLBACK_PERSON_PATTERN.finditer(text)
        ]

    @staticmethod
    def _remove_overlaps(detections: list[PIIDetection]) -> list[PIIDetection]:
        ordered = sorted(detections, key=lambda item: (item.start, -(item.end - item.start), -item.score))
        accepted: list[PIIDetection] = []
        for current in ordered:
            if not any(current.start < existing.end and current.end > existing.start for existing in accepted):
                accepted.append(current)
        return accepted