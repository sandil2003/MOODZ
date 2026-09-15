import asyncio
import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services import CrisisDetector


async def run_tests():
    detector = CrisisDetector()
    print("Testing CrisisDetector...")

    # Test cases that SHOULD trigger crisis detection
    trigger_cases = [
        "I want to commit suicide",
        "I feel like hurting myself",
        "I want to end my life",
        "I think of self-harm sometimes",
        "I want to kill myself today",
        "I want to end it all"
    ]

    # Test cases that SHOULD NOT trigger crisis detection
    safe_cases = [
        "This tool is harmless and fun.",
        "I am looking for a pharmacy.",
        "My keyboard is bad.", # Was previously a trigger, should now be safe
        "I had a busy day at work.",
        "How do I harm-proof my house?"
    ]

    print("\n--- Testing Trigger Cases ---")
    for case in trigger_cases:
        res = await detector.check_crisis(case)
        print(f"Input: '{case}' => Result: {res}")
        assert res["type"] == "immediate_risk"
        assert res["score"] == 1.0

    print("\n--- Testing Safe Cases ---")
    for case in safe_cases:
        res = await detector.check_crisis(case)
        print(f"Input: '{case}' => Result: {res}")
        assert res["type"] == "none"
        assert res["score"] == 0.0

    print("\n✅ All CrisisDetector tests passed successfully!")


if __name__ == "__main__":
    asyncio.run(run_tests())
