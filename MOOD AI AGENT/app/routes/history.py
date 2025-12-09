from fastapi import APIRouter, HTTPException
from uuid import UUID
from typing import List, Dict, Any
from app.services import get_session_manager
from pydantic import BaseModel

router = APIRouter(prefix="/history", tags=["history"])


class SessionHistoryResponse(BaseModel):
    """Response schema for session history."""
    session_id: str
    message_count: int
    messages: List[Dict[str, Any]]
    ttl_seconds: int


@router.get("/session/{session_id}", response_model=SessionHistoryResponse)
async def get_session_history(session_id: UUID, limit: int = 50):
    """
    Get conversation history for a specific session.
    
    Args:
        session_id: Session UUID
        limit: Maximum number of messages to retrieve (default: 50, max: 100)
    
    Returns:
        SessionHistoryResponse: Session history with messages
    """
    try:
        # Validate limit
        if limit > 100:
            limit = 100
        
        session_manager = await get_session_manager()
        
        # Check if session exists
        exists = await session_manager.session_exists(session_id)
        if not exists:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get messages
        if limit == -1:
            # Get all messages
            messages = await session_manager.get_full_history(session_id)
        else:
            # Get recent messages
            messages = await session_manager.get_recent_history(session_id, limit=limit)
        
        # Get session metadata
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


@router.get("/sessions/active")
async def get_active_sessions():
    """
    Get list of all active sessions.
    
    Returns:
        dict: List of active session IDs
    """
    try:
        session_manager = await get_session_manager()
        sessions = await session_manager.get_active_sessions()
        
        return {
            "active_sessions": sessions,
            "count": len(sessions)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/session/{session_id}")
async def clear_session_history(session_id: UUID):
    """
    Clear conversation history for a specific session.
    
    Args:
        session_id: Session UUID
    
    Returns:
        dict: Success message
    """
    try:
        session_manager = await get_session_manager()
        
        # Check if session exists
        exists = await session_manager.session_exists(session_id)
        if not exists:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Clear session
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
