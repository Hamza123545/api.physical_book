"""
Personalized Content Cache Model

Stores personalized chapter content to reduce OpenAI API costs and improve response times.
"""

import uuid
from datetime import datetime, timedelta
from sqlalchemy import Column, String, Text, DateTime, Integer, Index
from sqlalchemy.dialects.postgresql import UUID

from app.config import Base


class PersonalizedContentCache(Base):
    """
    Model for caching personalized content.

    Stores adapted chapter versions based on user profile hash.
    Cache entries expire after 30 days by default.
    """
    __tablename__ = "personalized_content_cache"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    chapter_id = Column(String, nullable=False, index=True)
    cache_key = Column(String(64), nullable=False, unique=True, index=True)  # MD5 hash of chapter_id + user profile
    original_content = Column(Text, nullable=False)
    personalized_content = Column(Text, nullable=False)
    model_used = Column(String(50), nullable=True)  # e.g., "gpt-4-turbo-preview"
    tokens_used = Column(Integer, nullable=True)  # OpenAI token count
    generation_time_ms = Column(Integer, nullable=True)  # Time to generate (for analytics)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True, index=True)  # Cache TTL (30 days default)

    def __repr__(self):
        return f"<PersonalizedContentCache(chapter_id='{self.chapter_id}', cache_key='{self.cache_key[:8]}...')>"

    @classmethod
    def set_default_expiration(cls, days=30):
        """Calculate default expiration date (30 days from now)."""
        return datetime.utcnow() + timedelta(days=days)


# Composite index for fast lookups
Index('idx_cache_lookup', PersonalizedContentCache.chapter_id, PersonalizedContentCache.cache_key)
