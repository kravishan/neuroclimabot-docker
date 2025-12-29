"""
Feedback database model (SQLAlchemy).
Stores user feedback in database.
"""

from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, DateTime, Enum
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.models.base import Base


class FeedbackRecord(Base):
    """Database model for user feedback."""
    __tablename__ = "feedback"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    response_id = Column(String, nullable=False, index=True)
    session_id = Column(PGUUID(as_uuid=True), nullable=True, index=True)

    # Feedback type (up/down)
    feedback = Column(
        Enum('up', 'down', name='feedback_type'),
        nullable=False
    )

    # User tracking
    user_id = Column(String, default="anonymous", nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Context
    response_language = Column(String, default="en")
    conversation_type = Column(String, default="unknown")

    def __repr__(self):
        return f"<FeedbackRecord(id={self.id}, response_id={self.response_id}, feedback={self.feedback})>"
