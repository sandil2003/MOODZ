from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


# ==========================================
# Chat Schemas
# ==========================================

class ChatRequest(BaseModel):
    """Request schema for chat endpoint."""
    user_id: UUID = Field(..., description="User UUID")
    session_id: UUID = Field(..., description="Session UUID")
    message: str = Field(..., min_length=1, max_length=5000, description="User message")
    deep_search: bool = Field(default=False, description="Enable deep search mode for latest information")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "session_id": "987fcdeb-51a2-43f7-b890-123456789abc",
                "message": "I'm feeling stressed about work today.",
                "deep_search": False
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


# ==========================================
# User Schemas
# ==========================================

class UserBase(BaseModel):
    """Base user schema with common fields."""
    name: str = Field(..., min_length=1, max_length=255, description="User's name")
    email: Optional[EmailStr] = Field(None, description="User's email for authentication")
    preferences: Dict[str, Any] = Field(
        default_factory=dict,
        description="User preferences stored as JSON"
    )
    role: str = Field(default="user", description="User role (user, admin, etc.)")


class UserCreate(UserBase):
    """Schema for creating a new user."""
    password: Optional[str] = Field(
        None,
        min_length=8,
        description="Plain text password (will be hashed before storage)"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "John Doe",
                "email": "john@example.com",
                "password": "SecurePass123!",
                "preferences": {
                    "tone": "friendly",
                    "verbose": False
                },
                "role": "user"
            }
        }
    )


class UserUpdate(BaseModel):
    """Schema for updating an existing user."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    preferences: Optional[Dict[str, Any]] = None
    password: Optional[str] = Field(None, min_length=8)
    is_active: Optional[bool] = None
    role: Optional[str] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "John Smith",
                "preferences": {
                    "tone": "professional",
                    "verbose": True
                }
            }
        }
    )


class UserResponse(UserBase):
    """Schema for user response (excludes sensitive data)."""
    id: UUID
    created_at: datetime
    last_active: datetime
    is_active: bool
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "John Doe",
                "email": "john@example.com",
                "preferences": {
                    "tone": "friendly",
                    "verbose": False
                },
                "role": "user",
                "created_at": "2025-12-07T08:00:00",
                "last_active": "2025-12-07T13:30:00",
                "is_active": True
            }
        }
    )


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "john@example.com",
                "password": "SecurePass123!"
            }
        }
    )


# ==========================================
# Mood History Schemas
# ==========================================

class MoodHistoryBase(BaseModel):
    """Base mood history schema with common fields."""
    mood_score: int = Field(..., ge=1, le=10, description="Mood score from 1-10")
    sentiment_label: Optional[str] = Field(None, max_length=50, description="Sentiment label")
    topics: Optional[List[str]] = Field(None, description="Topics list")
    summary: str = Field(..., min_length=1, description="Summary of the mood entry")
    session_id: Optional[UUID] = Field(None, description="Chat session ID")
    
    @field_validator('mood_score')
    @classmethod
    def validate_mood_score(cls, v):
        if not 1 <= v <= 10:
            raise ValueError('mood_score must be between 1 and 10')
        return v


class MoodHistoryCreate(MoodHistoryBase):
    """Schema for creating a new mood history entry."""
    user_id: UUID = Field(..., description="User ID who owns this mood entry")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "mood_score": 7,
                "sentiment_label": "Happy",
                "topics": ["work", "achievement"],
                "summary": "User completed a project milestone.",
                "session_id": "987e6543-e21b-12d3-a456-426614174000"
            }
        }
    )


class MoodHistoryUpdate(BaseModel):
    """Schema for updating an existing mood history entry."""
    mood_score: Optional[int] = Field(None, ge=1, le=10)
    sentiment_label: Optional[str] = Field(None, max_length=50)
    topics: Optional[List[str]] = None
    summary: Optional[str] = Field(None, min_length=1)
    session_id: Optional[UUID] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "mood_score": 8,
                "sentiment_label": "Excited",
                "topics": ["work", "promotion"]
            }
        }
    )


class MoodHistoryResponse(MoodHistoryBase):
    """Schema for mood history response."""
    id: int
    user_id: UUID
    created_at: datetime
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "mood_score": 7,
                "sentiment_label": "Happy",
                "topics": ["work", "achievement"],
                "summary": "User completed a project milestone.",
                "session_id": "987e6543-e21b-12d3-a456-426614174000",
                "created_at": "2025-12-07T14:30:00"
            }
        }
    )


class MoodHistoryStats(BaseModel):
    """Schema for mood statistics."""
    user_id: UUID
    total_entries: int
    average_mood_score: float
    most_common_sentiment: Optional[str]
    most_common_topics: List[str]
    date_range: dict
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "total_entries": 45,
                "average_mood_score": 6.8,
                "most_common_sentiment": "Happy",
                "most_common_topics": ["work", "family"],
                "date_range": {
                    "first_entry": "2025-11-01T10:00:00",
                    "last_entry": "2025-12-07T14:30:00"
                }
            }
        }
    )


# ==========================================
# User Fact Schemas
# ==========================================

class UserFactBase(BaseModel):
    """Base user fact schema with common fields."""
    fact_text: str = Field(..., min_length=1, description="The fact about the user")
    category: str = Field(..., max_length=50, description="Category: Personal, Work, Family, etc.")
    source: str = Field(..., max_length=50, description="Source: conversation or manual_input")
    
    @field_validator('category')
    @classmethod
    def validate_category(cls, v):
        allowed_categories = ['Personal', 'Work', 'Family', 'Health', 'Hobbies', 'Education', 'Other']
        if v not in allowed_categories:
            pass
        return v
        
    @field_validator('source')
    @classmethod
    def validate_source(cls, v):
        allowed_sources = ['conversation', 'manual_input']
        if v not in allowed_sources:
            raise ValueError(f'source must be one of: {", ".join(allowed_sources)}')
        return v


class UserFactCreate(UserFactBase):
    """Schema for creating a new user fact."""
    user_id: UUID = Field(..., description="User ID who owns this fact")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "fact_text": "User has a dog named Rex.",
                "category": "Personal",
                "source": "conversation"
            }
        }
    )


class UserFactUpdate(BaseModel):
    """Schema for updating an existing user fact."""
    fact_text: Optional[str] = Field(None, min_length=1)
    category: Optional[str] = Field(None, max_length=50)
    source: Optional[str] = Field(None, max_length=50)
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "fact_text": "User has two dogs: Rex and Max.",
                "category": "Personal"
            }
        }
    )


class UserFactResponse(UserFactBase):
    """Schema for user fact response."""
    id: int
    user_id: UUID
    created_at: datetime
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "fact_text": "User has a dog named Rex.",
                "category": "Personal",
                "source": "conversation",
                "created_at": "2025-12-07T14:30:00"
            }
        }
    )


class UserFactsByCategory(BaseModel):
    """Schema for facts grouped by category."""
    user_id: UUID
    categories: dict[str, list[UserFactResponse]]
    total_facts: int
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "categories": {
                    "Personal": [
                        {
                            "id": 1,
                            "user_id": "123e4567-e89b-12d3-a456-426614174000",
                            "fact_text": "User has a dog named Rex.",
                            "category": "Personal",
                            "source": "conversation",
                            "created_at": "2025-12-07T14:30:00"
                        }
                    ]
                },
                "total_facts": 1
            }
        }
    )
