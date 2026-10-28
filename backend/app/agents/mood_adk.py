"""Google ADK agent definition and tools for the Mood Agent with AgentOps tracing."""

from typing import Dict, Any, List, Optional
from google.adk.agents import Agent
from config import settings
from app.services.crisis_detector import CrisisDetector
from app.services.session_manager import get_session_manager
from app.services.vector_service import get_vector_service_gemini
from app.database import AsyncSessionLocal
from app.models import UserFact, MoodHistory
from app.core.telemetry import trace_tool
from uuid import UUID


# ==========================================
# Google ADK Tool Definitions (with AgentOps Tracing)
# ==========================================

@trace_tool("check_crisis_tool")
async def check_crisis_tool(message: str) -> Dict[str, Any]:
    """Check user message for immediate self-harm, suicidal ideation, or mental health emergency.
    
    Args:
        message: The text content of the user's message.
        
    Returns:
        dict: Evaluation containing 'type' ('immediate_risk' or 'none') and 'score' (1.0 or 0.0).
    """
    detector = CrisisDetector()
    return await detector.check_crisis(message)


@trace_tool("retrieve_user_context_tool")
async def retrieve_user_context_tool(user_id: str, session_id: str, query: str) -> Dict[str, Any]:
    """Retrieve multi-tier context for the user: short-term chat, semantic memory, and facts.
    
    Args:
        user_id: The UUID string of the user.
        session_id: The UUID string of the active chat session.
        query: The user's query or message for semantic similarity search.
        
    Returns:
        dict: Aggregated context containing recent_history, semantic_memories, and profile facts.
    """
    sm = await get_session_manager()
    vs = get_vector_service_gemini()
    
    uid = UUID(user_id) if isinstance(user_id, str) else user_id
    sid = UUID(session_id) if isinstance(session_id, str) else session_id
    
    recent_history = await sm.get_recent_history(sid, limit=5)
    semantic_results = await vs.similarity_search(query=query, user_id=uid, k=2)
    
    return {
        "recent_history": recent_history,
        "semantic_memories": semantic_results
    }


@trace_tool("persist_user_facts_tool")
async def persist_user_facts_tool(user_id: str, facts: List[str]) -> bool:
    """Persist newly extracted personal facts about the user into PostgreSQL and Pinecone.
    
    Args:
        user_id: The UUID string of the user.
        facts: List of extracted personal facts.
        
    Returns:
        bool: True if facts were saved successfully.
    """
    if not facts:
        return True
        
    uid = UUID(user_id) if isinstance(user_id, str) else user_id
    vs = get_vector_service_gemini()
    
    try:
        async with AsyncSessionLocal() as db:
            for fact_text in facts:
                db_fact = UserFact(
                    user_id=uid,
                    fact_text=fact_text,
                    category="auto_extracted",
                    source="adk_profiler"
                )
                db.add(db_fact)
            await db.commit()
            
        for fact_text in facts:
            await vs.add_text(
                user_id=uid,
                text=fact_text,
                data_type="user_fact",
                source="adk_profiler"
            )
        return True
    except Exception as e:
        print(f"Error in persist_user_facts_tool: {e}")
        return False


@trace_tool("persist_mood_entry_tool")
async def persist_mood_entry_tool(
    user_id: str,
    session_id: str,
    mood_label: str,
    mood_score: int,
    summary: str
) -> bool:
    """Record a sentiment analysis and numerical mood score entry into PostgreSQL.
    
    Args:
        user_id: The UUID string of the user.
        session_id: The UUID string of the session.
        mood_label: The emotional state label (e.g., happy, sad, anxious, calm).
        mood_score: Integer wellness rating from 1 (severe distress) to 10 (euphoric).
        summary: Brief summary or the user's message triggering this score.
        
    Returns:
        bool: True if mood entry was recorded successfully.
    """
    uid = UUID(user_id) if isinstance(user_id, str) else user_id
    sid = UUID(session_id) if isinstance(session_id, str) else session_id
    
    try:
        async with AsyncSessionLocal() as db:
            entry = MoodHistory(
                user_id=uid,
                session_id=sid,
                sentiment_label=mood_label,
                mood_score=mood_score,
                summary=summary
            )
            db.add(entry)
            await db.commit()
        return True
    except Exception as e:
        print(f"Error in persist_mood_entry_tool: {e}")
        return False


# ==========================================
# Google ADK Mood Agent Declaration
# ==========================================

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
        retrieve_user_context_tool,
        persist_user_facts_tool,
        persist_mood_entry_tool
    ]
)


def get_mood_adk_agent() -> Agent:
    """Returns the Google ADK Mood Agent instance."""
    return mood_adk_agent
