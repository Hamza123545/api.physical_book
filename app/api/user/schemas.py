"""
User Background Schemas

Pydantic models for user background request/response validation.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Literal
from datetime import datetime
import uuid


class UserBackgroundCreate(BaseModel):
    """Request schema for creating/updating user background."""
    software_experience: Literal["beginner", "intermediate", "advanced"] = Field(
        ...,
        description="Experience level with software development"
    )
    hardware_experience: Literal["beginner", "intermediate", "advanced"] = Field(
        ...,
        description="Experience level with hardware/electronics"
    )
    robotics_experience: Literal["none", "beginner", "intermediate", "advanced"] = Field(
        ...,
        description="Experience level with robotics"
    )
    programming_languages: Optional[str] = Field(
        None,
        max_length=500,
        description="Comma-separated list of known programming languages (e.g., python,c++,javascript)"
    )
    learning_goals: Optional[str] = Field(
        None,
        max_length=1000,
        description="User's learning objectives and goals"
    )
    current_role: Literal["student", "professional", "hobbyist", "researcher"] = Field(
        ...,
        description="Current professional or educational role"
    )
    industry: Optional[str] = Field(
        None,
        max_length=200,
        description="Industry background (optional)"
    )

    @validator("programming_languages")
    def validate_programming_languages(cls, v):
        """Validate and normalize programming languages list."""
        if v:
            # Remove extra spaces, convert to lowercase
            langs = [lang.strip().lower() for lang in v.split(",") if lang.strip()]
            return ",".join(langs)
        return v


class UserBackgroundResponse(BaseModel):
    """Response schema for user background data."""
    id: uuid.UUID
    user_id: uuid.UUID
    software_experience: str
    hardware_experience: str
    robotics_experience: str
    programming_languages: Optional[str]
    learning_goals: Optional[str]
    current_role: str
    industry: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # For Pydantic v2


class BackgroundSubmitResponse(BaseModel):
    """Response schema for background submission."""
    success: bool = Field(default=True)
    message: str = Field(..., description="Success message")
    background: UserBackgroundResponse
