"""History routes for both chat history (PostgreSQL) and session memory (Redis)."""

from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
from uuid import UUID
from pydantic import BaseModel

from app.database import get_db
from app.models import ChatHistory
from app.schemas import (
    ChatMessageResponse,
    ChatSessionSummary,
    ChatSessionDetail,
)
from app.services import get_session_manager


# ==========================================
# Router Definitions
# ==========================================
chat_history_router = APIRouter(prefix="/chat-history", tags=["chat-history"])
history_router = APIRouter(prefix="/history", tags=["history"])

# Combined router for all history endpoints
router = APIRouter()
router.include_router(chat_history_router)
router.include_router(history_router)


# ==========================================
# APIRouter 1: Chat History (PostgreSQL) Endpoints
# ==========================================

@chat_history_router.get("/sessions", response_model=List[ChatSessionSummary])
async def get_chat_sessions(
    user_id: UUID = Query(..., description="User ID to fetch sessions for"),
    limit: int = Query(50, ge=1, le=100, description="Max sessions to return"),
    db: AsyncSession = Depends(get_db)
):
    try:
        query = (
            select(
                ChatHistory.session_id,
                func.count(ChatHistory.id).label('message_count'),
                func.max(ChatHistory.timestamp).label('last_message_time')
            )
            .where(ChatHistory.user_id == user_id)
            .group_by(ChatHistory.session_id)
            .order_by(desc('last_message_time'))
            .limit(limit)
        )
        result = await db.execute(query)
        sessions_data = result.all()
        
        session_summaries = []
        for session_data in sessions_data:
            first_msg_query = (
                select(ChatHistory.content)
                .where(
                    ChatHistory.session_id == session_data.session_id,
                    ChatHistory.role == 'user'
                )
                .order_by(ChatHistory.timestamp)
                .limit(1)
            )
            first_msg_result = await db.execute(first_msg_query)
            first_message = first_msg_result.scalar()
            
            first_msg = first_message or "New Chat"
            title = first_msg[:50] + "..." if len(first_msg) > 50 else first_msg
            
            session_summaries.append(
                ChatSessionSummary(
                    session_id=session_data.session_id,
                    title=title,
                    last_message_time=session_data.last_message_time,
                    message_count=session_data.message_count,
                    first_message=first_message
                )
            )
        return session_summaries
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@chat_history_router.get("/sessions/{session_id}", response_model=ChatSessionDetail)
async def get_chat_session(
    session_id: UUID,
    user_id: UUID = Query(..., description="User ID for authorization"),
    db: AsyncSession = Depends(get_db)
):
    try:
        query = (
            select(ChatHistory)
            .where(
                ChatHistory.session_id == session_id,
                ChatHistory.user_id == user_id
            )
            .order_by(ChatHistory.timestamp)
        )
        result = await db.execute(query)
        messages = result.scalars().all()
        
        if not messages:
            raise HTTPException(status_code=404, detail=f"No messages found for session {session_id}")
            
        message_responses = [
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
            messages=message_responses,
            message_count=len(message_responses)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# APIRouter 2: Short-Term History (Redis) Endpoints
# ==========================================

class SessionHistoryResponse(BaseModel):
    session_id: str
    message_count: int
    messages: List[Dict[str, Any]]
    ttl_seconds: int


@history_router.get("/session/{session_id}", response_model=SessionHistoryResponse)
async def get_redis_session_history(session_id: UUID, limit: int = 50):
    try:
        if limit > 100:
            limit = 100
        session_manager = await get_session_manager()
        
        exists = await session_manager.session_exists(session_id)
        if not exists:
            raise HTTPException(status_code=404, detail="Session not found")
            
        if limit == -1:
            messages = await session_manager.get_full_history(session_id)
        else:
            messages = await session_manager.get_recent_history(session_id, limit=limit)
            
        message_count = await session_manager.get_session_length(session_id)
        ttl = await session_manager.get_session_ttl(session_id)
        
        return SessionHistoryResponse(
            session_id=str(session_id),
            message_count=message_count,
            messages=messages,
            ttl_seconds=ttl if ttl > 0 else 0
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@history_router.get("/sessions/active")
async def get_active_sessions():
    try:
        session_manager = await get_session_manager()
        sessions = await session_manager.get_active_sessions()
        return {
            "active_sessions": sessions,
            "count": len(sessions)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@history_router.delete("/session/{session_id}")
async def clear_session_history(session_id: UUID):
    try:
        session_manager = await get_session_manager()
        exists = await session_manager.session_exists(session_id)
        if not exists:
            raise HTTPException(status_code=404, detail="Session not found")
            
        success = await session_manager.clear_session(session_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to clear session")
            
        return {
            "message": "Session cleared successfully",
            "session_id": str(session_id)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
