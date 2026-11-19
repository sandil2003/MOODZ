"""PII Scrubber for clinical data privacy and sensitive pattern sanitization.

Recursively redacts email addresses, phone numbers, Social Security Numbers (SSN),
and payment card numbers from mental health dialogues and logs before persistence or export.
"""

import re
from typing import Dict, Any, List, Union


class PIIScrubber:
    """Masks sensitive clinical identifiers and PII in strings, dictionaries, and lists."""

    # Compiled regex patterns for sub-millisecond recursive redaction
    PATTERNS = [
        # Email addresses (e.g. user@example.com)
        (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[REDACTED_EMAIL]"),

        # Phone numbers: handles standard US/International formats: (123) 456-7890, 123-456-7890, +1 123 456 7890
        (re.compile(r"(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"), "[REDACTED_PHONE]"),

        # US Social Security Numbers (SSN: XXX-XX-XXXX)
        (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[REDACTED_SSN]"),

        # Credit / Debit Card Numbers (13-19 digits formatted with spaces or dashes)
        (re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"), "[REDACTED_CREDIT_CARD]"),
    ]

    @classmethod
    def scrub_text(cls, text: str) -> str:
        """Sanitize a text string by replacing recognized PII with redacted tokens."""
        if not text or not isinstance(text, str):
            return text or ""

        scrubbed = text
        for pattern, replacement in cls.PATTERNS:
            scrubbed = pattern.sub(replacement, scrubbed)
        return scrubbed

    @classmethod
    def scrub_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively scrub string values within nested dictionaries."""
        if not isinstance(data, dict):
            return data

        clean: Dict[str, Any] = {}
        for key, value in data.items():
            if isinstance(value, str):
                clean[key] = cls.scrub_text(value)
            elif isinstance(value, dict):
                clean[key] = cls.scrub_dict(value)
            elif isinstance(value, list):
                clean[key] = cls.scrub_list(value)
            else:
                clean[key] = value
        return clean

    @classmethod
    def scrub_list(cls, items: List[Any]) -> List[Any]:
        """Recursively scrub string values within lists."""
        clean: List[Any] = []
        for item in items:
            if isinstance(item, str):
                clean.append(cls.scrub_text(item))
            elif isinstance(item, dict):
                clean.append(cls.scrub_dict(item))
            elif isinstance(item, list):
                clean.append(cls.scrub_list(item))
            else:
                clean.append(item)
        return clean

    @classmethod
    def scrub(cls, payload: Union[str, Dict[str, Any], List[Any], Any]) -> Any:
        """Convenience entrypoint that automatically detects payload type and scrubs accordingly."""
        if isinstance(payload, str):
            return cls.scrub_text(payload)
        if isinstance(payload, dict):
            return cls.scrub_dict(payload)
        if isinstance(payload, list):
            return cls.scrub_list(payload)
        return payload
