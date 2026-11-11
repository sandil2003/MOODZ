"""Google ADK agent definition and tools for the Mood Agent with AgentOps tracing."""

import logging
from typing import Dict, Any, List, Union
from uuid import UUID
from sqlalchemy import select, desc
from google.adk.agents import Agent

from config import settings
from app.database import AsyncSessionLocal
from app.models import UserFact, MoodHistory
from app.core.telemetry import trace_tool
from app.services.crisis_detector import CrisisDetector
from app.services.session_manager import get_session_manager
from app.services.vector_service import get_vector_service_gemini

logger = logging.getLogger(__name__)


def _to_uuid(val: Union[str, UUID]) -> UUID:
    """Helper to convert string or UUID to a valid UUID object."""
    return UUID(str(val)) if not isinstance(val, UUID) else val


# ============================================================================
# 1. Safety Tools
# ============================================================================

@trace_tool("check_crisis_tool")
async def check_crisis_tool(message: str) -> Dict[str, Any]:
    """Check user message for immediate self-harm, suicidal ideation, or crisis risk."""
    return await CrisisDetector().check_crisis(message)


# ============================================================================
# 2. Context Retrieval Tools
# ============================================================================

@trace_tool("get_user_profile_tool")
async def get_user_profile_tool(user_id: Union[str, UUID]) -> Dict[str, Any]:
    """Retrieve known personal facts and past mood trends for a user from PostgreSQL."""
    uid = _to_uuid(user_id)
    try:
        async with AsyncSessionLocal() as db:
            fact_rows = await db.execute(
                select(UserFact).where(UserFact.user_id == uid).order_by(desc(UserFact.created_at)).limit(10)
            )
            mood_rows = await db.execute(
                select(MoodHistory).where(MoodHistory.user_id == uid).order_by(desc(MoodHistory.created_at)).limit(5)
            )

            facts = [f"[{f.category}] {f.fact_text}" for f in fact_rows.scalars().all()]
            moods = [f"{m.sentiment_label} (score: {m.mood_score}/10): {m.summary[:80]}" for m in mood_rows.scalars().all()]
            return {"facts": facts, "recent_moods": moods}
    except Exception as e:
        logger.error(f"Error in get_user_profile_tool: {e}")
        return {"facts": [], "recent_moods": []}


@trace_tool("search_past_memories_tool")
async def search_past_memories_tool(user_id: Union[str, UUID], query: str) -> List[Dict[str, Any]]:
    """Search user's past experiences and memories via Pinecone semantic search."""
    try:
        vs = get_vector_service_gemini()
        return await vs.similarity_search(query=query, user_id=_to_uuid(user_id), k=3)
    except Exception as e:
        logger.error(f"Error in search_past_memories_tool: {e}")
        return []


@trace_tool("get_recent_history_tool")
async def get_recent_history_tool(session_id: Union[str, UUID], limit: int = 5) -> List[Dict[str, Any]]:
    """Retrieve recent chat messages for an active session from Redis."""
    try:
        sm = await get_session_manager()
        return await sm.get_recent_history(_to_uuid(session_id), limit=limit)
    except Exception as e:
        logger.error(f"Error in get_recent_history_tool: {e}")
        return []


@trace_tool("retrieve_user_context_tool")
async def retrieve_user_context_tool(
    user_id: Union[str, UUID],
    session_id: Union[str, UUID],
    query: str
) -> Dict[str, Any]:
    """Retrieve aggregated short-term chat history and semantic memories."""
    return {
        "recent_history": await get_recent_history_tool(session_id, limit=5),
        "semantic_memories": await search_past_memories_tool(user_id, query)
    }


# ============================================================================
# 3. Persistence Tools
# ============================================================================

@trace_tool("persist_user_facts_tool")
async def persist_user_facts_tool(user_id: Union[str, UUID], facts: List[str]) -> bool:
    """Persist newly extracted personal facts into PostgreSQL and Pinecone."""
    if not facts:
        return True

    uid = _to_uuid(user_id)
    try:
        # 1. Save facts to PostgreSQL
        async with AsyncSessionLocal() as db:
            for text in facts:
                db.add(UserFact(user_id=uid, fact_text=text, category="auto_extracted", source="adk_profiler"))
            await db.commit()

        # 2. Save facts to Pinecone vector store
        vs = get_vector_service_gemini()
        for text in facts:
            await vs.add_text(user_id=uid, text=text, data_type="user_fact", source="adk_profiler")
        return True
    except Exception as e:
        logger.error(f"Error in persist_user_facts_tool: {e}")
        return False


@trace_tool("persist_mood_entry_tool")
async def persist_mood_entry_tool(
    user_id: Union[str, UUID],
    session_id: Union[str, UUID],
    mood_label: str,
    mood_score: int,
    summary: str
) -> bool:
    """Record sentiment analysis and numerical mood score into PostgreSQL."""
    try:
        async with AsyncSessionLocal() as db:
            db.add(MoodHistory(
                user_id=_to_uuid(user_id),
                session_id=_to_uuid(session_id),
                sentiment_label=mood_label,
                mood_score=mood_score,
                summary=summary
            ))
            await db.commit()
        return True
    except Exception as e:
        logger.error(f"Error in persist_mood_entry_tool: {e}")
        return False


# ============================================================================
# 4. Google ADK Agent Declaration
# ============================================================================

MOOD_AGENT_INSTRUCTION = """You are MOODZ, an empathetic, caring, and thoughtful AI mental wellness companion.
Your primary mission is to provide warm, validating, non-judgmental emotional support, promote healthy reflection,
and help users navigate their mental wellness journey.

Guidelines:
1. Always validate emotions before offering perspectives or coping strategies.
2. Speak in a comforting, human-like voice. Use formatting (bullet points, line breaks) thoughtfully.
3. If the user is in severe distress or mentions self-harm, immediately check for crisis.
4. Integrate the user's personal context, past conversations, and known facts naturally into your dialogue.
"""

mood_adk_agent = Agent(
    name="mood_agent",
    model=settings.gemini_model,
    description="Empathetic mental wellness companion that provides emotional support, crisis detection, and mood tracking.",
    instruction=MOOD_AGENT_INSTRUCTION,
    tools=[
        check_crisis_tool,
        get_user_profile_tool,
        search_past_memories_tool,
        get_recent_history_tool,
        persist_user_facts_tool,
        persist_mood_entry_tool,
        retrieve_user_context_tool
    ]
)


def get_mood_adk_agent() -> Agent:
    """Returns the Google ADK Mood Agent instance."""
    return mood_adk_agent
