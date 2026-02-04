from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import ChatHistory
from app.schemas.chat_history import (
    ChatMessageResponse,
    ChatSessionSummary,
    ChatSessionDetail
)
from typing import List
from uuid import UUID

router = APIRouter(prefix="/chat-history", tags=["chat-history"])


@router.get("/sessions", response_model=List[ChatSessionSummary])
async def get_chat_sessions(
    user_id: UUID = Query(..., description="User ID to fetch sessions for"),
    limit: int = Query(50, ge=1, le=100, description="Max number of sessions to return"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all chat sessions for a user.
    
    Returns a list of sessions with:
    - session_id
    - title (generated from first user message)
    - last_message_time
    - message_count
    - first_message preview
    
    Sessions are ordered by most recent first.
    """
    try:
        from sqlalchemy import case
        
        # Get sessions with message counts and last message time
        # First, get basic session info
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
        
        # For each session, get the first user message
        session_summaries = []
        for session_data in sessions_data:
            # Get first user message for this session
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
            
            # Generate title from first message (truncate to 50 chars)
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
        print(f"Error fetching chat sessions: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/sessions/{session_id}", response_model=ChatSessionDetail)
async def get_chat_session(
    session_id: UUID,
    user_id: UUID = Query(..., description="User ID for authorization"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all messages for a specific chat session.
    
    """
    try:
        # Get all messages for this session
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
            raise HTTPException(
                status_code=404,
                detail=f"No messages found for session {session_id}"
            )
        
        # Convert to response schema
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
        print(f"Error fetching chat session: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
