import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    """
    User model for storing user information and preferences.
    """
    __tablename__ = "users"
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        nullable=False,
        index=True,
        comment="Primary Key - UUID"
    )
    email = Column(
        String(255),
        unique=True,
        nullable=True,
        index=True,
        comment="Good for future auth/login"
    )
    name = Column(
        String(255),
        nullable=False,
        comment="So the agent knows what to call the user"
    )
    preferences = Column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Store things like {'tone': 'friendly', 'verbose': false}."
    )
    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        comment="To calculate 'how long have we known each other'"
    )
    last_active = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="To welcome back a user"
    )
    hashed_password = Column(
        Text,
        nullable=True,
        comment="Stored encrypted password"
    )
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Active status flag"
    )
    role = Column(
        String(50),
        nullable=False,
        default="user",
        comment="User role (user, admin, etc.)"
    )
    
    def __repr__(self):
        return f"<User(id={self.id}, name='{self.name}', email='{self.email}', role='{self.role}')>"
        
    def to_dict(self):
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
        
    def update_last_active(self):
        self.last_active = datetime.utcnow()


class ChatHistory(Base):
    """
    ChatHistory model for storing individual chat messages.
    """
    __tablename__ = "chat_history"
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        nullable=False,
        comment="Primary Key - UUID"
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User who sent/received this message"
    )
    session_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="Groups messages into conversations"
    )
    role = Column(
        String(20),
        nullable=False,
        comment="Either 'user' or 'assistant'"
    )
    content = Column(
        Text,
        nullable=False,
        comment="The actual message text"
    )
    timestamp = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
        comment="When the message was created"
    )
    deep_search = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether deep search was used"
    )
    
    __table_args__ = (
        Index('idx_user_session', 'user_id', 'session_id'),
        Index('idx_user_timestamp', 'user_id', 'timestamp'),
    )
    
    def __repr__(self):
        content_preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"<ChatHistory(id={self.id}, role='{self.role}', content='{content_preview}')>"
        
    def to_dict(self):
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
    """
    MoodHistory model for tracking user mood entries over time.
    """
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
        comment="Foreign Key to users table"
    )
    mood_score = Column(
        Integer,
        nullable=False,
        comment="1-10 scale"
    )
    sentiment_label = Column(
        String(50),
        nullable=True,
        comment="Sentiment label like 'Happy', 'Anxious', 'Neutral'"
    )
    topics = Column(
        JSONB,
        nullable=True,
        comment="Topics list"
    )
    summary = Column(
        Text,
        nullable=False,
        comment="Text summary of mood entry"
    )
    session_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="Links this mood entry to a specific chat session"
    )
    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
        comment="Timestamp"
    )
    
    user = relationship("User", backref="mood_entries")
    
    def __repr__(self):
        return f"<MoodHistory(id={self.id}, user_id={self.user_id}, mood_score={self.mood_score}, sentiment='{self.sentiment_label}')>"
        
    def to_dict(self):
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
    """
    UserFact model for storing facts about users.
    """
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
        comment="Foreign Key to users table"
    )
    fact_text = Column(
        Text,
        nullable=False,
        comment="Factual text"
    )
    category = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Category for filtering"
    )
    source = Column(
        String(50),
        nullable=False,
        comment="Source of learning"
    )
    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
        comment="Creation timestamp"
    )
    
    user = relationship("User", backref="facts")
    
    def __repr__(self):
        return f"<UserFact(id={self.id}, user_id={self.user_id}, category='{self.category}', fact='{self.fact_text[:50]}...')>"
        
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": str(self.user_id),
            "fact_text": self.fact_text,
            "category": self.category,
            "source": self.source,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
