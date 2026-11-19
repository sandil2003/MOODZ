"""Test on-demand tools refactor for LangGraph and Google ADK."""

import sys
import os
import asyncio
from uuid import uuid4
import pytest

# Add backend directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.agents.mood_adk import (
    mood_adk_agent,
    get_user_profile_tool,
    search_past_memories_tool,
    get_recent_history_tool,
    retrieve_user_context_tool
)
from app.services.mood_graph import get_mood_graph


@pytest.mark.asyncio
async def test_langgraph_lean_prompt_and_tools():
    """Verify that LangGraph context_ingestion_node creates a lean prompt without data dumps, and has the 3 tools."""
    graph = await get_mood_graph()
    user_id = uuid4()
    session_id = uuid4()

    state = {
        "user_id": user_id,
        "session_id": session_id,
        "user_message": "Hello MOODZ, how are you today?"
    }

    # 1. Test lean context ingestion
    context_output = await graph.context_ingestion_node(state)
    system_prompt = context_output["system_prompt"]

    # Verify that bulky sections are NOT present in the system prompt
    assert "=== USER PROFILE ===" not in system_prompt
    assert "=== LONG-TERM MEMORIES" not in system_prompt
    assert "=== RECENT CONVERSATION HISTORY ===" not in system_prompt
    assert "{profile_str}" not in system_prompt
    assert "{semantic_str}" not in system_prompt
    assert "{history_str}" not in system_prompt

    # Verify that the system prompt informs the LLM about the on-demand tools
    assert "get_user_profile" in system_prompt
    assert "search_past_memories" in system_prompt
    assert "get_recent_conversation_history" in system_prompt

    # 2. Test tool creation
    tools = graph._get_companion_tools(user_id, session_id)
    assert len(tools) == 3
    tool_names = [t.name for t in tools]
    assert "get_user_profile" in tool_names
    assert "search_past_memories" in tool_names
    assert "get_recent_conversation_history" in tool_names

    # 3. Test running tools through the tool executor
    tools_map = {t.name: t for t in tools}
    
    # Test profile tool call
    profile_tc = {"name": "get_user_profile", "args": {}}
    profile_res = await graph._execute_tool_call(profile_tc, tools_map)
    assert isinstance(profile_res, str)
    assert len(profile_res) > 0

    # Test history tool call
    history_tc = {"name": "get_recent_conversation_history", "args": {"limit": 3}}
    history_res = await graph._execute_tool_call(history_tc, tools_map)
    assert isinstance(history_res, str)
    assert len(history_res) > 0

    print("[OK] LangGraph lean prompt and on-demand tools verified!")


@pytest.mark.asyncio
async def test_google_adk_tools():
    """Verify Google ADK agent registers separate tools for profile, memories, and history."""
    tool_funcs = [t if callable(t) else getattr(t, "func", None) for t in mood_adk_agent.tools]
    tool_names = [getattr(t, "__name__", str(t)) for t in mood_adk_agent.tools]

    # Verify all tools exist in the ADK agent
    assert any("get_user_profile_tool" in name for name in tool_names)
    assert any("search_past_memories_tool" in name for name in tool_names)
    assert any("get_recent_history_tool" in name for name in tool_names)

    # Test executing ADK tools
    test_uid = str(uuid4())
    test_sid = str(uuid4())

    profile_data = await get_user_profile_tool(test_uid)
    assert "facts" in profile_data
    assert "recent_moods" in profile_data

    history_data = await get_recent_history_tool(test_sid, limit=5)
    assert isinstance(history_data, list)

    print("[OK] Google ADK on-demand tools verified!")


async def main():
    print("Running on-demand tools tests...")
    await test_langgraph_lean_prompt_and_tools()
    await test_google_adk_tools()
    print("ALL TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(main())
