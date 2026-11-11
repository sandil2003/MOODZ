import sys
import os
import asyncio

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath("backend"))

from app.services.crisis_detector import CrisisDetector
from app.core.pii_scrubber import PIIScrubber

async def verify_crisis_detector():
    print("=== CRISIS DETECTOR VERIFICATION ===")
    cd = CrisisDetector()
    
    # 1. Stated in test plan TC-SAFE-01..03
    plan_cases = [
        "I want to commit suicide",
        "I'm feeling suicidal today",
        "I want to kill myself",
        "I'm going to kill myself tonight",
        "I want to end my life right now",
        "I feel like hurting myself",
        "I've been hurting myself lately",
        "I have thoughts of self-harm",
        "I want to self harm",
        "Self-harming feels like the only relief",
        "I just want to end it all",
        "Thinking about ending it all tonight",
        "Ending my life feels like the only option"
    ]
    for prompt in plan_cases:
        res = await cd.check_crisis(prompt)
        assert res["type"] == "immediate_risk" and res["score"] == 1.0, f"Failed on plan case: {prompt} -> {res}"
    print(f"All {len(plan_cases)} test-plan cases PASSED with immediate_risk (1.0).")

    # 2. Benign control statements from TC-SAFE-04..05
    benign_cases = [
        "This tool is harmless and fun",
        "How do I harm-proof my house?",
        "The workout was a killer, but I feel good",
        "I hurt my ankle playing soccer yesterday",
        "I'm killing time waiting for the bus",
        "That comedy show killed it last night",
        "Work has been really stressful this week"
    ]
    for prompt in benign_cases:
        res = await cd.check_crisis(prompt)
        assert res["type"] == "none" and res["score"] == 0.0, f"False positive on benign: {prompt} -> {res}"
    print(f"All {len(benign_cases)} benign control cases PASSED with none (0.0).")

    # 3. Empty & boundary inputs from TC-SAFE-06
    assert (await cd.check_crisis(""))["score"] == 0.0
    assert (await cd.check_crisis("   "))["score"] == 0.0
    assert (await cd.check_crisis(None))["score"] == 0.0
    print("Boundary inputs PASSED.")

    # 4. Adversarial Edge Cases (Challenger stress-test)
    adversarial_misses = [
        ("I want to kill  myself", "Multiple spaces between kill and myself"),
        ("I want to kill my self", "Split my self"),
        ("I want to die", "Missing 'want to die' in patterns"),
        ("I am going to hang myself", "Missing 'hang myself' in patterns"),
        ("I'm overdosing", "Missing 'overdosing' in patterns"),
        ("I'm taking my own life", "Missing 'take/taking my own life' in patterns")
    ]
    print("\n--- Adversarial Edge Case Analysis ---")
    for prompt, reason in adversarial_misses:
        res = await cd.check_crisis(prompt)
        detected = res["score"] == 1.0
        print(f"Prompt: '{prompt}' -> Detected: {detected} | Nuance: {reason}")


def verify_pii_scrubber():
    print("\n=== PII SCRUBBER VERIFICATION ===")
    
    # TC-PII-01: Email
    email_text = "Hello, my doctor is dr.smith@healthcare.org and my email is user123@gmail.com."
    email_scrubbed = PIIScrubber.scrub_text(email_text)
    assert "dr.smith@healthcare.org" not in email_scrubbed
    assert "user123@gmail.com" not in email_scrubbed
    assert email_scrubbed.count("[REDACTED_EMAIL]") == 2
    print("TC-PII-01 (Email) PASSED.")

    # TC-PII-02: Phone formats
    phone_cases = [
        ("(555) 234-5678", True),
        ("555-890-1234", True),
        ("+1 800 555 1234", True),
        ("1234567890", True),
    ]
    for phone_str, expected in phone_cases:
        res = PIIScrubber.scrub_text(phone_str)
        assert "[REDACTED_PHONE]" in res, f"Failed on phone format: {phone_str} -> {res}"
    print("TC-PII-02 (Phone) PASSED.")

    # TC-PII-03: SSN
    ssn_text = "My SSN is 000-12-3456 and my file id is 987-65-4321."
    ssn_scrubbed = PIIScrubber.scrub_text(ssn_text)
    assert "000-12-3456" not in ssn_scrubbed
    assert "987-65-4321" not in ssn_scrubbed
    assert ssn_scrubbed.count("[REDACTED_SSN]") == 2
    print("TC-PII-03 (SSN) PASSED.")

    # TC-PII-04: Credit card
    cc_text = "Payment card 4111-2222-3333-4444 and 4555 6666 7777 8888."
    cc_scrubbed = PIIScrubber.scrub_text(cc_text)
    assert "4111-2222-3333-4444" not in cc_scrubbed
    assert "4555 6666 7777 8888" not in cc_scrubbed
    assert cc_scrubbed.count("[REDACTED_CREDIT_CARD]") == 2
    print("TC-PII-04 (Credit Card) PASSED.")

    # TC-PII-05: Recursive dict & list
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
    assert clean["notes"][1] == "safe note"
    print("TC-PII-05 (Dict/List recursive) PASSED.")

    # Challenger stress-test on PII
    print("\n--- Adversarial PII Edge Cases ---")
    amex_card = "3782-822463-10005" # 15-digit Amex
    amex_res = PIIScrubber.scrub_text(amex_card)
    print(f"Amex 15-digit: '{amex_card}' -> '{amex_res}' (Redacted: {'[REDACTED_CREDIT_CARD]' in amex_res})")

    eleven_digits = "12345678901 items"
    eleven_res = PIIScrubber.scrub_text(eleven_digits)
    print(f"11 digits string: '{eleven_digits}' -> '{eleven_res}'")

if __name__ == "__main__":
    asyncio.run(verify_crisis_detector())
    verify_pii_scrubber()
