"""Pydantic validation schemas for Chat, User, Mood History, and Facts."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator


# ============================================================================
# 1. Chat Schemas
# ============================================================================

class ChatRequest(BaseModel):
    """Request payload for chat generation and streaming."""
    user_id: UUID = Field(..., description="User UUID")
    session_id: UUID = Field(..., description="Session UUID")
    message: str = Field(..., min_length=1, max_length=5000, description="User conversational prompt")
    deep_search: bool = Field(default=False, description="Enable deep context retrieval mode")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "session_id": "987fcdeb-51a2-43f7-b890-123456789abc",
                "message": "I'm feeling stressed about work today.",
                "deep_search": False
            }
        }
    )


class ChatResponse(BaseModel):
    """Response payload for synchronous (non-streaming) chat."""
    response: str = Field(..., description="Empathetic companion text response")
    session_id: str = Field(..., description="Active session ID string")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "response": "I hear how overwhelmed you feel, and it's completely understandable...",
                "session_id": "987fcdeb-51a2-43f7-b890-123456789abc"
            }
        }
    )


class ChatMessageBase(BaseModel):
    """Common fields for chat message records."""
    role: str = Field(..., description="Speaker role: 'user' or 'assistant'")
    content: str = Field(..., description="Message text content")
    deep_search: bool = Field(default=False, description="Whether deep search was used")


class ChatMessageCreate(ChatMessageBase):
    """Creation payload for persisting a chat message."""
    user_id: UUID
    session_id: UUID


class ChatMessageResponse(ChatMessageBase):
    """Response representation of a persisted chat message."""
    id: UUID
    user_id: UUID
    session_id: UUID
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatSessionSummary(BaseModel):
    """Summary of a chat session for listing in the sidebar."""
    session_id: UUID
    title: str = Field(..., description="Session title derived from initial message")
    last_message_time: Optional[datetime] = Field(None, description="Timestamp of the latest message")
    message_count: int = Field(0, description="Total count of messages in this session")
    first_message: Optional[str] = Field(None, description="Preview snippet of the first message")

    model_config = ConfigDict(from_attributes=True)


class ChatSessionDetail(BaseModel):
    """Complete detail view of a session including all transcript messages."""
    session_id: UUID
    messages: List[ChatMessageResponse]
    message_count: int

    model_config = ConfigDict(from_attributes=True)


class ChatFeedbackRequest(BaseModel):
    """User feedback payload (thumbs up/down and mood correction)."""
    session_id: UUID = Field(..., description="Session UUID evaluated")
    message_id: Optional[UUID] = Field(default=None, description="Optional Message UUID")
    rating: int = Field(..., ge=-1, le=1, description="+1 for positive (thumbs up), -1 for negative (thumbs down)")
    comment: Optional[str] = Field(default=None, max_length=1000, description="Optional qualitative comment")
    corrected_mood: Optional[str] = Field(default=None, description="Optional corrected mood label")


class ChatFeedbackResponse(BaseModel):
    """Response returned upon feedback registration."""
    status: str = "recorded"
    message: str = "Feedback logged successfully"
    feedback_id: Optional[UUID] = Field(default=None, description="UUID of persisted feedback record")

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# 2. User & Authentication Schemas
# ============================================================================

class UserBase(BaseModel):
    """Common user account properties."""
    name: str = Field(..., min_length=1, max_length=255, description="Display name")
    email: Optional[EmailStr] = Field(None, description="User email address")
    preferences: Dict[str, Any] = Field(default_factory=dict, description="User preferences stored as JSON")
    role: str = Field(default="user", description="Account role ('user', 'admin')")


class UserCreate(UserBase):
    """Registration payload for creating a new user account."""
    password: Optional[str] = Field(None, min_length=8, description="Plain text password to be hashed")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Jane Doe",
                "email": "jane@example.com",
                "password": "SecurePassword123!",
                "preferences": {"tone": "gentle", "verbose": False},
                "role": "user"
            }
        }
    )


class UserUpdate(BaseModel):
    """Payload for updating user profile fields."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    preferences: Optional[Dict[str, Any]] = None
    password: Optional[str] = Field(None, min_length=8)
    is_active: Optional[bool] = None
    role: Optional[str] = None


