"""
User Background Service

Business logic for user background management.
"""

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional, Tuple
import uuid

from app.models.user_background import UserBackground
from app.api.user.schemas import UserBackgroundCreate
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class UserBackgroundService:
    """Service for user background operations."""

    @staticmethod
    async def create_or_update_background(
        db: Session,
        user_id: uuid.UUID,
        background_data: UserBackgroundCreate
    ) -> Tuple[Optional[UserBackground], Optional[str]]:
        """
        Create or update user background information.

        Args:
            db: Database session
            user_id: User's UUID
            background_data: Background information

        Returns:
            Tuple of (UserBackground object, error message)
            If successful: (UserBackground, None)
            If failed: (None, error_message)
        """
        try:
            # Check if background already exists
            existing = db.query(UserBackground).filter(
                UserBackground.user_id == user_id
            ).first()

            if existing:
                # Update existing background
                for key, value in background_data.dict().items():
                    setattr(existing, key, value)

                db.commit()
                db.refresh(existing)

                logger.info(f"Updated background for user: {user_id}")
                return existing, None
            else:
                # Create new background
                new_background = UserBackground(
                    user_id=user_id,
                    **background_data.dict()
                )

                db.add(new_background)
                db.commit()
                db.refresh(new_background)

                logger.info(f"Created background for user: {user_id}")
                return new_background, None

        except IntegrityError as e:
            db.rollback()
            logger.error(f"Database integrity error during background save: {e}")
            return None, "Failed to save background information"
        except Exception as e:
            db.rollback()
            logger.error(f"Unexpected error during background save: {e}")
            return None, f"An error occurred: {str(e)}"

    @staticmethod
    def get_background(
        db: Session,
        user_id: uuid.UUID
    ) -> Optional[UserBackground]:
        """
        Get user background information.

        Args:
            db: Database session
            user_id: User's UUID

        Returns:
            UserBackground object if found, None otherwise
        """
        try:
            background = db.query(UserBackground).filter(
                UserBackground.user_id == user_id
            ).first()

            if background:
                logger.info(f"Retrieved background for user: {user_id}")
            else:
                logger.info(f"No background found for user: {user_id}")

            return background

        except Exception as e:
            logger.error(f"Error retrieving background: {e}")
            return None

    @staticmethod
    def delete_background(
        db: Session,
        user_id: uuid.UUID
    ) -> Tuple[bool, Optional[str]]:
        """
        Delete user background information.

        Args:
            db: Database session
            user_id: User's UUID

        Returns:
            Tuple of (success boolean, error message)
        """
        try:
            background = db.query(UserBackground).filter(
                UserBackground.user_id == user_id
            ).first()

            if not background:
                return False, "Background not found"

            db.delete(background)
            db.commit()

            logger.info(f"Deleted background for user: {user_id}")
            return True, None

        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting background: {e}")
            return False, f"Failed to delete background: {str(e)}"
