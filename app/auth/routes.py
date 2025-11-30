"""
Authentication Routes

FastAPI endpoints for user signup and signin.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional

from app.auth.service import AuthService
from app.auth.schemas import (
    UserSignupRequest,
    UserSigninRequest,
    SignupResponse,
    SigninResponse,
    ErrorResponse,
    UserResponse,
    TokenResponse
)
from app.auth.config import auth_settings
from app.config import get_db
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter()
security = HTTPBearer()


@router.post(
    "/signup",
    response_model=SignupResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "User created successfully"},
        400: {"model": ErrorResponse, "description": "Bad request - validation error or user exists"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="User Signup",
    description="Create a new user account with email and password"
)
async def signup(
    signup_data: UserSignupRequest,
    db: Session = Depends(get_db)
):
    """
    Create a new user account.

    Args:
        signup_data: User signup request (email, password, full_name)
        db: Database session

    Returns:
        SignupResponse with user data and JWT tokens

    Raises:
        HTTPException: If signup fails (user exists, validation error, etc.)
    """
    try:
        # Create user
        user, error = await AuthService.signup_user(db, signup_data)

        if error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "error": {
                        "code": "SIGNUP_FAILED",
                        "message": error,
                        "details": {}
                    }
                }
            )

        # Generate tokens
        access_token, access_exp = AuthService.create_access_token(user.id, user.email)
        refresh_token, refresh_exp = AuthService.create_refresh_token(user.id, user.email)

        # Calculate expiration time in seconds
        expires_in = int((access_exp - user.created_at).total_seconds())

        return SignupResponse(
            success=True,
            message="User created successfully",
            user=UserResponse.from_orm(user),
            tokens=TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                expires_in=expires_in
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in signup endpoint: {e}")
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


@router.post(
    "/signin",
    response_model=SigninResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "User signed in successfully"},
        401: {"model": ErrorResponse, "description": "Unauthorized - invalid credentials"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="User Signin",
    description="Authenticate user and return JWT tokens"
)
async def signin(
    signin_data: UserSigninRequest,
    db: Session = Depends(get_db)
):
    """
    Authenticate a user and return JWT tokens.

    Args:
        signin_data: User signin request (email, password)
        db: Database session

    Returns:
        SigninResponse with user data and JWT tokens

    Raises:
        HTTPException: If signin fails (invalid credentials, inactive account, etc.)
    """
    try:
        # Authenticate user
        user, error = await AuthService.signin_user(db, signin_data)

        if error:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "success": False,
                    "error": {
                        "code": "AUTH_FAILED",
                        "message": error,
                        "details": {}
                    }
                }
            )

        # Generate tokens
        access_token, access_exp = AuthService.create_access_token(user.id, user.email)
        refresh_token, refresh_exp = AuthService.create_refresh_token(user.id, user.email)

        # Calculate expiration time in seconds
        from datetime import datetime
        expires_in = int((access_exp - datetime.utcnow()).total_seconds())

        return SigninResponse(
            success=True,
            message="User signed in successfully",
            user=UserResponse.from_orm(user),
            tokens=TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                expires_in=expires_in
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in signin endpoint: {e}")
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
    "/me",
    response_model=UserResponse,
    responses={
        200: {"description": "User profile retrieved successfully"},
        401: {"model": ErrorResponse, "description": "Unauthorized - invalid token"},
        404: {"model": ErrorResponse, "description": "User not found"}
    },
    summary="Get Current User",
    description="Get the current authenticated user's profile"
)
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Get the current authenticated user's profile.

    Args:
        credentials: JWT token from Authorization header
        db: Database session

    Returns:
        UserResponse with user data

    Raises:
        HTTPException: If token is invalid or user not found
    """
    try:
        # Verify token
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

        # Get user from database
        user = AuthService.get_user_by_id(db, token_data.user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "error": {
                        "code": "USER_NOT_FOUND",
                        "message": "User not found",
                        "details": {}
                    }
                }
            )

        return UserResponse.from_orm(user)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_current_user endpoint: {e}")
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
