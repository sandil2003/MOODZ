import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class UserFact(Base):
    """
    UserFact model for storing facts about users.
    
    Stores personal information learned about users over time,
    categorized and sourced for context and filtering.
    
    Attributes:
        id: Integer primary key
        user_id: Foreign key to users table (UUID)
        fact_text: Text content of the fact (e.g., "User has a dog named Rex.")
        category: Category of the fact ("Personal", "Work", "Family")
        source: How the fact was learned ("conversation" or "manual_input")
        created_at: Timestamp when fact was recorded
    """
    
    __tablename__ = "userfacts"
    
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
    
    # Fact Text
    fact_text = Column(
        Text,
        nullable=False,
        comment="'User has a dog named Rex.'"
    )
    
    # Category
    category = Column(
        String(50),
        nullable=False,
        index=True,
        comment="'Personal', 'Work', 'Family'. Helps filtering."
    )
    
    # Source
    source = Column(
        String(50),
        nullable=False,
        comment="'conversation' or 'manual_input'."
    )
    
    # Timestamp
    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
        comment="Context for the agent ('You told me this 2 years ago')."
    )
    
    # Relationship to User
    user = relationship("User", backref="facts")
    
    def __repr__(self):
        return f"<UserFact(id={self.id}, user_id={self.user_id}, category='{self.category}', fact='{self.fact_text[:50]}...')>"
    
    def to_dict(self):
        """Convert user fact object to dictionary."""
        return {
            "id": self.id,
            "user_id": str(self.user_id),
            "fact_text": self.fact_text,
            "category": self.category,
            "source": self.source,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
