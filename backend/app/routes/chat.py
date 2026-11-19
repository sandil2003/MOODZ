"""Chat routes for real-time conversation streaming, chat completion, and feedback tracking."""

import json
import time
import asyncio
import logging
from typing import AsyncGenerator, Dict, Any, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import StreamingResponse

from app.database import AsyncSessionLocal
from app.models import ChatHistory, MoodHistory, UserFact, ChatFeedback
from app.core.pii_scrubber import PIIScrubber
from app.core.telemetry import trace_span
from app.schemas import ChatRequest, ChatResponse, ChatFeedbackRequest, ChatFeedbackResponse
from app.services import (
    get_mood_agent,
    get_session_manager,
    get_vector_service_gemini,
    API_ERROR_WARNING,
    mock_classify
)
from app.utils import get_chat_logger

logger = logging.getLogger(__name__)


def normalize_text(content: Any) -> str:
    """Normalize LLM content chunks into a plain string."""
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
# Router & Connection Management
# ============================================================================

router = APIRouter(prefix="/moods/chat", tags=["chat"])
chat_router = router  # Backwards-compatibility alias


class ConnectionManager:
    """WebSocket connection registry for live chat status notifications."""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str) -> None:
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"WebSocket connected for session: {session_id}")

    def disconnect(self, session_id: str) -> None:
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"WebSocket disconnected for session: {session_id}")

    async def send_status(self, session_id: str, status: str) -> None:
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_json({
                    "type": "status",
                    "content": status
                })
            except Exception as e:
                logger.error(f"Error sending WebSocket status to {session_id}: {e}")


manager = ConnectionManager()


# ============================================================================
# Database Helpers
# ============================================================================

async def save_chat_message_to_db(
    user_id: UUID,
    session_id: UUID,
    role: str,
    content: str,
    deep_search: bool = False
) -> None:
    """Persist a scrubbed user or assistant message to the PostgreSQL chat_history table."""
    try:
        content_str = PIIScrubber.scrub_text(normalize_text(content))
        async with AsyncSessionLocal() as db:
            message = ChatHistory(
                user_id=user_id,
                session_id=session_id,
                role=role,
                content=content_str,
                deep_search=deep_search
            )
            db.add(message)
            await db.commit()
    except Exception as e:
        logger.error(f"Error saving {role} message to database: {e}")


async def save_conversation_intelligently(
    user_id: UUID,
    session_id: UUID,
    message: str,
    response: str,
    classification: Dict[str, Any]
) -> None:
    """Legacy helper persisting facts and mood rating to PostgreSQL and Pinecone."""
    if not classification.get("save", False):
        return

    try:
        vector_service = get_vector_service_gemini()

        # 1. Save turns to Pinecone
        try:
            await vector_service.add_text(
                user_id=user_id,
                text=message,
                data_type="mood_checkin",
                source="typing",
                mood_label=classification.get("mood", "neutral"),
                context_id=str(session_id)
            )
            await vector_service.add_text(
                user_id=user_id,
                text=response,
                data_type="text",
                source="assistant",
                context_id=str(session_id)
            )
        except Exception as pc_err:
            logger.warning(f"Failed to save text to Pinecone: {pc_err}")

        # 2. Save facts and mood to PostgreSQL
        async with AsyncSessionLocal() as db:
            for fact_text in classification.get("extracted_facts", []):
                db.add(UserFact(
                    user_id=user_id,
                    fact_text=PIIScrubber.scrub_text(fact_text),
                    category="auto_extracted",
                    source="conversation_classifier"
                ))

            mood_value = classification.get("mood", "neutral")
            if mood_value and mood_value != "neutral":
                mood_scores = {
                    "happy": 8, "joyful": 9, "excited": 8, "content": 7,
                    "sad": 3, "depressed": 2, "down": 3, "melancholic": 3,
                    "anxious": 4, "worried": 4, "nervous": 4, "stressed": 3,
                    "angry": 3, "frustrated": 4, "irritated": 4,
                    "calm": 7, "peaceful": 8, "relaxed": 7,
                    "neutral": 5, "confused": 5, "uncertain": 5,
                    "hopeful": 7, "optimistic": 8
                }
                db.add(MoodHistory(
                    user_id=user_id,
                    mood_score=mood_scores.get(mood_value, 5),
                    sentiment_label=mood_value,
                    summary=PIIScrubber.scrub_text(message[:255]),
                    session_id=session_id
                ))
            await db.commit()
    except Exception as e:
        logger.error(f"Error in save_conversation_intelligently: {e}")


# ============================================================================
# Streaming & Endpoints
# ============================================================================

