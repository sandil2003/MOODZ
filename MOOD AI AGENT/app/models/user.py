import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base


class User(Base):
    """
    User model for storing user information and preferences.
    
    Attributes:
        id: UUID primary key
        email: User email (optional, for future auth/login)
        name: User's name (required)
        preferences: JSONB field for storing user preferences (tone, verbose, etc.)
        created_at: Timestamp when user was created
        last_active: Timestamp of last user activity
        hashed_password: Encrypted password (never store plain text)
        is_active: Flag to ban users or handle email verification
        role: User role for admin panel functionality
    """
    
    __tablename__ = "users"
    
    # Primary Key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        nullable=False,
        index=True,
        comment="Primary Key - UUID"
    )
    
    # User Information
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
        comment="So the agent knows what to call the user (e.g., 'John')"
    )
    
    # Preferences stored as JSONB
    preferences = Column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Crucial. Store things like {'tone': 'friendly', 'verbose': false}. JSONB is faster than text metadata."
    )
    
    # Timestamps
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
        comment="To welcome back a user ('I haven't seen you in a week!')"
    )
    
    # Authentication & Security
    hashed_password = Column(
        Text,
        nullable=True,
        comment="Added to store the encrypted password (never store plain text!)"
    )
    
    # Account Status
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Added to allow you to ban users or handle email verification flows without deleting the record"
    )
    
    # Role-based Access
    role = Column(
        String(50),
        nullable=False,
        default="user",
        comment="Added in case you want an 'Admin' panel later to view all users"
    )
    
    def __repr__(self):
        return f"<User(id={self.id}, name='{self.name}', email='{self.email}', role='{self.role}')>"
    
    def to_dict(self):
        """Convert user object to dictionary."""
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
        """Update the last_active timestamp to current time."""
        self.last_active = datetime.utcnow()
