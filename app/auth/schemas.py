"""
Authentication Schemas

Pydantic models for request/response validation in authentication endpoints.
"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime
import uuid


class UserSignupRequest(BaseModel):
    """Request schema for user signup."""
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., min_length=8, max_length=100, description="User's password")
    full_name: Optional[str] = Field(None, max_length=100, description="User's full name")

    @validator("password")
    def validate_password(cls, v):
        """Validate password complexity."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(char.isdigit() for char in v):
            raise ValueError("Password must contain at least one digit")
        if not any(char.isupper() for char in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(char.islower() for char in v):
            raise ValueError("Password must contain at least one lowercase letter")
        return v


class UserSigninRequest(BaseModel):
    """Request schema for user signin."""
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., description="User's password")


class UserResponse(BaseModel):
    """Response schema for user data."""
    id: uuid.UUID
    email: str
    full_name: Optional[str]
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # For Pydantic v2 (replaces orm_mode)


class TokenResponse(BaseModel):
    """Response schema for authentication tokens."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: Optional[str] = Field(None, description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")


class SignupResponse(BaseModel):
    """Response schema for signup endpoint."""
    success: bool = Field(default=True)
    message: str = Field(..., description="Success message")
    user: UserResponse
    tokens: TokenResponse


class SigninResponse(BaseModel):
    """Response schema for signin endpoint."""
    success: bool = Field(default=True)
    message: str = Field(..., description="Success message")
    user: UserResponse
    tokens: TokenResponse


class ErrorResponse(BaseModel):
    """Response schema for errors."""
    success: bool = Field(default=False)
    error: dict = Field(..., description="Error details")

    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": {
                    "code": "AUTH_ERROR",
                    "message": "Authentication failed",
                    "details": {}
                }
            }
        }


class TokenData(BaseModel):
    """Data extracted from JWT token."""
    user_id: uuid.UUID
    email: str
    exp: datetime
