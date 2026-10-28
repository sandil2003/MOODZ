"""PII Scrubber for sanitizing mental health dialogues and user messages before logging and tracing."""

import re
from typing import Dict, Any, List, Union

class PIIScrubber:
    """Masks phone numbers, emails, addresses, SSNs, and credit cards in traces and telemetry."""
    
    # Common PII Regex Patterns
    PATTERNS = [
        # Email addresses
        (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), "[REDACTED_EMAIL]"),
        
        # Phone numbers (US/Intl common formats: (123) 456-7890, 123-456-7890, +1 123 456 7890, etc.)
        (re.compile(r"(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"), "[REDACTED_PHONE]"),
        
        # Social Security Numbers (SSN: XXX-XX-XXXX)
        (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[REDACTED_SSN]"),
        
        # Credit Card Numbers (13 to 19 digits with dashes or spaces)
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
        
        clean = {}
        for k, v in data.items():
            if isinstance(v, str):
                clean[k] = cls.scrub_text(v)
            elif isinstance(v, dict):
                clean[k] = cls.scrub_dict(v)
            elif isinstance(v, list):
                clean[k] = cls.scrub_list(v)
            else:
                clean[k] = v
        return clean

    @classmethod
    def scrub_list(cls, items: List[Any]) -> List[Any]:
        """Recursively scrub string values within lists."""
        clean = []
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
        """Generic scrubber entry point for strings, dicts, and lists."""
        if isinstance(payload, str):
            return cls.scrub_text(payload)
        elif isinstance(payload, dict):
            return cls.scrub_dict(payload)
        elif isinstance(payload, list):
            return cls.scrub_list(payload)
        return payload
