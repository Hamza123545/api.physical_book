"""
User Background Routes

FastAPI endpoints for user background management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.api.user.service import UserBackgroundService
from app.api.user.schemas import (
    UserBackgroundCreate,
    UserBackgroundResponse,
    BackgroundSubmitResponse
)
from app.auth.service import AuthService
from app.auth.schemas import ErrorResponse
from app.config import get_db
from app.utils.logger import setup_logger
from app.services.personalization_service import PersonalizationService

logger = setup_logger(__name__)

router = APIRouter()
security = HTTPBearer()


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
    "/background",
    response_model=BackgroundSubmitResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Background information saved successfully"},
        401: {"model": ErrorResponse, "description": "Unauthorized - invalid token"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Submit User Background",
    description="Create or update authenticated user's background information for content personalization"
)
async def submit_background(
    background_data: UserBackgroundCreate,
    user_id = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Submit or update user background information.

    This endpoint allows authenticated users to provide their experience levels,
    learning goals, and professional context for personalized content recommendations.

    Args:
        background_data: User background information
        user_id: Authenticated user's UUID (from token)
        db: Database session

    Returns:
        BackgroundSubmitResponse with saved background data

    Raises:
        HTTPException: If save fails
    """
    try:
        background, error = await UserBackgroundService.create_or_update_background(
            db, user_id, background_data
        )

        if error:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "success": False,
                    "error": {
                        "code": "BACKGROUND_SAVE_FAILED",
                        "message": error,
                        "details": {}
                    }
                }
            )

        return BackgroundSubmitResponse(
            success=True,
            message="Background information saved successfully",
            background=UserBackgroundResponse.from_orm(background)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in submit_background endpoint: {e}")
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


@router.get(
    "/background",
    response_model=UserBackgroundResponse,
    responses={
        200: {"description": "Background information retrieved successfully"},
        401: {"model": ErrorResponse, "description": "Unauthorized - invalid token"},
        404: {"model": ErrorResponse, "description": "Background not found"}
    },
    summary="Get User Background",
    description="Retrieve authenticated user's background information"
)
async def get_background(
    user_id = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get authenticated user's background information.

    Args:
        user_id: Authenticated user's UUID (from token)
        db: Database session

    Returns:
        UserBackgroundResponse with background data

    Raises:
        HTTPException: If background not found
    """
    try:
        background = UserBackgroundService.get_background(db, user_id)

        if not background:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "error": {
                        "code": "BACKGROUND_NOT_FOUND",
                        "message": "Background information not found for this user",
                        "details": {}
                    }
                }
            )

        return UserBackgroundResponse.from_orm(background)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_background endpoint: {e}")
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


@router.delete(
    "/background",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Background information deleted successfully"},
        401: {"model": ErrorResponse, "description": "Unauthorized - invalid token"},
        404: {"model": ErrorResponse, "description": "Background not found"}
    },
    summary="Delete User Background",
    description="Delete authenticated user's background information"
)
async def delete_background(
    user_id = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Delete authenticated user's background information.

    Args:
        user_id: Authenticated user's UUID (from token)
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException: If deletion fails
    """
    try:
        success, error = UserBackgroundService.delete_background(db, user_id)

        if not success:
            status_code = status.HTTP_404_NOT_FOUND if "not found" in error.lower() else status.HTTP_500_INTERNAL_SERVER_ERROR
            raise HTTPException(
                status_code=status_code,
                detail={
                    "success": False,
                    "error": {
                        "code": "BACKGROUND_DELETE_FAILED",
                        "message": error,
                        "details": {}
                    }
                }
            )

        return {
            "success": True,
            "message": "Background information deleted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in delete_background endpoint: {e}")
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


@router.get(
    "/personalize/chapter",
    responses={
        200: {"description": "Personalized chapter content retrieved successfully"},
        401: {"model": ErrorResponse, "description": "Unauthorized - invalid token"},
        404: {"model": ErrorResponse, "description": "Chapter not found"},
        500: {"model": ErrorResponse, "description": "Personalization failed"}
    },
    summary="Get Personalized Chapter",
    description="Retrieve chapter content personalized based on authenticated user's background"
)
async def get_personalized_chapter(
    chapter_path: str,
    user_id = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get personalized chapter content.

    This endpoint retrieves a chapter from the textbook and personalizes it based on
    the authenticated user's background (experience levels, learning goals, role).

    Args:
        chapter_path: Relative path to chapter file (e.g., "intro/physical-ai-foundations.md")
        user_id: Authenticated user's UUID (from token)
        db: Database session

    Returns:
        JSON response with personalized markdown content

    Raises:
        HTTPException: If chapter not found or personalization fails
    """
    try:
        personalized_content, error = await PersonalizationService.get_personalized_chapter(
            db, str(user_id), chapter_path
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
                            "details": {"chapter_path": chapter_path}
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
                            "details": {"chapter_path": chapter_path}
                        }
                    }
                )

        return {
            "success": True,
            "chapter_path": chapter_path,
            "content": personalized_content,
            "personalized": personalized_content is not None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_personalized_chapter endpoint: {e}")
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
