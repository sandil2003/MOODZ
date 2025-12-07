import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base


class MoodHistory(Base):
    """
    MoodHistory model for tracking user mood entries over time.
    
    Attributes:
        id: Integer primary key
        user_id: Foreign key to users table (UUID)
        mood_score: Integer score from 1-10 for graphing
        sentiment_label: String label like "Happy", "Anxious", "Neutral"
        topics: JSONB array of topics like ["work", "deadline"]
        summary: Text summary of the mood entry
        session_id: UUID linking to specific chat session for debugging
        created_at: Timestamp when mood was recorded
    """
    
    __tablename__ = "moodhistory"
    
    # Primary Key
    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        nullable=False,
        index=True,
        comment="Primary Key"
    )
    
    # Foreign Key to User
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign Key to users table"
    )
    
    # Mood Score (1-10 scale)
    mood_score = Column(
        Integer,
        nullable=False,
        comment="1-10 scale. Good for graphing on the Frontend."
    )
    
    # Sentiment Label
    sentiment_label = Column(
        String(50),
        nullable=True,
        comment="'Happy', 'Anxious', 'Neutral'. The LLM understands words better than numbers."
    )
    
    # Topics (JSONB array)
    topics = Column(
        JSONB,
        nullable=True,
        comment="['work', 'deadline']. Stores why they feel this way. Essential for pattern recognition."
    )
    
    # Summary
    summary = Column(
        Text,
        nullable=False,
        comment="'User is stressed about the demo tomorrow.'"
    )
    
    # Session ID for debugging
    session_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="Links this mood entry to a specific chat session (in case you need to debug)."
    )
    
    # Timestamp
    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
        comment="Timestamp"
    )
    
    # Relationship to User
    user = relationship("User", backref="mood_entries")
    
    def __repr__(self):
        return f"<MoodHistory(id={self.id}, user_id={self.user_id}, mood_score={self.mood_score}, sentiment='{self.sentiment_label}')>"
    
    def to_dict(self):
        """Convert mood history object to dictionary."""
        return {
            "id": self.id,
            "user_id": str(self.user_id),
            "mood_score": self.mood_score,
            "sentiment_label": self.sentiment_label,
            "topics": self.topics,
            "summary": self.summary,
            "session_id": str(self.session_id) if self.session_id else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
