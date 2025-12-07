from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional
from datetime import datetime
from uuid import UUID


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
            # Allow custom categories but could warn
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
                    ],
                    "Work": [
                        {
                            "id": 2,
                            "user_id": "123e4567-e89b-12d3-a456-426614174000",
                            "fact_text": "User works as a software engineer.",
                            "category": "Work",
                            "source": "conversation",
                            "created_at": "2025-12-07T14:35:00"
                        }
                    ]
                },
                "total_facts": 2
            }
        }
    )
