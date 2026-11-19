"""Empathetic Mood Agent Service.

Adapter layer delegating execution to the LangGraph Hybrid Engine (MoodHybridGraph),
preserving backward compatibility for legacy routes and callers.
"""

from typing import List, Optional, AsyncGenerator
from uuid import UUID
from pydantic import BaseModel, Field

from app.services.session_manager import SessionManager, get_session_manager
from app.services.vector_service import VectorService, get_vector_service_gemini
from app.services.crisis_detector import CrisisDetector
from app.services.mood_graph import MoodHybridGraph, get_mood_graph, ProfileAnalysisResult


class MoodzAgentOutput(BaseModel):
    """Legacy Pydantic schema for empathetic wellness response and conversation classification."""
    response: str = Field(description="Warm, empathetic response message to the user.")
    save: bool = Field(description="Set to true if user message contains personal facts or strong emotional shifts.")
    extracted_facts: List[str] = Field(default_factory=list, description="Extracted personal facts about the user.")
    mood: str = Field(description="Detected emotional state of the user.")


class MoodAgentChainV2:
    """Adapter class wrapping MoodHybridGraph to maintain existing API contracts."""

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
        """Stream Markdown tokens progressively via Server-Sent Events."""
        if result_holder is None:
            result_holder = {}
        graph = await self._get_graph()
        async for chunk in graph.astream_chat(user_id, session_id, user_message, result_holder):
            yield chunk


_mood_agent: Optional[MoodAgentChainV2] = None


async def get_mood_agent() -> MoodAgentChainV2:
    """Returns the singleton MoodAgentChainV2 adapter instance."""
    global _mood_agent
    if _mood_agent is None:
        sm = await get_session_manager()
        vs = get_vector_service_gemini()
        cd = CrisisDetector()
        _mood_agent = MoodAgentChainV2(session_manager=sm, vector_service=vs, crisis_detector=cd)
    return _mood_agent
