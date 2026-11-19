"""LangGraph Hybrid Execution Engine for the Mood Agent.

Coordinates:
1. Fast Foreground Path:
   - Deterministic safety gating (regex crisis detection short-circuit).
   - Lean context ingestion with 3 on-demand dynamic tools.
   - Empathetic companion streaming yielding pure Markdown tokens over SSE.
2. Asynchronous Background Sub-Agent:
   - Post-stream clinical intelligence analysis for personal facts and mood scoring.
   - Non-blocking persistence to PostgreSQL and Pinecone.
"""

import json
import time
import asyncio
import logging
from typing import TypedDict, List, Dict, Any, Optional, AsyncGenerator, Tuple
from uuid import UUID
from pydantic import BaseModel, Field

# LangGraph Core
from langgraph.graph import StateGraph, START, END

# LangChain LLMs & Tools
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langchain_core.messages import ToolMessage
from sqlalchemy import select, desc

from config import settings
from app.database import AsyncSessionLocal
from app.models import MoodHistory, UserFact
from app.core.telemetry import trace_span, record_llm_metrics
from app.core.pii_scrubber import PIIScrubber
from app.services.fallback_mocks import API_ERROR_WARNING, generate_mock_wellness_response, mock_classify
from app.services.custom_model import get_custom_model
from app.services.session_manager import SessionManager, get_session_manager
from app.services.vector_service import VectorService, get_vector_service_gemini
from app.services.crisis_detector import CrisisDetector

logger = logging.getLogger(__name__)


