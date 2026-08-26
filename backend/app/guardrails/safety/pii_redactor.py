"""PII masking only. Detection, policy, and final enforcement live elsewhere."""
from __future__ import annotations

from app.guardrails.schemas.pii import PIIDetection, PIIResult


class PIIRedactor:
    """Mask detector ranges right-to-left so earlier replacement never shifts offsets."""

    def redact(self, content: str, result: PIIResult) -> str:
        if not content or not result.detections:
            return content

        redacted = content
        for detection in sorted(result.detections, key=lambda item: item.start, reverse=True):
            if detection.start < 0 or detection.end > len(content) or detection.start >= detection.end:
                continue
            original = content[detection.start:detection.end]
            replacement = self._mask(detection, original)
            redacted = f"{redacted[:detection.start]}{replacement}{redacted[detection.end:]}"
        return redacted

    def _mask(self, detection: PIIDetection, value: str) -> str:
        entity_type = detection.entity_type.upper()
        if entity_type in {"EMAIL", "EMAIL_ADDRESS"}:
            return self._mask_email(value)
        if entity_type in {"PHONE", "PHONE_NUMBER", "IN_PHONE_NUMBER"}:
            return self._mask_phone(value)
        if entity_type == "IP_ADDRESS":
            return self._mask_ip_address(value)
        if entity_type == "CREDIT_CARD":
            return self._mask_credit_card(value)
        if entity_type == "US_SSN":
            return self._mask_ssn(value)
        if entity_type == "IN_PAN":
            return self._mask_pan(value)
        if entity_type == "IN_AADHAAR":
            return self._mask_aadhaar(value)
        if entity_type == "IN_PASSPORT":
            return self._mask_passport(value)
        return f"[{entity_type}_REDACTED]"

    @staticmethod
    def _mask_email(value: str) -> str:
        local, separator, domain = value.partition("@")
        return f"{local[0]}***@{domain}" if separator and local else "[EMAIL_REDACTED]"

    @staticmethod
    def _mask_phone(value: str) -> str:
        digits = "".join(character for character in value if character.isdigit())
        return "#" * len(digits) if len(digits) <= 2 else f"{digits[:2]}{'#' * (len(digits) - 2)}"

    @staticmethod
    def _mask_ip_address(value: str) -> str:
        parts = value.split(".")
        return f"{parts[0]}.{parts[1]}.*.*" if len(parts) == 4 else "[IP_ADDRESS_REDACTED]"

    @staticmethod
    def _mask_credit_card(value: str) -> str:
        digits = "".join(character for character in value if character.isdigit())
        return "#" * len(digits) if len(digits) <= 4 else f"{'#' * (len(digits) - 4)}{digits[-4:]}"

    @staticmethod
    def _mask_ssn(value: str) -> str:
        return "###-##-####" if len("".join(character for character in value if character.isdigit())) == 9 else "[US_SSN_REDACTED]"

    @staticmethod
    def _mask_pan(value: str) -> str:
        return f"{value[0]}****{value[5:9]}{value[9]}" if len(value) == 10 else "[IN_PAN_REDACTED]"

    @staticmethod
    def _mask_aadhaar(value: str) -> str:
        digits = "".join(character for character in value if character.isdigit())
        return f"#### #### {digits[-4:]}" if len(digits) == 12 else "[IN_AADHAAR_REDACTED]"

    @staticmethod
    def _mask_passport(value: str) -> str:
        return f"{value[0]}******{value[-1]}" if len(value) >= 2 else "[IN_PASSPORT_REDACTED]"


_redactor = PIIRedactor()


def redact_pii(content: str, result: PIIResult) -> str:
    """Compatibility wrapper used by the pipeline."""
    return _redactor.redact(content, result)
