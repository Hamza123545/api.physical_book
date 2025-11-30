"""
Authentication Service

Business logic for user authentication, password hashing, and JWT token generation.
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import uuid

from app.models.user import User
from app.auth.config import auth_settings, ACCESS_TOKEN_EXPIRE, REFRESH_TOKEN_EXPIRE
from app.auth.schemas import UserSignupRequest, UserSigninRequest, TokenData
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Service for user authentication operations."""

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password using bcrypt.

        Args:
            password: Plain text password

        Returns:
            Hashed password string
        """
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.

        Args:
            plain_password: Plain text password
            hashed_password: Hashed password from database

        Returns:
            True if password matches, False otherwise
        """
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def create_access_token(user_id: uuid.UUID, email: str) -> Tuple[str, datetime]:
        """
        Create a JWT access token.

        Args:
            user_id: User's UUID
            email: User's email address

        Returns:
            Tuple of (token string, expiration datetime)
        """
        expire = datetime.utcnow() + ACCESS_TOKEN_EXPIRE
        to_encode = {
            "sub": str(user_id),
            "email": email,
            "exp": expire,
            "type": "access"
        }
        encoded_jwt = jwt.encode(
            to_encode,
            auth_settings.jwt_secret_key,
            algorithm=auth_settings.jwt_algorithm
        )
        return encoded_jwt, expire

    @staticmethod
    def create_refresh_token(user_id: uuid.UUID, email: str) -> Tuple[str, datetime]:
        """
        Create a JWT refresh token.

        Args:
            user_id: User's UUID
            email: User's email address

        Returns:
            Tuple of (token string, expiration datetime)
        """
        expire = datetime.utcnow() + REFRESH_TOKEN_EXPIRE
        to_encode = {
            "sub": str(user_id),
            "email": email,
            "exp": expire,
            "type": "refresh"
        }
        encoded_jwt = jwt.encode(
            to_encode,
            auth_settings.jwt_secret_key,
            algorithm=auth_settings.jwt_algorithm
        )
        return encoded_jwt, expire

    @staticmethod
    def verify_token(token: str) -> Optional[TokenData]:
        """
        Verify and decode a JWT token.

        Args:
            token: JWT token string

        Returns:
            TokenData if valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token,
                auth_settings.jwt_secret_key,
                algorithms=[auth_settings.jwt_algorithm]
            )
            user_id: str = payload.get("sub")
            email: str = payload.get("email")
            exp: int = payload.get("exp")

            if user_id is None or email is None:
                return None

            return TokenData(
                user_id=uuid.UUID(user_id),
                email=email,
                exp=datetime.fromtimestamp(exp)
            )
        except JWTError as e:
            logger.error(f"JWT verification failed: {e}")
            return None

    @staticmethod
    async def signup_user(
        db: Session,
        signup_data: UserSignupRequest
    ) -> Tuple[Optional[User], Optional[str]]:
        """
        Create a new user account.

        Args:
            db: Database session
            signup_data: User signup request data

        Returns:
            Tuple of (User object, error message)
            If successful: (User, None)
            If failed: (None, error_message)
        """
        try:
            # Check if user already exists
            existing_user = db.query(User).filter(User.email == signup_data.email).first()
            if existing_user:
                return None, "User with this email already exists"

            # Hash password
            hashed_password = AuthService.hash_password(signup_data.password)

            # Create new user
            new_user = User(
                email=signup_data.email,
                hashed_password=hashed_password,
                full_name=signup_data.full_name,
                is_active=True,
                is_verified=False  # Email verification can be added later
            )

            db.add(new_user)
            db.commit()
            db.refresh(new_user)

            logger.info(f"User created successfully: {new_user.email}")
            return new_user, None

        except IntegrityError as e:
            db.rollback()
            logger.error(f"Database integrity error during signup: {e}")
            return None, "User with this email already exists"
        except Exception as e:
            db.rollback()
            logger.error(f"Unexpected error during signup: {e}")
            return None, f"An error occurred during signup: {str(e)}"

    @staticmethod
    async def signin_user(
        db: Session,
        signin_data: UserSigninRequest
    ) -> Tuple[Optional[User], Optional[str]]:
        """
        Authenticate a user and return user object.

        Args:
            db: Database session
            signin_data: User signin request data

        Returns:
            Tuple of (User object, error message)
            If successful: (User, None)
            If failed: (None, error_message)
        """
        try:
            # Find user by email
            user = db.query(User).filter(User.email == signin_data.email).first()
            if not user:
                return None, "Invalid email or password"

            # Verify password
            if not AuthService.verify_password(signin_data.password, user.hashed_password):
                return None, "Invalid email or password"

            # Check if account is active
            if not user.is_active:
                return None, "Account is inactive. Please contact support."

            logger.info(f"User signed in successfully: {user.email}")
            return user, None

        except Exception as e:
            logger.error(f"Unexpected error during signin: {e}")
            return None, f"An error occurred during signin: {str(e)}"

    @staticmethod
    def get_user_by_id(db: Session, user_id: uuid.UUID) -> Optional[User]:
        """
        Get user by ID.

        Args:
            db: Database session
            user_id: User's UUID

        Returns:
            User object if found, None otherwise
        """
        try:
            return db.query(User).filter(User.id == user_id).first()
        except Exception as e:
            logger.error(f"Error fetching user by ID: {e}")
            return None
