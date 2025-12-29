"""
Repository for feedback database operations.
"""

from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session

from app.models.feedback_model import FeedbackRecord
from app.repositories.base import BaseRepository


class FeedbackRepository(BaseRepository[FeedbackRecord]):
    """Repository for feedback operations."""

    def __init__(self, session: Session):
        super().__init__(FeedbackRecord, session)

    def find_by_response_id(self, response_id: str) -> List[FeedbackRecord]:
        """
        Find all feedback for a specific response.

        Args:
            response_id: The response ID

        Returns:
            List of feedback records
        """
        return (
            self.session.query(FeedbackRecord)
            .filter_by(response_id=response_id)
            .all()
        )

    def find_by_session_id(self, session_id: UUID) -> List[FeedbackRecord]:
        """
        Find all feedback for a specific session.

        Args:
            session_id: The session UUID

        Returns:
            List of feedback records
        """
        return (
            self.session.query(FeedbackRecord)
            .filter_by(session_id=session_id)
            .all()
        )

    def find_by_user_id(self, user_id: str, limit: Optional[int] = None) -> List[FeedbackRecord]:
        """
        Find all feedback from a specific user.

        Args:
            user_id: The user ID
            limit: Optional limit on results

        Returns:
            List of feedback records
        """
        query = self.session.query(FeedbackRecord).filter_by(user_id=user_id)
        if limit:
            query = query.limit(limit)
        return query.all()

    def count_by_feedback_type(self, feedback_type: str) -> int:
        """
        Count feedback by type (up/down).

        Args:
            feedback_type: 'up' or 'down'

        Returns:
            Count of feedback
        """
        return (
            self.session.query(FeedbackRecord)
            .filter_by(feedback=feedback_type)
            .count()
        )

    def get_feedback_stats(self) -> dict:
        """
        Get comprehensive feedback statistics.

        Returns:
            Dictionary with feedback statistics
        """
        total = self.count()
        positive = self.count_by_feedback_type('up')
        negative = self.count_by_feedback_type('down')

        satisfaction_rate = (positive / total * 100) if total > 0 else 0.0

        return {
            "total_feedback": total,
            "positive_count": positive,
            "negative_count": negative,
            "satisfaction_rate": satisfaction_rate,
        }