def normalize_text(content: Any) -> str:
    """Normalize LLM output into a clean string representation."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in content
        )
    return str(content)


# ============================================================================
# 1. State & Output Schema Definitions
# ============================================================================

class MoodHybridState(TypedDict, total=False):
    """LangGraph state schema representing a single conversation turn."""
    user_id: UUID
    session_id: UUID
    user_message: str

    # Safety
    is_crisis: bool
    crisis_response: Optional[str]

    # Context & Memory
    short_term_history: List[Dict[str, Any]]
    semantic_memories: List[Dict[str, Any]]
    user_moods: List[Dict[str, Any]]
    user_facts: List[Dict[str, Any]]

    # Prompts & Generation
    system_prompt: str
    messages: List[Dict[str, str]]
    response_text: str

    # Background Extraction
    classification: Dict[str, Any]
    error: Optional[str]


class ProfileAnalysisResult(BaseModel):
    """Structured Pydantic schema for background intelligence analysis."""
    save: bool = Field(description="Set to true if user shared meaningful emotional updates, goals, or facts.")
    mood: str = Field(description="Detected emotional tone (e.g. happy, calm, anxious, sad, neutral).")
    mood_score: int = Field(ge=1, le=10, description="Wellness/mood score from 1 (distress) to 10 (optimal).")
    extracted_facts: List[str] = Field(default_factory=list, description="New durable personal facts learned.")


# Standard emotion to numerical score fallback map
MOOD_SCORE_MAP: Dict[str, int] = {
    "happy": 8, "joyful": 9, "excited": 8, "content": 7,
    "sad": 3, "depressed": 2, "down": 3, "melancholic": 3,
    "anxious": 4, "worried": 4, "nervous": 4, "stressed": 3,
    "angry": 3, "frustrated": 4, "irritated": 4,
    "calm": 7, "peaceful": 8, "relaxed": 7,
    "neutral": 5, "confused": 5, "uncertain": 5,
    "hopeful": 7, "optimistic": 8
}

CRISIS_EMERGENCY_MESSAGE = (
    "I'm really concerned about what you're sharing. Please reach out to a mental health "
    "professional or crisis helpline immediately. You can reach the 988 Suicide & Crisis Lifeline "
    "(US/Canada by calling or texting 988), text HOME to 741741 to connect with Crisis Text Line, "
    "or contact your local emergency services."
)


# ============================================================================
# 2. MoodHybridGraph Orchestrator
# ============================================================================

class MoodHybridGraph:
    """Compiled LangGraph StateGraph engine coordinating conversational turns and profiling."""

    def __init__(
        self,
        session_manager: SessionManager,
        vector_service: VectorService,
        crisis_detector: CrisisDetector
    ):
        self.session_manager = session_manager
        self.vector_service = vector_service
        self.crisis_detector = crisis_detector

        # 1. Initialize Foreground Conversational LLM
        self.companion_llm, self.fallback_companion_llm = self._setup_companion_models()

        # 2. Initialize Background Profiler LLM (low temperature for JSON extraction)
        self.profiler_llm = ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            temperature=0.2,
            google_api_key=settings.gemini_api_key,
            response_mime_type="application/json",
            max_retries=1
        )

        # 3. Build & Compile StateGraph
        self.graph = self._build_graph()

    # ------------------------------------------------------------------------
    # Model Setup Helpers
    # ------------------------------------------------------------------------

    def _setup_companion_models(self) -> Tuple[Any, Optional[Any]]:
        """Instantiate primary conversational LLM and fallback model."""
        fallback_model = None

        if settings.use_custom_model and settings.custom_model_url:
            logger.info(f"[MoodGraph] Using custom model endpoint: {settings.custom_model_url}")
            if settings.custom_model_type == "openai":
                from langchain_openai import ChatOpenAI
                base_url = settings.custom_model_url if "/v1" in settings.custom_model_url else f"{settings.custom_model_url}/v1"
                primary_model = ChatOpenAI(
                    base_url=base_url,
                    api_key="lm-studio",
                    model="gpt-4o-mini",
                    temperature=settings.custom_model_temperature,
                    max_tokens=settings.custom_model_max_tokens,
                    timeout=settings.custom_model_timeout
                )
            else:
                primary_model = get_custom_model(
                    base_url=settings.custom_model_url,
                    temperature=settings.custom_model_temperature,
                    max_tokens=settings.custom_model_max_tokens,
                    timeout=settings.custom_model_timeout
                )

            # Prepare Gemini fallback if primary custom model is unreachable
            if settings.gemini_api_key:
                fallback_model = ChatGoogleGenerativeAI(
                    model=settings.gemini_model,
                    temperature=0.7,
                    google_api_key=settings.gemini_api_key,
                    max_retries=1
                )
        else:
            logger.info(f"[MoodGraph] Using Gemini companion model: {settings.gemini_model}")
            primary_model = ChatGoogleGenerativeAI(
                model=settings.gemini_model,
                temperature=0.7,
                google_api_key=settings.gemini_api_key,
                max_retries=1
            )

        return primary_model, fallback_model

    # ------------------------------------------------------------------------
    # LangGraph Nodes
    # ------------------------------------------------------------------------

    async def safety_gate_node(self, state: MoodHybridState) -> Dict[str, Any]:
        """Node 1 (Deterministic, 0ms): Scan for self-harm / emergency risk."""
        with trace_span("langgraph.safety_gate_node", span_type="safety.gate", attributes={"user_id": str(state.get("user_id", ""))}) as span:
            user_message = state.get("user_message", "")
            crisis_info = await self.crisis_detector.check_crisis(user_message)

            if crisis_info.get("score", 0.0) == 1.0:
                span.set_attribute("moodz.is_crisis", True)
                return {
                    "is_crisis": True,
                    "crisis_response": CRISIS_EMERGENCY_MESSAGE,
                    "response_text": CRISIS_EMERGENCY_MESSAGE
                }

            span.set_attribute("moodz.is_crisis", False)
            return {"is_crisis": False}

    async def crisis_intervention_node(self, state: MoodHybridState) -> Dict[str, Any]:
        """Node 2: Short-circuit response outputting emergency resources."""
        return {
            "response_text": state.get("crisis_response", CRISIS_EMERGENCY_MESSAGE)
        }

    async def context_ingestion_node(self, state: MoodHybridState) -> Dict[str, Any]:
        """Node 3: Assemble lean system prompt with instructions on using on-demand context tools."""
        user_id = state["user_id"]
        session_id = state["session_id"]
        user_message = state["user_message"]

        with trace_span(
            "langgraph.context_ingestion_node",
            span_type="context.ingestion",
            attributes={"user_id": str(user_id), "session_id": str(session_id)}
        ):
            system_prompt = (
                "You are MOODZ, an empathetic, caring, and thoughtful AI mental wellness companion.\n\n"
                "Your Core Guidelines:\n"
                "- Understand, validate, and support the user's emotional state with warmth, patience, and compassion.\n"
                "- Speak in a comforting, natural, human voice.\n"
                "- Output pure, formatted Markdown text (paragraphs, gentle tone, bullet points where helpful).\n"
                "- Do NOT wrap your answer in JSON, markdown code fences, or metadata tags. Speak directly to the user.\n"
                "- On-Demand Context Tools:\n"
                "  * Call `get_user_profile()` to retrieve known user facts, preferences, and recent emotional trends.\n"
                "  * Call `search_past_memories(query)` to search past experiences, check-ins, or topics mentioned in past sessions.\n"
                "  * Call `get_recent_conversation_history(limit)` to review earlier messages from the active session.\n"
                "  * Call these tools ONLY when you genuinely need background context or history. "
                "If the user's message is self-contained, a casual greeting, or simple conversation, respond directly to save time and tokens."
            )

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]

            return {
                "system_prompt": system_prompt,
                "messages": messages,
                "short_term_history": [],
                "semantic_memories": [],
                "user_moods": [],
                "user_facts": []
            }

    async def companion_node(self, state: MoodHybridState) -> Dict[str, Any]:
        """Node 4: Non-streaming companion invocation with on-demand tool execution."""
        messages = list(state.get("messages", []))
        user_id = state["user_id"]
        session_id = state["session_id"]
        tools = self._get_companion_tools(user_id, session_id)
        tools_map = {t.name: t for t in tools}

        try:
            llm_to_use = self.companion_llm
            try:
                llm_with_tools = llm_to_use.bind_tools(tools)
                response = await llm_with_tools.ainvoke(messages)
            except Exception as bind_err:
                logger.debug(f"[MoodGraph] Tool binding fallback in companion_node: {bind_err}")
                response = await llm_to_use.ainvoke(messages)

            if hasattr(response, "tool_calls") and response.tool_calls:
                messages.append(response)
                for tc in response.tool_calls:
                    tool_result = await self._execute_tool_call(tc, tools_map)
                    messages.append(ToolMessage(content=tool_result, tool_call_id=tc.get("id", "")))
                final_resp = await llm_to_use.ainvoke(messages)
                text = normalize_text(getattr(final_resp, "content", str(final_resp)))
            else:
                text = normalize_text(getattr(response, "content", str(response)))

            return {"response_text": text}
        except Exception as e:
            logger.error(f"[MoodGraph] Error in companion invocation: {e}")
            if self.fallback_companion_llm:
                try:
                    logger.info("[MoodGraph] Fallback to Gemini companion model...")
                    response = await self.fallback_companion_llm.ainvoke(messages)
                    return {"response_text": normalize_text(getattr(response, "content", str(response)))}
                except Exception as fb_err:
                    logger.error(f"[MoodGraph] Fallback companion also failed: {fb_err}")

            mock_text = generate_mock_wellness_response(state.get("user_message", ""))
            return {"response_text": API_ERROR_WARNING + mock_text}

    # ------------------------------------------------------------------------
    # On-Demand Tool Construction
    # ------------------------------------------------------------------------

    def _get_companion_tools(self, user_id: UUID, session_id: UUID) -> List[Any]:
        """Construct the 3 on-demand context retrieval tools for the companion LLM."""
        @tool
        async def get_user_profile() -> str:
            """Retrieve known personal facts and past mood trends about the user from the database."""
            try:
                moods, facts = await self._fetch_db_profile(user_id)
                parts = []
                if moods:
                    parts.append("Recent Mood History:")
                    for m in moods:
                        parts.append(f"- {m.sentiment_label} (score: {m.mood_score}/10): {m.summary[:100]}")
                if facts:
                    parts.append("Known Facts about User:")
                    for f in facts:
                        parts.append(f"- [{f.category}] {f.fact_text}")
                return "\n".join(parts) if parts else "No structured profile recorded yet."
            except Exception as e:
                return f"Error fetching profile: {e}"

        @tool
        async def search_past_memories(query: str) -> str:
            """Search the user's past experiences and episodic memories using semantic search."""
            try:
                memories = await self.vector_service.similarity_search(query=query, user_id=user_id, k=3)
                if not memories:
                    return "No related past experiences found."
                formatted = []
                for res in memories:
                    meta = res.get("metadata", {})
                    formatted.append(f"- [{meta.get('data_type', 'experience')}] {res.get('text', '')} (mood: {meta.get('mood_label', 'N/A')})")
                return "\n".join(formatted)
            except Exception as e:
                return f"Error searching past memories: {e}"

        @tool
        async def get_recent_conversation_history(limit: int = 5) -> str:
            """Retrieve recent messages from the current conversation session from Redis."""
            try:
                history = await self.session_manager.get_recent_history(session_id, limit=limit)
                if not history:
                    return "First message in this session."
                formatted = [f"{msg.get('role', 'user').upper()}: {msg.get('content', '')}" for msg in history]
                return "\n".join(formatted)
            except Exception as e:
                return f"Error fetching conversation history: {e}"

        return [get_user_profile, search_past_memories, get_recent_conversation_history]

    async def _execute_tool_call(self, tool_call: Dict[str, Any], tools_map: Dict[str, Any]) -> str:
        """Execute a tool called by the LLM."""
        name = tool_call.get("name")
        args = tool_call.get("args", {})
        if name in tools_map:
            try:
                res = await tools_map[name].ainvoke(args)
                return str(res)
            except Exception as e:
                return f"Error running {name}: {e}"
        return f"Unknown tool: {name}"

    # ------------------------------------------------------------------------
    # Graph Construction & Routing
    # ------------------------------------------------------------------------

    def _route_after_safety(self, state: MoodHybridState) -> str:
        """Route to crisis intervention if risk detected, else proceed to context ingestion."""
        if state.get("is_crisis", False):
            return "crisis_intervention_node"
        return "context_ingestion_node"

    def _build_graph(self):
        """Construct and compile the LangGraph StateGraph."""
        builder = StateGraph(MoodHybridState)

        # Add Nodes
        builder.add_node("safety_gate_node", self.safety_gate_node)
        builder.add_node("crisis_intervention_node", self.crisis_intervention_node)
        builder.add_node("context_ingestion_node", self.context_ingestion_node)
        builder.add_node("companion_node", self.companion_node)

        # Add Edges & Conditional Routing
        builder.add_edge(START, "safety_gate_node")
        builder.add_conditional_edges(
            "safety_gate_node",
            self._route_after_safety,
            {
                "crisis_intervention_node": "crisis_intervention_node",
                "context_ingestion_node": "context_ingestion_node"
            }
        )
        builder.add_edge("crisis_intervention_node", END)
        builder.add_edge("context_ingestion_node", "companion_node")
        builder.add_edge("companion_node", END)

        return builder.compile()

    # ------------------------------------------------------------------------
    # Persistence Helpers
    # ------------------------------------------------------------------------

    async def _fetch_db_profile(self, user_id: UUID) -> Tuple[List[MoodHistory], List[UserFact]]:
        """Fetch last 3 moods and last 5 facts from PostgreSQL."""
        async with AsyncSessionLocal() as db:
            mood_res = await db.execute(
                select(MoodHistory).where(MoodHistory.user_id == user_id).order_by(desc(MoodHistory.created_at)).limit(3)
            )
            fact_res = await db.execute(
                select(UserFact).where(UserFact.user_id == user_id).order_by(desc(UserFact.created_at)).limit(5)
            )
            return mood_res.scalars().all(), fact_res.scalars().all()

    async def _persist_profiler_results(
        self,
        user_id: UUID,
        session_id: UUID,
        user_message: str,
        assistant_response: str,
        classification: Dict[str, Any]
    ) -> None:
        """Persist extracted facts, sentiment, and check-in entries into Pinecone and PostgreSQL."""
        if not classification.get("save", False):
            return

        # 1. Pinecone Vector Storage
        try:
            await self.vector_service.add_text(
                user_id=user_id,
                text=user_message,
                data_type="mood_checkin",
                source="typing",
                mood_label=classification["mood"],
                context_id=str(session_id)
            )
            await self.vector_service.add_text(
                user_id=user_id,
                text=assistant_response,
                data_type="text",
                source="assistant",
                context_id=str(session_id)
            )
            for fact in classification.get("extracted_facts", []):
                await self.vector_service.add_text(
                    user_id=user_id,
                    text=fact,
                    data_type="user_fact",
                    source="adk_profiler",
                    context_id=str(session_id),
                    additional_info={"category": "auto_extracted"}
                )
        except Exception as pe:
            logger.warning(f"[BackgroundProfiler] Pinecone persistence note: {pe}")

        # 2. PostgreSQL Relational Storage
        try:
            async with AsyncSessionLocal() as db:
                for fact in classification.get("extracted_facts", []):
                    db.add(UserFact(
                        user_id=user_id,
                        fact_text=PIIScrubber.scrub_text(fact),
                        category="auto_extracted",
                        source="adk_profiler"
                    ))
                if classification.get("mood", "neutral") != "neutral":
                    db.add(MoodHistory(
                        user_id=user_id,
                        session_id=session_id,
                        sentiment_label=classification["mood"],
                        mood_score=classification["mood_score"],
                        summary=PIIScrubber.scrub_text(user_message[:255])
                    ))
                await db.commit()
        except Exception as dbe:
            logger.error(f"[BackgroundProfiler] PostgreSQL persistence error: {dbe}")

    # ------------------------------------------------------------------------
    # Asynchronous Background Profiler
    # ------------------------------------------------------------------------

    async def profile_conversation_async(
        self,
        user_id: UUID,
        session_id: UUID,
        user_message: str,
        assistant_response: str
    ) -> Dict[str, Any]:
        """Asynchronous non-blocking sub-agent analyzing user sentiment and facts."""
        with trace_span(
            "langgraph.profile_conversation_async",
            span_type="profiler.async",
            attributes={"user_id": str(user_id), "session_id": str(session_id)}
        ) as profiler_span:

            profiler_prompt = (
                "You are a clinical wellness profiling sub-agent.\n"
                "Analyze the following conversation turn between a user and an empathetic companion:\n\n"
                f'USER: "{user_message}"\n'
                f'ASSISTANT: "{assistant_response}"\n\n'
                "Extract the following in strict JSON:\n"
                "{\n"
                '  "save": true or false, // Set to true ONLY if the USER\'s message contains personal facts, life events, goals, or notable emotional shifts. Set to false for small talk, greetings, or casual remarks.\n'
                '  "mood": "Detected emotion (e.g. happy, joyful, calm, anxious, stressed, sad, angry, neutral)",\n'
                '  "mood_score": 1 to 10, // Wellness score from 1 (severe distress) to 10 (joyful/optimal)\n'
                '  "extracted_facts": ["Fact 1", "Fact 2"] // New personal facts learned ONLY about the user (e.g. job, family, pets, hobbies). Empty list if none.\n'
                "}"
            )

            try:
                llm_response = await self.profiler_llm.ainvoke([
                    {"role": "system", "content": "You are a clinical data extraction sub-agent. Respond only in strict JSON."},
                    {"role": "user", "content": profiler_prompt}
                ])
                raw_text = getattr(llm_response, "content", str(llm_response))
                cleaned = raw_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                data = json.loads(cleaned)

                mood = str(data.get("mood", "neutral")).lower()
                mood_score = max(1, min(10, int(data.get("mood_score", MOOD_SCORE_MAP.get(mood, 5)))))

                classification = {
                    "save": bool(data.get("save", False)),
                    "mood": mood,
                    "mood_score": mood_score,
                    "extracted_facts": list(data.get("extracted_facts", []))
                }
            except Exception as e:
                logger.debug(f"[BackgroundProfiler] Fallback to rule classifier ({e})")
                fb = mock_classify(user_message)
                fb_mood = fb.get("mood", "neutral").lower()
                classification = {
                    "save": fb.get("save", False),
                    "mood": fb_mood,
                    "mood_score": MOOD_SCORE_MAP.get(fb_mood, 5),
                    "extracted_facts": fb.get("extracted_facts", [])
                }

            profiler_span.set_attribute("moodz.classified_mood", classification.get("mood", ""))
            profiler_span.set_attribute("moodz.mood_score", classification.get("mood_score", 0))
            profiler_span.set_attribute("moodz.facts_count", len(classification.get("extracted_facts", [])))
            profiler_span.set_attribute("moodz.save_flag", classification.get("save", False))

            # Non-blocking async persistence
            await self._persist_profiler_results(user_id, session_id, user_message, assistant_response, classification)
            return classification

    # ------------------------------------------------------------------------
    # Public Chat Interfaces
    # ------------------------------------------------------------------------

    async def astream_chat(
        self,
        user_id: UUID,
        session_id: UUID,
        user_message: str,
        result_holder: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[str, None]:
        """Fast Foreground Pure-Markdown Streaming Interface with on-demand tool execution."""
        if result_holder is None:
            result_holder = {}

        initial_state: MoodHybridState = {
            "user_id": user_id,
            "session_id": session_id,
            "user_message": user_message
        }

        # Step 1: Safety Gate Check
        safety_output = await self.safety_gate_node(initial_state)
        if safety_output.get("is_crisis", False):
            yield "CRISIS"
            return

        # Step 2: Context Ingestion
        context_output = await self.context_ingestion_node(initial_state)
        messages = list(context_output.get("messages", []))
        tools = self._get_companion_tools(user_id, session_id)
        tools_map = {t.name: t for t in tools}

        # Step 3: Progressive SSE Streaming
        full_response = ""
        ttft_recorded = False
        stream_start = time.perf_counter()

        with trace_span("langgraph.astream_companion", span_type="llm.stream", attributes={"user_id": str(user_id)}) as stream_span:
            try:
                llm_to_use = self.companion_llm
                try:
                    target_streamer = llm_to_use.bind_tools(tools)
                except Exception:
                    target_streamer = llm_to_use

                detected_tool_calls: List[Dict[str, Any]] = []

                async for chunk in target_streamer.astream(messages):
                    if getattr(chunk, "tool_calls", None):
                        detected_tool_calls.extend(chunk.tool_calls)
                    elif getattr(chunk, "tool_call_chunks", None) and any(tc.get("name") for tc in chunk.tool_call_chunks):
                        for tc in chunk.tool_call_chunks:
                            if tc.get("name"):
                                detected_tool_calls.append(tc)

                    token = normalize_text(getattr(chunk, "content", str(chunk)))
                    if token and not detected_tool_calls:
                        if not ttft_recorded:
                            stream_span.set_attribute("moodz.ttft_ms", (time.perf_counter() - stream_start) * 1000)
                            ttft_recorded = True
                        full_response += token
                        yield token

                # If the LLM requested on-demand context tools
                if detected_tool_calls:
                    for tc in detected_tool_calls:
                        tool_result = await self._execute_tool_call(tc, tools_map)
                        messages.append(ToolMessage(content=tool_result, tool_call_id=tc.get("id", "")))

                    async for chunk in llm_to_use.astream(messages):
                        if not ttft_recorded:
                            stream_span.set_attribute("moodz.ttft_ms", (time.perf_counter() - stream_start) * 1000)
                            ttft_recorded = True
                        token = normalize_text(getattr(chunk, "content", str(chunk)))
                        if token:
                            full_response += token
                            yield token

            except Exception as e:
                logger.error(f"[MoodGraph] Error streaming companion: {e}")
                fallback_success = False

                if self.fallback_companion_llm:
                    try:
                        logger.info("[MoodGraph] Fallback stream to Gemini...")
                        async for chunk in self.fallback_companion_llm.astream(messages):
                            token = normalize_text(getattr(chunk, "content", str(chunk)))
                            if token:
                                full_response += token
                                yield token
                        fallback_success = True
                    except Exception as fb_err:
                        logger.error(f"[MoodGraph] Fallback stream failed: {fb_err}")

                if not fallback_success:
                    yield API_ERROR_WARNING
                    mock_text = generate_mock_wellness_response(user_message)
                    full_response = mock_text
                    for word in mock_text.split():
                        yield " " + word
                        await asyncio.sleep(0.04)

            finally:
                stream_span.set_attribute("moodz.response_len", len(full_response))
                input_chars = sum(len(m.get("content", "")) for m in messages if isinstance(m, dict))
                model_name = getattr(self.companion_llm, "model_name", None) or getattr(self.companion_llm, "model", "gemini-2.5-flash")
                record_llm_metrics(
                    stream_span,
                    model=model_name,
                    input_tokens=max(1, input_chars // 4),
                    output_tokens=max(1, len(full_response) // 4)
                )

        result_holder["response"] = full_response
        result_holder["user_id"] = user_id
        result_holder["session_id"] = session_id
        result_holder["user_message"] = user_message

    async def ainvoke_chat(
        self,
        user_id: UUID,
        session_id: UUID,
        user_message: str,
        result_holder: Optional[Dict[str, Any]] = None
    ) -> str:
        """Synchronous chat invocation using the compiled LangGraph StateGraph."""
        if result_holder is None:
            result_holder = {}

        initial_state: MoodHybridState = {
            "user_id": user_id,
            "session_id": session_id,
            "user_message": user_message
        }

        output = await self.graph.ainvoke(initial_state)

        if output.get("is_crisis", False):
            return "CRISIS"

        response_text = output.get("response_text", "")
        result_holder["response"] = response_text
        return response_text


# Global Singleton Instance
_mood_graph: Optional[MoodHybridGraph] = None


async def get_mood_graph() -> MoodHybridGraph:
    """Retrieve or create the initialized singleton MoodHybridGraph instance."""
    global _mood_graph
    if _mood_graph is None:
        sm = await get_session_manager()
        vs = get_vector_service_gemini()
        cd = CrisisDetector()
        _mood_graph = MoodHybridGraph(session_manager=sm, vector_service=vs, crisis_detector=cd)
    return _mood_graph
