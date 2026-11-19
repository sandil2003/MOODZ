"""Automated tests for Google ADK Agent and LangGraph Hybrid Mood Agent."""

import asyncio
import sys
import os
from uuid import uuid4
import pytest

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.agents.mood_adk import mood_adk_agent, check_crisis_tool
from app.services.mood_graph import MoodHybridGraph, get_mood_graph
from app.services.mood_agent import MoodAgentChainV2, get_mood_agent
from app.services.crisis_detector import CrisisDetector


@pytest.mark.asyncio
async def test_google_adk_agent_definition():
    """Verify that Google ADK agent is correctly declared with tools and metadata."""
    assert mood_adk_agent.name == "mood_agent"
    assert "empathetic" in mood_adk_agent.instruction.lower()
    assert len(mood_adk_agent.tools) >= 4
    
    # Test ADK crisis tool directly
    crisis_res = await check_crisis_tool("I feel like hurting myself today")
    assert crisis_res["type"] == "immediate_risk"
    assert crisis_res["score"] == 1.0

    safe_res = await check_crisis_tool("I had a nice walk in the park")
    assert safe_res["type"] == "none"
    assert safe_res["score"] == 0.0


@pytest.mark.asyncio
async def test_deterministic_safety_gate():
    """Verify that the LangGraph deterministic safety gate flags crisis with 0ms / 0 tokens."""
    graph = await get_mood_graph()
    
    # 1. Trigger case
    trigger_state = {
        "user_id": uuid4(),
        "session_id": uuid4(),
        "user_message": "I want to kill myself"
    }
    safety_output = await graph.safety_gate_node(trigger_state)
    assert safety_output["is_crisis"] is True
    assert "988" in safety_output["crisis_response"]
    
    # 2. Safe case
    safe_state = {
        "user_id": uuid4(),
        "session_id": uuid4(),
        "user_message": "I am feeling a bit tired after a long work day"
    }
    safe_output = await graph.safety_gate_node(safe_state)
    assert safe_output["is_crisis"] is False


@pytest.mark.asyncio
async def test_pure_markdown_streaming_crisis_response():
    """Verify that crisis messages stream 'CRISIS' signal immediately."""
    graph = await get_mood_graph()
    user_id = uuid4()
    session_id = uuid4()
    
    chunks = []
    result_holder = {}
    async for chunk in graph.astream_chat(user_id, session_id, "I want to end it all", result_holder):
        chunks.append(chunk)
        
    assert "CRISIS" in chunks


@pytest.mark.asyncio
async def test_pure_markdown_streaming_conversational():
    """Verify that normal conversations stream pure Markdown without JSON formatting."""
    agent = await get_mood_agent()
    user_id = uuid4()
    session_id = uuid4()
    
    chunks = []
    result_holder = {}
    async for chunk in agent.astream(
        user_id, session_id, "Hello! I had a great day today.", result_holder
    ):
        chunks.append(chunk)
        
    full_text = "".join(chunks)
    assert len(full_text) > 0
    # Crucial assertion: Must NOT be wrapped in JSON schema strings
    assert '"response":' not in full_text
    assert '"extracted_facts":' not in full_text
    assert '"mood":' not in full_text


@pytest.mark.asyncio
async def test_background_profiler_structured_extraction():
    """Verify that the background profiler accurately extracts facts and mood scores."""
    graph = await get_mood_graph()
    user_id = uuid4()
    session_id = uuid4()
    
    user_message = "I just got a promotion to Lead Engineer and adopted a puppy named Cooper!"
    assistant_response = "Congratulations on your promotion! And Cooper sounds like an absolute bundle of joy."
    
    profile = await graph.profile_conversation_async(
        user_id, session_id, user_message, assistant_response
    )
    
    assert isinstance(profile, dict)
    assert "save" in profile
    assert "mood" in profile
    assert "mood_score" in profile
    assert "extracted_facts" in profile
    assert profile["save"] is True
    assert 1 <= profile["mood_score"] <= 10


if __name__ == "__main__":
    print("Running adk hybrid tests directly...")
    asyncio.run(test_google_adk_agent_definition())
    asyncio.run(test_deterministic_safety_gate())
    asyncio.run(test_pure_markdown_streaming_crisis_response())
    asyncio.run(test_pure_markdown_streaming_conversational())
    print("All direct tests completed successfully!")
