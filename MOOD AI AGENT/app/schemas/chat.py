from pydantic import BaseModel, Field
from uuid import UUID
from typing import Optional


class ChatRequest(BaseModel):
    """Request schema for chat endpoint."""
    user_id: UUID = Field(..., description="User UUID")
    session_id: UUID = Field(..., description="Session UUID")
    message: str = Field(..., min_length=1, max_length=5000, description="User message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "session_id": "987fcdeb-51a2-43f7-b890-123456789abc",
                "message": "I'm feeling stressed about work today."
            }
        }


class ChatResponse(BaseModel):
    """Response schema for non-streaming chat."""
    response: str = Field(..., description="AI response")
    session_id: str = Field(..., description="Session ID")
    
    class Config:
        json_schema_extra = {
            "example": {
                "response": "I understand you're feeling stressed...",
                "session_id": "987fcdeb-51a2-43f7-b890-123456789abc"
            }
        }
