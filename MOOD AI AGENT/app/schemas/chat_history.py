"""Chat History schemas for API request/response validation."""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional
from uuid import UUID


class ChatMessageBase(BaseModel):
    """Base schema for chat messages."""
    role: str = Field(..., description="Either 'user' or 'assistant'")
    content: str = Field(..., description="The message text")
    deep_search: bool = Field(default=False, description="Whether deep search was used")


class ChatMessageCreate(ChatMessageBase):
    """Schema for creating a new chat message."""
    user_id: UUID
    session_id: UUID


class ChatMessageResponse(ChatMessageBase):
    """Schema for returning a chat message."""
    id: UUID
    user_id: UUID
    session_id: UUID
    timestamp: datetime

    class Config:
        from_attributes = True


class ChatSessionSummary(BaseModel):
    """Schema for chat session summary (for listing sessions)."""
    session_id: UUID
    title: str = Field(..., description="Generated title from first user message")
    last_message_time: datetime
    message_count: int
    first_message: Optional[str] = Field(None, description="Preview of first message")

    class Config:
        from_attributes = True


class ChatSessionDetail(BaseModel):
    """Schema for complete chat session with all messages."""
    session_id: UUID
    messages: List[ChatMessageResponse]
    message_count: int

    class Config:
        from_attributes = True
