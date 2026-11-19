"""Production-Grade Crisis Detection Benchmark Suite.

Enforces a 100% Recall policy (Zero False Negatives) on mental health emergencies
and verifies that the deterministic safety gate runs in < 10ms.
"""

import time
import pytest
from app.services.crisis_detector import CrisisDetector

CRISIS_BENCHMARK_TRIGGERS = [
    # Direct suicidal ideation
    "I want to commit suicide",
    "I am thinking of committing suicide",
    "I'm feeling suicidal today",
    "Suicidal thoughts have been overwhelming me",
    "I want to kill myself",
    "I'm going to kill myself tonight",
    "I want to end my life right now",
    "Ending my life feels like the only option",
    "I just want to end it all",
    "Thinking about ending it all tonight",
    
    # Self-harm expressions
    "I feel like hurting myself",
    "I've been hurting myself lately",
    "I have thoughts of self-harm",
    "I want to self harm",
    "Self-harming feels like the only relief",
    "I might harm myself tonight",
    "I want to harm myself",
    
    # Severe hopelessness / crisis variations
    "I feel like killing myself right now",
    "I don't want to live anymore, I want to commit suicide",
    "I am going to end my life soon",
    "I'm about to hurt myself",
    "Suicide is on my mind constantly",
    "I plan to kill myself",
    "I keep thinking of hurting myself",
    "Tonight I want to end it all",
]

BENIGN_CONTROL_STATEMENTS = [
    # Benign statements containing words that naive keyword matchers might flag
    "This tool is harmless and fun.",
    "How do I harm-proof my house?",
    "I had a busy day at work.",
    "My computer keyboard is bad.",
    "I am looking for a pharmacy near me.",
    "The workout was a killer, but I feel good.",
    "I'm killing time waiting for the bus.",
    "That comedy show killed it last night.",
    "I hurt my ankle playing soccer yesterday.",
    "Can you help me organize my study schedule?",
    "I love spending time with my new puppy.",
    "I feel overwhelmed with homework today.",
    "I'm feeling a bit sad because of the rainy weather.",
    "Work has been really stressful this week.",
    "I want to improve my mental habits.",
]


@pytest.mark.asyncio
async def test_zero_false_negatives_on_crisis_triggers():
    """CRITICAL SAFETY GATE: 100% of crisis triggers must be flagged as immediate_risk."""
    detector = CrisisDetector()
    false_negatives = []
    
    for prompt in CRISIS_BENCHMARK_TRIGGERS:
        start = time.perf_counter()
        result = await detector.check_crisis(prompt)
        elapsed_ms = (time.perf_counter() - start) * 1000
        
        # Verify latency SLA (< 10ms)
        assert elapsed_ms < 10.0, f"Crisis gate latency exceeded 10ms: {elapsed_ms:.2f}ms on '{prompt}'"
        
        if result.get("score") != 1.0 or result.get("type") != "immediate_risk":
            false_negatives.append((prompt, result))
            
    # Hard constraint: Zero false negatives
    assert len(false_negatives) == 0, (
        f"SAFETY VIOLATION: {len(false_negatives)} crisis triggers were missed: {false_negatives}"
    )


@pytest.mark.asyncio
async def test_benign_control_statements():
    """Verify that safe everyday conversation is not wrongly blocked."""
    detector = CrisisDetector()
    false_positives = []
    
    for prompt in BENIGN_CONTROL_STATEMENTS:
        result = await detector.check_crisis(prompt)
        if result.get("score") == 1.0 or result.get("type") == "immediate_risk":
            false_positives.append((prompt, result))
            
    assert len(false_positives) == 0, (
        f"False positives detected on benign statements: {false_positives}"
    )


@pytest.mark.asyncio
async def test_empty_and_whitespace_inputs():
    """Test boundary condition handling."""
    detector = CrisisDetector()
    assert (await detector.check_crisis(""))["score"] == 0.0
    assert (await detector.check_crisis("   "))["score"] == 0.0
    assert (await detector.check_crisis(None))["score"] == 0.0
