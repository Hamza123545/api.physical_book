"""
Authentication Configuration

JWT token settings and security configuration for user authentication.
"""

import os
from datetime import timedelta
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class AuthSettings(BaseSettings):
    """
    Authentication configuration settings.

    Loads JWT secret key, algorithm, and token expiration settings from environment variables.
    """

    # JWT Settings
    jwt_secret_key: str = Field(
        default="your-secret-key-change-in-production",
        validation_alias="JWT_SECRET_KEY"
    )
    jwt_algorithm: str = Field(default="HS256", validation_alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=30,
        validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    refresh_token_expire_days: int = Field(
        default=7,
        validation_alias="REFRESH_TOKEN_EXPIRE_DAYS"
    )

    # Password Settings
    password_min_length: int = 8
    password_max_length: int = 100

    # Security Settings
    bcrypt_rounds: int = 12  # Number of hashing rounds for bcrypt

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


# Global auth settings instance
auth_settings = AuthSettings()


# Token expiration deltas
ACCESS_TOKEN_EXPIRE = timedelta(minutes=auth_settings.access_token_expire_minutes)
REFRESH_TOKEN_EXPIRE = timedelta(days=auth_settings.refresh_token_expire_days)