class UserResponse(UserBase):
    """Safe public user representation excluding password hashes."""
    id: UUID
    created_at: datetime
    last_active: datetime
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class UserLogin(BaseModel):
    """Credentials payload for JWT authentication."""
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    """Authentication response returning bearer token and user profile."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ============================================================================
# 3. Mood History Schemas
# ============================================================================

class MoodHistoryBase(BaseModel):
    """Common mood history check-in fields."""
    mood_score: int = Field(..., ge=1, le=10, description="Wellness rating from 1 to 10")
    sentiment_label: Optional[str] = Field(None, max_length=50, description="Sentiment descriptor (e.g., 'Happy')")
    topics: Optional[List[str]] = Field(None, description="Associated conversational topic tags")
    summary: str = Field(..., min_length=1, description="Summary or trigger description")
    session_id: Optional[UUID] = Field(None, description="Optional associated session ID")

    @field_validator("mood_score")
    @classmethod
    def validate_mood_score(cls, v: int) -> int:
        if not 1 <= v <= 10:
            raise ValueError("mood_score must be between 1 and 10")
        return v


class MoodHistoryCreate(MoodHistoryBase):
    """Creation payload for logging a mood check-in."""
    user_id: UUID = Field(..., description="User ID for the mood check-in")


class MoodHistoryUpdate(BaseModel):
    """Payload for modifying an existing mood log."""
    mood_score: Optional[int] = Field(None, ge=1, le=10)
    sentiment_label: Optional[str] = Field(None, max_length=50)
    topics: Optional[List[str]] = None
    summary: Optional[str] = Field(None, min_length=1)
    session_id: Optional[UUID] = None


class MoodHistoryResponse(MoodHistoryBase):
    """Response representation of a mood history entry."""
    id: int
    user_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MoodHistoryStats(BaseModel):
    """Aggregated mood metrics and emotional trends."""
    user_id: UUID
    total_entries: int
    average_mood_score: float
    most_common_sentiment: Optional[str]
    most_common_topics: List[str]
    date_range: Dict[str, Any]

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# 4. User Fact Schemas
# ============================================================================

class UserFactBase(BaseModel):
    """Common properties for durable user facts."""
    fact_text: str = Field(..., min_length=1, description="Fact statement")
    category: str = Field(..., max_length=50, description="Fact category (Personal, Work, Family, etc.)")
    source: str = Field(..., max_length=50, description="Extraction source")

    @field_validator("source")
    @classmethod
    def validate_source(cls, v: str) -> str:
        allowed = {
            "conversation",
            "manual_input",
            "adk_profiler",
            "background_profiler",
            "profiler",
            "chat",
            "auto_extracted"
        }
        if v not in allowed:
            if isinstance(v, str) and v.strip():
                return v.strip()
            raise ValueError(f"source must be one of: {', '.join(sorted(allowed))}")
        return v


class UserFactCreate(UserFactBase):
    """Creation payload for recording a user fact."""
    user_id: UUID = Field(..., description="User ID owning this fact")


class UserFactUpdate(BaseModel):
    """Update payload for modifying a user fact."""
    fact_text: Optional[str] = Field(None, min_length=1)
    category: Optional[str] = Field(None, max_length=50)
    source: Optional[str] = Field(None, max_length=50)


class UserFactResponse(UserFactBase):
    """Response representation of a persisted user fact."""
    id: int
    user_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserFactsByCategory(BaseModel):
    """Categorized breakdown of user facts."""
    user_id: UUID
    categories: Dict[str, List[UserFactResponse]]
    total_facts: int

    model_config = ConfigDict(from_attributes=True)
