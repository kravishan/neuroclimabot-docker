from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.schemas.feedback import FeedbackStats
from app.services.feedback.storage import get_simple_feedback_service, SimpleFeedbackService
from app.services.database.stats_database import get_stats_database
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


class FeedbackRequest(BaseModel):
    """Request for thumbs up/down buttons."""
    
    response_id: str = Field(..., description="ID of the response")
    feedback: str = Field(..., description="'up' or 'down'")
    session_id: Optional[UUID] = Field(None, description="Session ID if available")
    response_language: str = Field(default="en", description="Response language")
    conversation_type: str = Field(default="unknown", description="start/continue/unknown")


class FeedbackResponse(BaseModel):
    """Response for feedback submission."""
    
    success: bool
    message: str
    total_feedback_count: Optional[int] = None


@router.post("/submit", response_model=FeedbackResponse)
async def submit_feedback(request: FeedbackRequest):
    """Submit thumbs up/down feedback to SQLite database."""

    try:
        # Get stats database
        stats_db = await get_stats_database()

        # Determine feedback type
        feedback_type = "thumbs_up" if request.feedback.lower() == "up" else "thumbs_down"

        # Determine conversation type
        conv_type = request.conversation_type if request.conversation_type in ["start", "continue"] else "continue"

        # Add feedback to database (with response_id to track duplicates)
        await stats_db.add_feedback(
            response_id=request.response_id,
            feedback_type=feedback_type,
            conversation_type=conv_type,
            language=request.response_language
        )

        # Get updated stats
        feedback_stats = await stats_db.get_feedback_stats()

        return FeedbackResponse(
            success=True,
            message="Thank you for your feedback!",
            total_feedback_count=feedback_stats["total_feedback"]
        )

    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit feedback"
        )

@router.get("/stats", response_model=FeedbackStats)
async def get_feedback_statistics():
    """Get ALL feedback statistics from SQLite database (not filtered by date)."""

    try:
        # Get stats database
        stats_db = await get_stats_database()

        # Get ALL feedback stats from database (cumulative, not time-filtered)
        db_stats = await stats_db.get_feedback_stats()

        # Calculate satisfaction rate
        total_feedback = db_stats["total_feedback"]
        total_thumbs_up = db_stats["total_thumbs_up"]
        satisfaction_rate = (total_thumbs_up / total_feedback * 100) if total_feedback > 0 else 0.0

        # Create FeedbackStats response
        return FeedbackStats(
            total_feedback=total_feedback,
            positive_count=total_thumbs_up,
            negative_count=db_stats["total_thumbs_down"],
            satisfaction_rate=round(satisfaction_rate, 2),
            start_conversation_stats=db_stats["start_conversation_stats"],
            continue_conversation_stats=db_stats["continue_conversation_stats"],
            language_stats=db_stats["language_stats"]
        )

    except Exception as e:
        logger.error(f"Error getting feedback statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get feedback statistics"
        )