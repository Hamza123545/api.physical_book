"""
Content Personalization Routes

FastAPI endpoints for content personalization functionality.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional
import uuid

from app.services.personalization_service import PersonalizationService
from app.auth.service import AuthService
from app.auth.schemas import ErrorResponse
from app.config import get_db
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter()
security = HTTPBearer()


class PersonalizeRequest(BaseModel):
    """Request schema for content personalization."""
    chapter_id: str = Field(..., description="Chapter identifier (e.g., 'intro/physical-ai-foundations.md')")
    user_id: Optional[uuid.UUID] = Field(None, description="User UUID (optional, can use auth token)")


class PersonalizeResponse(BaseModel):
    """Response schema for personalized content."""
    success: bool
    chapter_id: str
    personalized_content: str
    cache_hit: bool = Field(default=False, description="Whether content was served from cache")
    metadata: Optional[dict] = Field(default=None, description="Additional metadata about personalization")


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Dependency to extract and verify user ID from JWT token.

    Args:
        credentials: JWT token from Authorization header

    Returns:
        User UUID

    Raises:
        HTTPException: If token is invalid
    """
    token_data = AuthService.verify_token(credentials.credentials)

    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "success": False,
                "error": {
                    "code": "INVALID_TOKEN",
                    "message": "Invalid or expired token",
                    "details": {}
                }
            }
        )

    return token_data.user_id


@router.post(
    "/personalize",
    response_model=PersonalizeResponse,
    responses={
        200: {"description": "Personalized content generated successfully"},
        401: {"model": ErrorResponse, "description": "Unauthorized - invalid token"},
        404: {"model": ErrorResponse, "description": "Chapter not found"},
        500: {"model": ErrorResponse, "description": "Personalization failed"}
    },
    summary="Personalize Chapter Content",
    description="Generate personalized version of a chapter based on user's background and preferences"
)
async def personalize_content(
    request: PersonalizeRequest,
    user_id = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Personalize chapter content for a specific user.

    This endpoint generates a personalized version of a chapter by:
    1. Retrieving the user's background/preferences from the database
    2. Checking if a personalized version exists in cache
    3. If not cached, using OpenAI to adapt the content
    4. Storing the personalized content in cache for future requests
    5. Returning the personalized markdown content

    Args:
        request: PersonalizeRequest with chapter_id and optional user_id
        user_id: Authenticated user's UUID (from token)
        db: Database session

    Returns:
        PersonalizeResponse with personalized content and metadata

    Raises:
        HTTPException: If chapter not found or personalization fails
    """
    try:
        # Use user_id from token (auth) unless specified in request
        target_user_id = request.user_id if request.user_id else user_id

        logger.info(f"Personalizing chapter {request.chapter_id} for user {target_user_id}")

        # Get personalized content from service (with caching)
        personalized_content, error, cache_hit, metadata = await PersonalizationService.get_personalized_chapter(
            db,
            str(target_user_id),
            request.chapter_id
        )

        if error:
            if "not found" in error.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "success": False,
                        "error": {
                            "code": "CHAPTER_NOT_FOUND",
                            "message": error,
                            "details": {"chapter_id": request.chapter_id}
                        }
                    }
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail={
                        "success": False,
                        "error": {
                            "code": "PERSONALIZATION_FAILED",
                            "message": error,
                            "details": {"chapter_id": request.chapter_id}
                        }
                    }
                )

        # Add user_id to metadata
        if metadata:
            metadata["user_id"] = str(target_user_id)
        else:
            metadata = {"user_id": str(target_user_id)}

        return PersonalizeResponse(
            success=True,
            chapter_id=request.chapter_id,
            personalized_content=personalized_content,
            cache_hit=cache_hit,
            metadata=metadata
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in personalize_content endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                    "details": {"error": str(e)}
                }
            }
        )
