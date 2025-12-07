from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID


class UserBase(BaseModel):
    """Base user schema with common fields."""
    name: str = Field(..., min_length=1, max_length=255, description="User's name")
    email: Optional[EmailStr] = Field(None, description="User's email for authentication")
    preferences: Dict[str, Any] = Field(
        default_factory=dict,
        description="User preferences stored as JSON (e.g., {'tone': 'friendly', 'verbose': false})"
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
                    "verbose": False,
                    "language": "en"
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
