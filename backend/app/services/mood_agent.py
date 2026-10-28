"""Empathetic Mood Agent Service.

Adapter layer delegating execution to the LangGraph Hybrid Engine (MoodHybridGraph)
and Google ADK, preserving backward compatibility for existing routes and callers.
"""

from typing import List, Dict, Any, Optional, AsyncGenerator
from uuid import UUID
from pydantic import BaseModel, Field

from config import settings
from app.services.session_manager import SessionManager, get_session_manager
from app.services.vector_service import VectorService, get_vector_service_gemini
from app.services.crisis_detector import CrisisDetector
from app.services.fallback_mocks import API_ERROR_WARNING
from app.services.mood_graph import MoodHybridGraph, get_mood_graph, ProfileAnalysisResult


class MoodzAgentOutput(BaseModel):
    """
    Combined Pydantic schema for empathetic wellness response and conversation classification.
    Maintained for backwards compatibility.
    """
    response: str = Field(
        description="Your warm, empathetic response message to the user."
    )
    save: bool = Field(
        description="Set to true if the user's message contains meaningful personal facts, goals, or strong emotional shifts. Set to false for casual greetings, small talk, test messages, or generic chatter."
    )
    extracted_facts: List[str] = Field(
        default_factory=list,
        description="Extract new personal facts about the user (e.g. hobbies, family members, jobs, events). Return empty list if no new facts are shared."
    )
    mood: str = Field(
        description="Detected mood/emotion of the user's current message (e.g. happy, sad, anxious, excited, calm, neutral)"
    )


class MoodAgentChainV2:
    """
    Empathetic Mood Agent powered by the LangGraph Hybrid Engine.
    Provides fast foreground pure-Markdown streaming and asynchronous background intelligence profiling.
    """
    def __init__(
        self,
        session_manager: SessionManager,
        vector_service: VectorService,
        crisis_detector: CrisisDetector,
        model: Optional[str] = None
    ):
        self.session_manager = session_manager
        self.vector_service = vector_service
        self.crisis_detector = crisis_detector
        self._graph: Optional[MoodHybridGraph] = None
        
    async def _get_graph(self) -> MoodHybridGraph:
        if self._graph is None:
            self._graph = await get_mood_graph()
        return self._graph

    async def invoke(
        self,
        user_id: UUID,
        session_id: UUID,
        user_message: str,
        result_holder: Optional[dict] = None
    ) -> str:
        """Execute chat turn synchronously using the compiled LangGraph."""
        if result_holder is None:
            result_holder = {}
        graph = await self._get_graph()
        return await graph.ainvoke_chat(user_id, session_id, user_message, result_holder)

    async def astream(
        self,
        user_id: UUID,
        session_id: UUID,
        user_message: str,
        result_holder: Optional[dict] = None
    ) -> AsyncGenerator[str, None]:
        """
        Fast Foreground Stream:
        Yields pure Markdown tokens progressively directly to SSE.
        Populates result_holder with full response and context metadata.
        """
        if result_holder is None:
            result_holder = {}
        graph = await self._get_graph()
        async for chunk in graph.astream_chat(user_id, session_id, user_message, result_holder):
            yield chunk


_mood_agent: Optional[MoodAgentChainV2] = None


async def get_mood_agent() -> MoodAgentChainV2:
    """Returns the singleton MoodAgentChainV2 instance."""
    global _mood_agent
    if _mood_agent is None:
        sm = await get_session_manager()
        vs = get_vector_service_gemini()
        cd = CrisisDetector()
        _mood_agent = MoodAgentChainV2(session_manager=sm, vector_service=vs, crisis_detector=cd)
    return _mood_agent
