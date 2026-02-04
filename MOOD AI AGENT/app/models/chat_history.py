import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class ChatHistory(Base):
    """
    ChatHistory model for storing individual chat messages.
    
    Each message (user or assistant) is stored as a separate row.
    Messages are grouped by session_id to form conversations.
    
    """
    
    __tablename__ = "chat_history"
    
    # Primary Key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        nullable=False,
        comment="Primary Key - UUID"
    )
    
    # Foreign Key to User
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User who sent/received this message"
    )
    
    # Session ID to group messages
    session_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="Groups messages into conversations"
    )
    
    # Role: user or assistant
    role = Column(
        String(20),
        nullable=False,
        comment="Either 'user' or 'assistant'"
    )
    
    # Message content
    content = Column(
        Text,
        nullable=False,
        comment="The actual message text"
    )
    
    # Timestamp
    timestamp = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
        comment="When the message was created"
    )
    
    # Deep search flag
    deep_search = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether deep search was used"
    )
    
    # Composite indexes for efficient queries
    __table_args__ = (
        Index('idx_user_session', 'user_id', 'session_id'),
        Index('idx_user_timestamp', 'user_id', 'timestamp'),
    )
    
    def __repr__(self):
        content_preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"<ChatHistory(id={self.id}, role='{self.role}', content='{content_preview}')>"
    
    def to_dict(self):
        #Convert chat message to dictionary.
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "session_id": str(self.session_id),
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "deep_search": self.deep_search
        }
