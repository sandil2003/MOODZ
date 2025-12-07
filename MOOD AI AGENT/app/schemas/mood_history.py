from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class MoodHistoryBase(BaseModel):
    """Base mood history schema with common fields."""
    mood_score: int = Field(..., ge=1, le=10, description="Mood score from 1-10")
    sentiment_label: Optional[str] = Field(None, max_length=50, description="Sentiment label like 'Happy', 'Anxious', 'Neutral'")
    topics: Optional[List[str]] = Field(None, description="List of topics like ['work', 'deadline']")
    summary: str = Field(..., min_length=1, description="Summary of the mood entry")
    session_id: Optional[UUID] = Field(None, description="Chat session ID for debugging")
    
    @field_validator('mood_score')
    @classmethod
    def validate_mood_score(cls, v):
        if not 1 <= v <= 10:
            raise ValueError('mood_score must be between 1 and 10')
        return v
    
    @field_validator('sentiment_label')
    @classmethod
    def validate_sentiment_label(cls, v):
        if v is not None:
            allowed_sentiments = ['Happy', 'Sad', 'Anxious', 'Neutral', 'Excited', 'Stressed', 'Calm', 'Angry', 'Content']
            if v not in allowed_sentiments:
                # Allow custom sentiments but warn
                pass
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
                "summary": "User completed a major project milestone today.",
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
                "summary": "User completed a major project milestone today.",
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
                "most_common_topics": ["work", "family", "health"],
                "date_range": {
                    "first_entry": "2025-11-01T10:00:00",
                    "last_entry": "2025-12-07T14:30:00"
                }
            }
        }
    )
