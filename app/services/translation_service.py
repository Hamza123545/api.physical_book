"""
Translation Service for Urdu Content

Translates textbook content from English to Urdu using OpenAI.
Implements intelligent caching to minimize API costs.
"""

from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
import os
import hashlib
from datetime import datetime, timedelta
import time

from app.utils.logger import setup_logger
from app.config import openai_client, settings

logger = setup_logger(__name__)


class TranslationService:
    """Service for translating textbook content to Urdu."""

    @staticmethod
    def _generate_cache_key(chapter_id: str, target_language: str = "urdu") -> str:
        """
        Generate a unique cache key for translated content.

        Args:
            chapter_id: Chapter identifier
            target_language: Target language (default: "urdu")

        Returns:
            MD5 hash of the combination
        """
        cache_string = f"{chapter_id}:{target_language}"
        return hashlib.md5(cache_string.encode()).hexdigest()

    @staticmethod
    def _check_cache(
        db: Session,
        chapter_id: str,
        cache_key: str
    ) -> Optional[Any]:
        """
        Check if translated content exists in cache.

        Args:
            db: Database session
            chapter_id: Chapter identifier
            cache_key: Cache key (MD5 hash)

        Returns:
            TranslationCache object if found and not expired, None otherwise
        """
        # Import here to avoid circular dependency
        from app.models.translation_cache import TranslationCache

        try:
            cached = db.query(TranslationCache).filter(
                TranslationCache.chapter_id == chapter_id,
                TranslationCache.cache_key == cache_key
            ).first()

            if cached:
                # Check if cache is expired
                if cached.expires_at and cached.expires_at < datetime.utcnow():
                    logger.info(f"Translation cache expired for {chapter_id}, cache_key={cache_key[:8]}")
                    # Delete expired cache
                    db.delete(cached)
                    db.commit()
                    return None

                logger.info(f"Translation cache HIT for {chapter_id}, cache_key={cache_key[:8]}")
                return cached

            logger.info(f"Translation cache MISS for {chapter_id}, cache_key={cache_key[:8]}")
            return None

        except Exception as e:
            logger.error(f"Error checking translation cache: {e}")
            return None

    @staticmethod
    def _save_to_cache(
        db: Session,
        chapter_id: str,
        cache_key: str,
        source_language: str,
        target_language: str,
        original_content: str,
        translated_content: str,
        model_used: str,
        tokens_used: int,
        generation_time_ms: int
    ) -> bool:
        """
        Save translated content to cache.

        Args:
            db: Database session
            chapter_id: Chapter identifier
            cache_key: Cache key (MD5 hash)
            source_language: Source language (e.g., "english")
            target_language: Target language (e.g., "urdu")
            original_content: Original markdown content
            translated_content: Translated markdown content
            model_used: OpenAI model used (e.g., "gpt-4-turbo-preview")
            tokens_used: Total tokens used for translation
            generation_time_ms: Time taken to generate (milliseconds)

        Returns:
            True if save successful, False otherwise
        """
        # Import here to avoid circular dependency
        from app.models.translation_cache import TranslationCache

        try:
            # Check if cache entry already exists
            existing = db.query(TranslationCache).filter(
                TranslationCache.cache_key == cache_key
            ).first()

            if existing:
                # Update existing cache
                existing.translated_content = translated_content
                existing.model_used = model_used
                existing.tokens_used = tokens_used
                existing.generation_time_ms = generation_time_ms
                existing.created_at = datetime.utcnow()
                existing.expires_at = TranslationCache.set_default_expiration(30)
            else:
                # Create new cache entry
                cache_entry = TranslationCache(
                    chapter_id=chapter_id,
                    cache_key=cache_key,
                    source_language=source_language,
                    target_language=target_language,
                    original_content=original_content,
                    translated_content=translated_content,
                    model_used=model_used,
                    tokens_used=tokens_used,
                    generation_time_ms=generation_time_ms,
                    expires_at=TranslationCache.set_default_expiration(30)
                )
                db.add(cache_entry)

            db.commit()
            logger.info(f"Saved to translation cache: {chapter_id}, cache_key={cache_key[:8]}")
            return True

        except Exception as e:
            db.rollback()
            logger.error(f"Error saving to translation cache: {e}")
            return False

    @staticmethod
    def _build_translation_prompt(
        content: str,
        target_language: str = "urdu"
    ) -> str:
        """
        Build a translation prompt for OpenAI.

        Args:
            content: Original chapter content in English
            target_language: Target language (default: "urdu")

        Returns:
            Formatted prompt string
        """
        prompt = f"""You are an expert translator specializing in technical and educational content translation from English to Urdu.

ORIGINAL CONTENT (English):
{content}

TASK:
Translate the above educational content about Physical AI and Humanoid Robotics into Urdu. Follow these critical requirements:

1. **Preserve Markdown Structure**: Maintain all markdown formatting (headings, lists, code blocks, links, images, etc.)
2. **Technical Terms**:
   - Keep technical terms, programming keywords, and API names in English
   - Provide Urdu translations for concepts while keeping English terms in parentheses when first introduced
   - Example: "Machine Learning (مشین لرننگ)" on first use, then use either form
3. **Code Blocks**:
   - DO NOT translate code, comments in code, variable names, or function names
   - Keep all code blocks exactly as they are
   - Only translate explanatory text outside code blocks
4. **Accuracy**:
   - Maintain technical accuracy and precision
   - Use formal Urdu suitable for educational/academic content
   - Preserve all links, URLs, and image paths exactly
5. **Readability**:
   - Write in clear, modern Urdu
   - Use appropriate technical vocabulary
   - Maintain the same pedagogical flow and structure
6. **Completeness**:
   - Translate ALL content (headings, paragraphs, lists, captions)
   - Do not skip or summarize any sections

Return ONLY the translated content in markdown format, without any preamble or explanation."""

        return prompt

    @staticmethod
    async def translate_content(
        db: Session,
        chapter_id: str,
        original_content: str,
        target_language: str = "urdu"
    ) -> Tuple[Optional[str], Optional[str], bool, Optional[dict]]:
        """
        Translate content to target language with caching.

        Args:
            db: Database session
            chapter_id: Chapter identifier
            original_content: Original markdown content in English
            target_language: Target language (default: "urdu")

        Returns:
            Tuple of (translated_content, error_message, cache_hit, metadata)
        """
        start_time = time.time()
        cache_hit = False
        metadata = {}

        try:
            # Generate cache key
            cache_key = TranslationService._generate_cache_key(chapter_id, target_language)

            # Check cache
            cached = TranslationService._check_cache(db, chapter_id, cache_key)

            if cached:
                # Cache hit - return cached translation
                cache_hit = True
                generation_time = int((time.time() - start_time) * 1000)
                metadata = {
                    "model_used": cached.model_used,
                    "tokens_used": cached.tokens_used,
                    "generation_time_ms": generation_time,
                    "cached_at": cached.created_at.isoformat() if cached.created_at else None,
                    "source_language": cached.source_language,
                    "target_language": cached.target_language
                }
                logger.info(f"Returning cached translation for chapter {chapter_id}")
                return cached.translated_content, None, cache_hit, metadata

            # Cache miss - generate translation
            logger.info(f"Generating {target_language} translation for chapter {chapter_id}")

            # Build translation prompt
            prompt = TranslationService._build_translation_prompt(
                original_content,
                target_language
            )

            # Call OpenAI API
            # Import settings here to get chat_model
            from app.config import settings as app_settings

            response = openai_client.chat.completions.create(
                model=app_settings.CHAT_MODEL if hasattr(app_settings, 'CHAT_MODEL') else "gpt-4-turbo-preview",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert translator specializing in technical and educational content translation."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Lower temperature for more consistent translations
                max_tokens=4000
            )

            translated_content = response.choices[0].message.content
            generation_time = int((time.time() - start_time) * 1000)

            # Calculate tokens used
            tokens_used = response.usage.total_tokens if response.usage else 0

            # Get model used
            model_used = app_settings.CHAT_MODEL if hasattr(app_settings, 'CHAT_MODEL') else "gpt-4-turbo-preview"

            # Save to cache
            TranslationService._save_to_cache(
                db,
                chapter_id,
                cache_key,
                "english",
                target_language,
                original_content,
                translated_content,
                model_used,
                tokens_used,
                generation_time
            )

            metadata = {
                "model_used": model_used,
                "tokens_used": tokens_used,
                "generation_time_ms": generation_time,
                "source_language": "english",
                "target_language": target_language
            }

            logger.info(f"Successfully translated content to {target_language} (took {generation_time}ms, {tokens_used} tokens)")

            return translated_content, None, cache_hit, metadata

        except Exception as e:
            logger.error(f"Error translating content: {e}")
            generation_time = int((time.time() - start_time) * 1000)
            metadata = {"generation_time_ms": generation_time}
            # On error, return original content
            return original_content, f"Translation failed: {str(e)}", False, metadata

    @staticmethod
    def read_chapter_content(chapter_path: str) -> Optional[str]:
        """
        Read chapter content from markdown file.

        Args:
            chapter_path: Path to the chapter markdown file

        Returns:
            File content as string, or None if not found
        """
        try:
            # Construct full path (assuming chapters are in book-source/docs/)
            base_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "book-source", "docs")
            full_path = os.path.join(base_path, chapter_path)

            if not os.path.exists(full_path):
                logger.error(f"Chapter file not found: {full_path}")
                return None

            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()

            logger.info(f"Successfully read chapter content from {chapter_path}")
            return content

        except Exception as e:
            logger.error(f"Error reading chapter content: {e}")
            return None

    @staticmethod
    async def get_translated_chapter(
        db: Session,
        chapter_path: str,
        target_language: str = "urdu"
    ) -> Tuple[Optional[str], Optional[str], bool, Optional[dict]]:
        """
        Get translated chapter content with caching.

        Workflow:
        1. Read original chapter content
        2. Generate cache key from chapter_id and target language
        3. Check cache for existing translation
        4. If cache miss, translate content using OpenAI
        5. Save to cache and return translated content

        Args:
            db: Database session
            chapter_path: Relative path to chapter file (e.g., "intro/physical-ai-foundations.md")
            target_language: Target language (default: "urdu")

        Returns:
            Tuple of (translated_content, error_message, cache_hit, metadata)
        """
        try:
            # Read original content
            original_content = TranslationService.read_chapter_content(chapter_path)

            if not original_content:
                return None, "Chapter content not found", False, {}

            # Extract chapter ID from path for caching
            chapter_id = chapter_path.replace("/", "_").replace(".md", "")

            # Translate content (with caching)
            translated_content, error, cache_hit, metadata = await TranslationService.translate_content(
                db,
                chapter_id,
                original_content,
                target_language
            )

            return translated_content, error, cache_hit, metadata

        except Exception as e:
            logger.error(f"Error getting translated chapter: {e}")
            return None, f"Failed to get translated chapter: {str(e)}", False, {}
