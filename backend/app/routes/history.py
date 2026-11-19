"""History routes for PostgreSQL chat transcripts and Redis session buffering."""

from typing import List, Dict, Any
from uuid import UUID
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db
from app.models import ChatHistory
from app.schemas import ChatMessageResponse, ChatSessionSummary, ChatSessionDetail
from app.services import get_session_manager

chat_history_router = APIRouter(prefix="/chat-history", tags=["chat-history"])
history_router = APIRouter(prefix="/history", tags=["history"])

# Combined router
router = APIRouter()
router.include_router(chat_history_router)
router.include_router(history_router)


# ============================================================================
# 1. PostgreSQL Chat History Endpoints
# ============================================================================

@chat_history_router.get("/sessions", response_model=List[ChatSessionSummary])
async def get_chat_sessions(
    user_id: UUID = Query(..., description="User ID to fetch sessions for"),
    limit: int = Query(50, ge=1, le=100, description="Max sessions to return"),
    db: AsyncSession = Depends(get_db)
) -> List[ChatSessionSummary]:
    """Retrieve distinct conversation session summaries for a user."""
    try:
        session_query = (
            select(
                ChatHistory.session_id,
                func.count(ChatHistory.id).label("message_count"),
                func.max(ChatHistory.timestamp).label("last_message_time")
            )
            .where(ChatHistory.user_id == user_id)
            .group_by(ChatHistory.session_id)
            .order_by(desc("last_message_time"))
            .limit(limit)
        )
        sessions_data = (await db.execute(session_query)).all()

        summaries: List[ChatSessionSummary] = []
        for row in sessions_data:
            first_msg_query = (
                select(ChatHistory.content)
                .where(
                    ChatHistory.session_id == row.session_id,
                    ChatHistory.role == "user"
                )
                .order_by(ChatHistory.timestamp)
                .limit(1)
            )
            first_msg = (await db.execute(first_msg_query)).scalar() or "New Chat"
            title = first_msg[:50] + "..." if len(first_msg) > 50 else first_msg

            summaries.append(
                ChatSessionSummary(
                    session_id=row.session_id,
                    title=title,
                    last_message_time=row.last_message_time,
                    message_count=row.message_count,
                    first_message=first_msg
                )
            )
        return summaries
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@chat_history_router.get("/sessions/{session_id}", response_model=ChatSessionDetail)
async def get_chat_session(
    session_id: UUID,
    user_id: UUID = Query(..., description="User ID for authorization"),
    db: AsyncSession = Depends(get_db)
) -> ChatSessionDetail:
    """Retrieve all messages in a specific chat session transcript."""
    try:
        msg_query = (
            select(ChatHistory)
            .where(
                ChatHistory.session_id == session_id,
                ChatHistory.user_id == user_id
            )
            .order_by(ChatHistory.timestamp)
        )
        messages = (await db.execute(msg_query)).scalars().all()

        if not messages:
            raise HTTPException(status_code=404, detail=f"No messages found for session {session_id}")

        responses = [
            ChatMessageResponse(
                id=msg.id,
                user_id=msg.user_id,
                session_id=msg.session_id,
                role=msg.role,
                content=msg.content,
                timestamp=msg.timestamp,
                deep_search=msg.deep_search
            )
            for msg in messages
        ]
        return ChatSessionDetail(
            session_id=session_id,
            messages=responses,
            message_count=len(responses)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 2. Redis Short-Term History Endpoints
# ============================================================================

class SessionHistoryResponse(BaseModel):
    session_id: str
    message_count: int
    messages: List[Dict[str, Any]]
    ttl_seconds: int


@history_router.get("/session/{session_id}", response_model=SessionHistoryResponse)
async def get_redis_session_history(session_id: UUID, limit: int = 50) -> SessionHistoryResponse:
    """Retrieve in-memory conversation buffer from Redis for an active session."""
    try:
        actual_limit = min(100, limit)
        sm = await get_session_manager()

        if not await sm.session_exists(session_id):
            raise HTTPException(status_code=404, detail="Session not found in cache")

        messages = (
            await sm.get_full_history(session_id)
            if actual_limit == -1
            else await sm.get_recent_history(session_id, limit=actual_limit)
        )
        count = await sm.get_session_length(session_id)
        ttl = await sm.get_session_ttl(session_id)

        return SessionHistoryResponse(
            session_id=str(session_id),
            message_count=count,
            messages=messages,
            ttl_seconds=max(0, ttl)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@history_router.get("/sessions/active")
async def get_active_sessions() -> Dict[str, Any]:
    """List all active session keys currently tracked in Redis."""
    try:
        sm = await get_session_manager()
        sessions = await sm.get_active_sessions()
        return {"active_sessions": sessions, "count": len(sessions)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@history_router.delete("/session/{session_id}")
async def clear_session_history(session_id: UUID) -> Dict[str, Any]:
    """Purge in-memory conversation state for a session from Redis."""
    try:
        sm = await get_session_manager()
        if not await sm.session_exists(session_id):
            raise HTTPException(status_code=404, detail="Session not found")

        if not await sm.clear_session(session_id):
            raise HTTPException(status_code=500, detail="Failed to clear session")

        return {"message": "Session cleared successfully", "session_id": str(session_id)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
