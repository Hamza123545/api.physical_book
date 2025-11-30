"""
Translation Cache Model

Stores translated chapter content to reduce OpenAI API costs and improve response times.
"""

import uuid
from datetime import datetime, timedelta
from sqlalchemy import Column, String, Text, DateTime, Integer, Index
from sqlalchemy.dialects.postgresql import UUID

from app.config import Base


class TranslationCache(Base):
    """
    Model for caching translated content.

    Stores translated chapter versions based on chapter_id and target language.
    Cache entries expire after 30 days by default.
    """
    __tablename__ = "translation_cache"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    chapter_id = Column(String, nullable=False, index=True)
    cache_key = Column(String(64), nullable=False, unique=True, index=True)  # MD5 hash of chapter_id + language
    source_language = Column(String(50), nullable=False, default="english")
    target_language = Column(String(50), nullable=False, default="urdu")
    original_content = Column(Text, nullable=False)
    translated_content = Column(Text, nullable=False)
    model_used = Column(String(50), nullable=True)  # e.g., "gpt-4-turbo-preview"
    tokens_used = Column(Integer, nullable=True)  # OpenAI token count
    generation_time_ms = Column(Integer, nullable=True)  # Time to generate (for analytics)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True, index=True)  # Cache TTL (30 days default)

    def __repr__(self):
        return f"<TranslationCache(chapter_id='{self.chapter_id}', {self.source_language}->{self.target_language}, cache_key='{self.cache_key[:8]}...')>"

    @classmethod
    def set_default_expiration(cls, days=30):
        """Calculate default expiration date (30 days from now)."""
        return datetime.utcnow() + timedelta(days=days)


# Composite index for fast lookups
Index('idx_translation_cache_lookup', TranslationCache.chapter_id, TranslationCache.cache_key)
