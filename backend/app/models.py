"""SQLAlchemy ORM models for the MOODZ mental wellness platform."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base


def _utc_now():
    """Helper returning current UTC datetime."""
    return datetime.now(timezone.utc)


class User(Base):
    """User account model storing identity, encrypted credentials, and preferences."""
    __tablename__ = "users"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        nullable=False,
        index=True,
        comment="Primary Key - User UUID"
    )
    email = Column(
        String(255),
        unique=True,
        nullable=True,
        index=True,
        comment="Unique user email address"
    )
    name = Column(
        String(255),
        nullable=False,
        comment="Display name for personalized companion dialogue"
    )
    preferences = Column(
        JSONB,
        nullable=False,
        default=dict,
        comment="User conversational settings (e.g., {'tone': 'friendly', 'verbose': false})"
    )
    created_at = Column(
        DateTime,
        nullable=False,
        default=_utc_now,
        comment="Account registration timestamp"
    )
    last_active = Column(
        DateTime,
        nullable=False,
        default=_utc_now,
        onupdate=_utc_now,
        comment="Last active interaction timestamp"
    )
    hashed_password = Column(
        Text,
        nullable=True,
        comment="Bcrypt-hashed user password"
    )
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Active account status flag"
    )
    role = Column(
        String(50),
        nullable=False,
        default="user",
        comment="User access role (e.g., 'user', 'admin')"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, name='{self.name}', email='{self.email}', role='{self.role}')>"

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "email": self.email,
            "name": self.name,
            "preferences": self.preferences,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_active": self.last_active.isoformat() if self.last_active else None,
            "is_active": self.is_active,
            "role": self.role
        }

    def update_last_active(self) -> None:
        """Update last active timestamp to current UTC time."""
        self.last_active = _utc_now()


class ChatHistory(Base):
    """Stores individual message turns between user and companion."""
    __tablename__ = "chat_history"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        nullable=False,
        comment="Primary Key - Message UUID"
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign Key referencing users.id"
    )
    session_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="Chat conversation session UUID"
    )
    role = Column(
        String(20),
        nullable=False,
        comment="Message role ('user' or 'assistant')"
    )
    content = Column(
        Text,
        nullable=False,
        comment="Message text content (PII sanitized)"
    )
    timestamp = Column(
        DateTime,
        nullable=False,
        default=_utc_now,
        index=True,
        comment="Message creation timestamp"
    )
    deep_search = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Flag indicating if deep context search was invoked"
    )

    __table_args__ = (
        Index("idx_user_session", "user_id", "session_id"),
        Index("idx_user_timestamp", "user_id", "timestamp"),
    )

    def __repr__(self) -> str:
        preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"<ChatHistory(id={self.id}, role='{self.role}', content='{preview}')>"

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "session_id": str(self.session_id),
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "deep_search": self.deep_search
        }


class MoodHistory(Base):
    """Tracks numerical mood ratings (1-10) and sentiment trends over time."""
    __tablename__ = "moodhistory"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        nullable=False,
        index=True,
        comment="Primary Key"
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign Key referencing users.id"
    )
    mood_score = Column(
        Integer,
        nullable=False,
        comment="Numerical wellness score from 1 (distress) to 10 (optimal)"
    )
    sentiment_label = Column(
        String(50),
        nullable=True,
        comment="Emotional state label (e.g., 'happy', 'anxious', 'calm')"
    )
    topics = Column(
        JSONB,
        nullable=True,
        comment="Extracted conversation topic tags"
    )
    summary = Column(
        Text,
        nullable=False,
        comment="Turn summary or user message excerpt"
    )
    session_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="Session UUID associated with this mood check-in"
    )
    created_at = Column(
        DateTime,
        nullable=False,
        default=_utc_now,
        index=True,
        comment="Creation timestamp"
    )

    user = relationship("User", backref="mood_entries")

    def __repr__(self) -> str:
        return f"<MoodHistory(id={self.id}, user_id={self.user_id}, mood_score={self.mood_score}, sentiment='{self.sentiment_label}')>"

    def to_dict(self) -> dict:
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


class UserFact(Base):
    """Stores durable personal facts learned about the user across conversations."""
    __tablename__ = "userfacts"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        nullable=False,
        index=True,
        comment="Primary Key"
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign Key referencing users.id"
    )
    fact_text = Column(
        Text,
        nullable=False,
        comment="Personal fact statement (e.g., 'User has a dog named Max')"
    )
    category = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Category tag (e.g., 'Personal', 'Work', 'Health', 'Hobbies')"
    )
    source = Column(
        String(50),
        nullable=False,
        comment="Extraction source (e.g., 'adk_profiler', 'manual_input')"
    )
    created_at = Column(
        DateTime,
        nullable=False,
        default=_utc_now,
        index=True,
        comment="Extraction timestamp"
    )

    user = relationship("User", backref="facts")

    def __repr__(self) -> str:
        preview = self.fact_text[:50] + "..." if len(self.fact_text) > 50 else self.fact_text
        return f"<UserFact(id={self.id}, user_id={self.user_id}, category='{self.category}', fact='{preview}')>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": str(self.user_id),
            "fact_text": self.fact_text,
            "category": self.category,
            "source": self.source,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class ChatFeedback(Base):
    """User ratings and feedback enabling the AgentOps continuous improvement flywheel."""
    __tablename__ = "chat_feedback"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        nullable=False,
        index=True,
        comment="Primary Key - Feedback UUID"
    )
    session_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="Session UUID associated with the feedback"
    )
    message_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="Optional Message UUID evaluated"
    )
    rating = Column(
        Integer,
        nullable=False,
        comment="User score: +1 for thumbs up, -1 for thumbs down"
    )
    comment = Column(
        Text,
        nullable=True,
        comment="Optional user comment or critique"
    )
    corrected_mood = Column(
        String(50),
        nullable=True,
        comment="User-corrected emotional tone label if misclassified"
    )
    created_at = Column(
        DateTime,
        nullable=False,
        default=_utc_now,
        index=True,
        comment="Submission timestamp"
    )

    def __repr__(self) -> str:
        return f"<ChatFeedback(id={self.id}, session_id={self.session_id}, rating={self.rating})>"

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "session_id": str(self.session_id),
            "message_id": str(self.message_id) if self.message_id else None,
            "rating": self.rating,
            "comment": self.comment,
            "corrected_mood": self.corrected_mood,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
