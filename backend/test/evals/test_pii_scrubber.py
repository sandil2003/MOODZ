"""Tests for PII Scrubber ensuring no mental health conversation leaks personal data."""

import pytest
from app.core.pii_scrubber import PIIScrubber


def test_scrub_emails():
    text = "Hello, my doctor is dr.smith@healthcare.org and my email is user123@gmail.com."
    scrubbed = PIIScrubber.scrub_text(text)
    assert "dr.smith@healthcare.org" not in scrubbed
    assert "user123@gmail.com" not in scrubbed
    assert "[REDACTED_EMAIL]" in scrubbed


def test_scrub_phone_numbers():
    cases = [
        "Call me at (555) 234-5678 if I don't reply.",
        "My therapist's office is 555-890-1234.",
        "Reach out at +1 800 555 1234 immediately.",
    ]
    for case in cases:
        scrubbed = PIIScrubber.scrub_text(case)
        assert "[REDACTED_PHONE]" in scrubbed
        assert "555" not in scrubbed or "[REDACTED_PHONE]" in scrubbed


def test_scrub_ssn_and_financial():
    text = "My SSN is 000-12-3456 and my card is 4111-2222-3333-4444."
    scrubbed = PIIScrubber.scrub_text(text)
    assert "000-12-3456" not in scrubbed
    assert "4111-2222-3333-4444" not in scrubbed
    assert "[REDACTED_SSN]" in scrubbed
    assert "[REDACTED_CREDIT_CARD]" in scrubbed


def test_scrub_dict_and_list():
    payload = {
        "user_name": "Alice",
        "email": "alice@example.com",
        "notes": ["Had panic attack, called 555-123-4567", "safe note"],
        "metadata": {"emergency_contact": "bob@domain.com"}
    }
    clean = PIIScrubber.scrub_dict(payload)
    assert clean["email"] == "[REDACTED_EMAIL]"
    assert "[REDACTED_PHONE]" in clean["notes"][0]
    assert clean["metadata"]["emergency_contact"] == "[REDACTED_EMAIL]"
