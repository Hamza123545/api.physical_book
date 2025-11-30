"""
Content Personalization Service

Uses FREE Gemini 2.5 Flash to adapt textbook content based on user background and experience level.
Implements intelligent caching to minimize API costs.
Falls back to OpenAI if Gemini is not configured.
"""

from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
import os
import hashlib
from datetime import datetime, timedelta
import time
from litellm import completion

from app.models.user_background import UserBackground
from app.models.personalized_content_cache import PersonalizedContentCache
from app.utils.logger import setup_logger
from app.config import settings, USE_GEMINI, GEMINI_API_KEY

logger = setup_logger(__name__)

# Configure Gemini API if enabled
if USE_GEMINI and GEMINI_API_KEY:
    os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY
    os.environ["GEMINI_API_VERSION"] = "v1"  # Use v1 API instead of v1beta
    logger.info("Gemini API configured for personalization service")


class PersonalizationService:
    """Service for personalizing textbook content based on user background."""

    @staticmethod
    def _generate_cache_key(
        chapter_id: str,
        user_background: UserBackground
    ) -> str:
        """
        Generate a unique cache key for personalized content.

        Args:
            chapter_id: Chapter identifier
            user_background: User background information

        Returns:
            MD5 hash of the combination
        """
        # Create a string representation of relevant background factors
        background_string = (
            f"{chapter_id}:"
            f"{user_background.software_experience}:"
            f"{user_background.hardware_experience}:"
            f"{user_background.robotics_experience}:"
            f"{user_background.current_role}:"
            f"{user_background.programming_languages or ''}"
        )

        return hashlib.md5(background_string.encode()).hexdigest()

    @staticmethod
    def _check_cache(
        db: Session,
        chapter_id: str,
        cache_key: str
    ) -> Optional[PersonalizedContentCache]:
        """
        Check if personalized content exists in cache.

        Args:
            db: Database session
            chapter_id: Chapter identifier
            cache_key: Cache key (MD5 hash)

        Returns:
            PersonalizedContentCache object if found and not expired, None otherwise
        """
        try:
            cached = db.query(PersonalizedContentCache).filter(
                PersonalizedContentCache.chapter_id == chapter_id,
                PersonalizedContentCache.cache_key == cache_key
            ).first()

            if cached:
                # Check if cache is expired
                if cached.expires_at and cached.expires_at < datetime.utcnow():
                    logger.info(f"Cache expired for {chapter_id}, cache_key={cache_key[:8]}")
                    # Delete expired cache
                    db.delete(cached)
                    db.commit()
                    return None

                logger.info(f"Cache HIT for {chapter_id}, cache_key={cache_key[:8]}")
                return cached

            logger.info(f"Cache MISS for {chapter_id}, cache_key={cache_key[:8]}")
            return None

        except Exception as e:
            logger.error(f"Error checking cache: {e}")
            return None

    @staticmethod
    def _save_to_cache(
        db: Session,
        chapter_id: str,
        cache_key: str,
        original_content: str,
        personalized_content: str,
        model_used: str,
        tokens_used: int,
        generation_time_ms: int
    ) -> bool:
        """
        Save personalized content to cache.

        Args:
            db: Database session
            chapter_id: Chapter identifier
            cache_key: Cache key (MD5 hash)
            original_content: Original markdown content
            personalized_content: Personalized markdown content
            model_used: OpenAI model used (e.g., "gpt-4-turbo-preview")
            tokens_used: Total tokens used for personalization
            generation_time_ms: Time taken to generate (milliseconds)

        Returns:
            True if save successful, False otherwise
        """
        try:
            # Check if cache entry already exists
            existing = db.query(PersonalizedContentCache).filter(
                PersonalizedContentCache.cache_key == cache_key
            ).first()

            if existing:
                # Update existing cache
                existing.personalized_content = personalized_content
                existing.model_used = model_used
                existing.tokens_used = tokens_used
                existing.generation_time_ms = generation_time_ms
                existing.created_at = datetime.utcnow()
                existing.expires_at = PersonalizedContentCache.set_default_expiration(30)
            else:
                # Create new cache entry
                cache_entry = PersonalizedContentCache(
                    chapter_id=chapter_id,
                    cache_key=cache_key,
                    original_content=original_content,
                    personalized_content=personalized_content,
                    model_used=model_used,
                    tokens_used=tokens_used,
                    generation_time_ms=generation_time_ms,
                    expires_at=PersonalizedContentCache.set_default_expiration(30)
                )
                db.add(cache_entry)

            db.commit()
            logger.info(f"Saved to cache: {chapter_id}, cache_key={cache_key[:8]}")
            return True

        except Exception as e:
            db.rollback()
            logger.error(f"Error saving to cache: {e}")
            return False

    @staticmethod
    def _build_personalization_prompt(
        content: str,
        user_background: UserBackground
    ) -> str:
        """
        Build a personalization prompt for OpenAI.

        Args:
            content: Original chapter content
            user_background: User background information

        Returns:
            Formatted prompt string
        """
        # Build user profile description
        profile_parts = []

        profile_parts.append(f"Experience Levels:")
        profile_parts.append(f"- Software: {user_background.software_experience}")
        profile_parts.append(f"- Hardware: {user_background.hardware_experience}")
        profile_parts.append(f"- Robotics: {user_background.robotics_experience}")

        if user_background.programming_languages:
            langs = user_background.programming_languages.replace(",", ", ")
            profile_parts.append(f"\nKnown Programming Languages: {langs}")

        profile_parts.append(f"\nCurrent Role: {user_background.current_role}")

        if user_background.learning_goals:
            profile_parts.append(f"\nLearning Goals: {user_background.learning_goals}")

        if user_background.industry:
            profile_parts.append(f"\nIndustry Background: {user_background.industry}")

        user_profile = "\n".join(profile_parts)

        # Build personalization instructions based on experience levels
        instructions = []

        # Software experience adaptations
        if user_background.software_experience == "beginner":
            instructions.append("- Explain software concepts in simple terms with analogies")
            instructions.append("- Include more detailed code comments")
            instructions.append("- Add step-by-step explanations for code examples")
        elif user_background.software_experience == "advanced":
            instructions.append("- Use more technical terminology")
            instructions.append("- Include advanced patterns and optimizations")
            instructions.append("- Reference related advanced concepts")

        # Hardware experience adaptations
        if user_background.hardware_experience == "beginner":
            instructions.append("- Explain hardware components with visual descriptions")
            instructions.append("- Include basic electronics concepts where relevant")
        elif user_background.hardware_experience == "advanced":
            instructions.append("- Reference specific hardware specifications")
            instructions.append("- Include technical details about sensors and actuators")

        # Robotics experience adaptations
        if user_background.robotics_experience in ["none", "beginner"]:
            instructions.append("- Provide foundational robotics context")
            instructions.append("- Explain why concepts matter in practical applications")
            instructions.append("- Include motivating real-world examples")
        elif user_background.robotics_experience == "advanced":
            instructions.append("- Reference advanced robotics topics")
            instructions.append("- Include connections to research papers or cutting-edge techniques")

        # Programming language adaptations
        if user_background.programming_languages:
            known_langs = user_background.programming_languages.split(",")
            if "python" in known_langs:
                instructions.append("- Emphasize Python-specific idioms and best practices")
            if "c++" in known_langs:
                instructions.append("- Include C++ performance considerations where relevant")
            if "javascript" in known_langs or "typescript" in known_langs:
                instructions.append("- Reference web-based robotics interfaces when applicable")

        # Role-based adaptations
        if user_background.current_role == "student":
            instructions.append("- Include learning exercises and practice problems")
            instructions.append("- Connect concepts to academic fundamentals")
        elif user_background.current_role == "professional":
            instructions.append("- Focus on practical applications and industry use cases")
            instructions.append("- Include production-ready code patterns")
        elif user_background.current_role == "researcher":
            instructions.append("- Reference research papers and theoretical foundations")
            instructions.append("- Include experimental approaches and evaluation metrics")
        elif user_background.current_role == "hobbyist":
            instructions.append("- Emphasize fun projects and creative applications")
            instructions.append("- Include accessible, low-cost alternatives")

        instructions_text = "\n".join(instructions)

        # Build final prompt
        prompt = f"""You are an expert educator personalizing robotics and physical AI content for a specific learner.

USER PROFILE:
{user_profile}

PERSONALIZATION INSTRUCTIONS:
{instructions_text}

ORIGINAL CONTENT:
{content}

TASK:
Adapt the above content to match this learner's profile. Maintain the same structure and key information, but:
1. Adjust technical depth and terminology to their experience levels
2. Use code examples in their known programming languages when possible
3. Add relevant context based on their role and learning goals
4. Keep the same markdown formatting and structure
5. Preserve all important technical accuracy
6. Make the content more engaging and relevant to this specific learner

Return ONLY the personalized content in markdown format, without any preamble or explanation."""

        return prompt

    @staticmethod
    async def personalize_content(
        db: Session,
        user_id: str,
        chapter_id: str,
        original_content: str
    ) -> Tuple[Optional[str], Optional[str], bool, Optional[dict]]:
        """
        Personalize content for a specific user with caching.

        Args:
            db: Database session
            user_id: User UUID
            chapter_id: Chapter identifier
            original_content: Original markdown content

        Returns:
            Tuple of (personalized_content, error_message, cache_hit, metadata)
        """
        start_time = time.time()
        cache_hit = False
        metadata = {}

        try:
            # Get user background
            background = db.query(UserBackground).filter(
                UserBackground.user_id == user_id
            ).first()

            if not background:
                # No background - return original content
                logger.info(f"No background found for user {user_id}, returning original content")
                return original_content, None, False, metadata

            # Generate cache key
            cache_key = PersonalizationService._generate_cache_key(chapter_id, background)

            # Check cache
            cached = PersonalizationService._check_cache(db, chapter_id, cache_key)

            if cached:
                # Cache hit - return cached content
                cache_hit = True
                generation_time = int((time.time() - start_time) * 1000)
                metadata = {
                    "model_used": cached.model_used,
                    "tokens_used": cached.tokens_used,
                    "generation_time_ms": generation_time,
                    "cached_at": cached.created_at.isoformat() if cached.created_at else None
                }
                logger.info(f"Returning cached content for user {user_id}, chapter {chapter_id}")
                return cached.personalized_content, None, cache_hit, metadata

            # Cache miss - generate personalized content
            logger.info(f"Generating personalized content for user {user_id}, chapter {chapter_id}")

            # Build personalization prompt
            prompt = PersonalizationService._build_personalization_prompt(
                original_content,
                background
            )

            # Call LiteLLM API (supports Gemini and OpenAI)
            # LiteLLM automatically routes to the correct provider based on model name
            response = completion(
                model=settings.CHAT_MODEL,  # Can be "gemini/gemini-2.5-flash" or "gpt-4-turbo-preview"
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert educator who personalizes technical content for individual learners."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=4000
            )

            personalized_content = response.choices[0].message.content
            generation_time = int((time.time() - start_time) * 1000)

            # Calculate tokens used
            tokens_used = response.usage.total_tokens if hasattr(response, 'usage') and response.usage else 0

            # Save to cache
            PersonalizationService._save_to_cache(
                db,
                chapter_id,
                cache_key,
                original_content,
                personalized_content,
                settings.CHAT_MODEL,
                tokens_used,
                generation_time
            )

            metadata = {
                "model_used": settings.CHAT_MODEL,
                "tokens_used": tokens_used,
                "generation_time_ms": generation_time
            }

            logger.info(f"Successfully personalized content for user {user_id} using {settings.CHAT_MODEL} (took {generation_time}ms, {tokens_used} tokens)")

            return personalized_content, None, cache_hit, metadata

        except Exception as e:
            logger.error(f"Error personalizing content: {e}")
            generation_time = int((time.time() - start_time) * 1000)
            metadata = {"generation_time_ms": generation_time}
            # On error, return original content
            return original_content, f"Personalization failed: {str(e)}", False, metadata

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
    async def get_personalized_chapter(
        db: Session,
        user_id: str,
        chapter_path: str
    ) -> Tuple[Optional[str], Optional[str], bool, Optional[dict]]:
        """
        Get personalized chapter content for a user with caching.

        Workflow:
        1. Read original chapter content
        2. Generate cache key from user background
        3. Check cache for existing personalized version
        4. If cache miss, personalize content using OpenAI
        5. Save to cache and return personalized content

        Args:
            db: Database session
            user_id: User UUID
            chapter_path: Relative path to chapter file (e.g., "intro/physical-ai-foundations.md")

        Returns:
            Tuple of (personalized_content, error_message, cache_hit, metadata)
        """
        try:
            # Read original content
            original_content = PersonalizationService.read_chapter_content(chapter_path)

            if not original_content:
                return None, "Chapter content not found", False, {}

            # Extract chapter ID from path for caching
            chapter_id = chapter_path.replace("/", "_").replace(".md", "")

            # Personalize content (with caching)
            personalized_content, error, cache_hit, metadata = await PersonalizationService.personalize_content(
                db,
                user_id,
                chapter_id,
                original_content
            )

            return personalized_content, error, cache_hit, metadata

        except Exception as e:
            logger.error(f"Error getting personalized chapter: {e}")
            return None, f"Failed to get personalized chapter: {str(e)}", False, {}
