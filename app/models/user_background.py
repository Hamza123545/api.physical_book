"""
User Background Model

SQLAlchemy model for storing user experience and background information.
Used for content personalization.
"""

from sqlalchemy import Column, String, Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()


class UserBackground(Base):
    """
    User background information for content personalization.

    Attributes:
        id: UUID primary key
        user_id: Foreign key to users table
        software_experience: Experience level with software (beginner/intermediate/advanced)
        hardware_experience: Experience level with hardware (beginner/intermediate/advanced)
        robotics_experience: Experience level with robotics (none/beginner/intermediate/advanced)
        programming_languages: Comma-separated list of known languages
        learning_goals: User's learning objectives
        current_role: Current professional role (student/professional/hobbyist/researcher)
        industry: Industry background (optional)
        created_at: Record creation timestamp
        updated_at: Last update timestamp
    """
    __tablename__ = "user_backgrounds"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    # Experience levels
    software_experience = Column(String, nullable=False)  # beginner/intermediate/advanced
    hardware_experience = Column(String, nullable=False)  # beginner/intermediate/advanced
    robotics_experience = Column(String, nullable=False)  # none/beginner/intermediate/advanced

    # Skills and goals
    programming_languages = Column(String, nullable=True)  # Comma-separated: python,c++,javascript
    learning_goals = Column(String, nullable=True)  # Free text

    # Professional context
    current_role = Column(String, nullable=False)  # student/professional/hobbyist/researcher
    industry = Column(String, nullable=True)  # Optional industry background

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<UserBackground(user_id={self.user_id}, software={self.software_experience}, hardware={self.hardware_experience})>"