async def stream_chat_response(
    user_id: UUID,
    session_id: UUID,
    message: str
) -> AsyncGenerator[str, None]:
    """Execute conversational turn via LangGraph and yield Server-Sent Events (SSE)."""
    start_time = time.time()
    try:
        chain = await get_mood_agent()
        session_manager = await get_session_manager()

        # Buffer message in Redis and database
        await session_manager.add_user_message(session_id, message)
        await save_chat_message_to_db(user_id, session_id, "user", message)

        full_response = ""
        result_holder: Dict[str, Any] = {}

        async for chunk in chain.astream(user_id, session_id, message, result_holder):
            if chunk == "CRISIS":
                crisis_message = (
                    "I'm really concerned about what you're sharing. Please reach out to a mental health "
                    "professional or crisis helpline immediately. You can reach the 988 Suicide & Crisis Lifeline "
                    "(call or text 988), text HOME to 741741, or contact your local emergency services."
                )
                await session_manager.add_assistant_message(session_id, crisis_message)
                await save_chat_message_to_db(user_id, session_id, "assistant", crisis_message)
                yield f"data: {json.dumps({'chunk': crisis_message})}\n\n"
                yield f"data: {json.dumps({'done': True, 'session_id': str(session_id), 'crisis_detected': True})}\n\n"
                return

            if chunk == API_ERROR_WARNING:
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                continue

            full_response += chunk
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"

        latency = time.time() - start_time
        clean_response = full_response

        # Save assistant response
        await session_manager.add_assistant_message(session_id, clean_response)
        await save_chat_message_to_db(user_id, session_id, "assistant", clean_response)

        # Classification summary for terminal event
        classification = mock_classify(message)
        logger_service = get_chat_logger()
        await logger_service.log_chat(
            user_id=user_id,
            session_id=session_id,
            prompt=message,
            response=clean_response,
            latency=latency,
            metadata={
                "streaming": True,
                "save_to_db": classification.get("save", False),
                "mood": classification.get("mood", "neutral"),
                "extracted_facts": classification.get("extracted_facts", [])
            }
        )

        completion_data = {
            "done": True,
            "session_id": str(session_id),
            "latency": round(latency, 3),
            "classification": classification
        }
        yield f"data: {json.dumps(completion_data)}\n\n"

    except Exception as e:
        logger.error(f"Error in stream_chat_response: {e}")
        yield f"data: {json.dumps({'error': f'Error: {str(e)}'})}\n\n"


@router.post("/stream", response_class=StreamingResponse)
async def chat_stream(
    request: ChatRequest,
    background_tasks: BackgroundTasks
):
    """Real-time SSE token streaming endpoint with background intelligence profiling."""
    async def generate():
        full_response = ""

        async for event in stream_chat_response(request.user_id, request.session_id, request.message):
            if '"chunk"' in event:
                try:
                    data = json.loads(event.replace("data: ", "").strip())
                    if "chunk" in data and data["chunk"] != API_ERROR_WARNING:
                        full_response += data["chunk"]
                except Exception:
                    pass
            yield event

        # Schedule non-blocking background analysis after stream ends
        if full_response:
            from app.services.mood_graph import get_mood_graph
            graph = await get_mood_graph()
            background_tasks.add_task(
                graph.profile_conversation_async,
                request.user_id,
                request.session_id,
                request.message,
                full_response
            )

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    background_tasks: BackgroundTasks
) -> ChatResponse:
    """Synchronous chat endpoint with background intelligence extraction."""
    start_time = time.time()
    try:
        chain = await get_mood_agent()
        result_holder: Dict[str, Any] = {}
        response = await chain.invoke(
            user_id=request.user_id,
            session_id=request.session_id,
            user_message=request.message,
            result_holder=result_holder
        )
        latency = time.time() - start_time

        await save_chat_message_to_db(request.user_id, request.session_id, "user", request.message)

        clean_response = response.replace(API_ERROR_WARNING, "") if API_ERROR_WARNING in response else response
        await save_chat_message_to_db(request.user_id, request.session_id, "assistant", clean_response)

        # Trigger background profiler
        from app.services.mood_graph import get_mood_graph
        graph = await get_mood_graph()
        background_tasks.add_task(
            graph.profile_conversation_async,
            request.user_id,
            request.session_id,
            request.message,
            clean_response
        )

        chat_logger = get_chat_logger()
        background_tasks.add_task(
            chat_logger.log_chat,
            request.user_id,
            request.session_id,
            request.message,
            clean_response,
            latency,
            {"streaming": False, "save_to_db": True}
        )

        return ChatResponse(
            response=response,
            session_id=str(request.session_id)
        )
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/feedback", response_model=ChatFeedbackResponse)
async def submit_chat_feedback(feedback: ChatFeedbackRequest) -> ChatFeedbackResponse:
    """AgentOps endpoint to record user feedback rating and tag traces in Arize Phoenix."""
    with trace_span(
        "agentops.user_feedback",
        span_type="feedback.user",
        attributes={
            "session_id": str(feedback.session_id),
            "rating": feedback.rating,
            "comment": feedback.comment or "",
            "corrected_mood": feedback.corrected_mood or ""
        }
    ) as span:
        span.set_attribute("feedback.rating", feedback.rating)

        feedback_record = ChatFeedback(
            session_id=feedback.session_id,
            message_id=feedback.message_id,
            rating=feedback.rating,
            comment=feedback.comment,
            corrected_mood=feedback.corrected_mood
        )
        async with AsyncSessionLocal() as db:
            db.add(feedback_record)
            await db.commit()
            await db.refresh(feedback_record)

        return ChatFeedbackResponse(
            status="recorded",
            message="Feedback logged successfully",
            feedback_id=feedback_record.id
        )


@router.websocket("/ws/status/{session_id}")
async def websocket_status(websocket: WebSocket, session_id: str):
    """WebSocket channel for live status and thought notifications."""
    await manager.connect(websocket, session_id)
    try:
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
    except WebSocketDisconnect:
        manager.disconnect(session_id)


# ============================================================================
# Backwards-Compatibility Re-exports
# ============================================================================
from app.routes.history import history_router, chat_history_router  # noqa: E402
from app.routes.mood import mood_data_router  # noqa: E402

__all__ = [
    "router",
    "chat_router",
    "history_router",
    "chat_history_router",
    "mood_data_router",
    "normalize_text",
    "ConnectionManager",
    "manager",
    "save_chat_message_to_db",
    "save_conversation_intelligently",
    "stream_chat_response",
    "chat_stream",
    "chat",
    "websocket_status"
]
