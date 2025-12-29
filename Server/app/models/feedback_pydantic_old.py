from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


class ThumbsFeedback(str, Enum):
    """Simple thumbs feedback types."""
    UP = "up"
    DOWN = "down"


class ResponseFeedback(BaseModel):
    """Simple feedback model for thumbs up/down tracking."""
    
    id: UUID = Field(default_factory=uuid4)
    response_id: str = Field(..., description="ID of the response being rated")
    session_id: Optional[UUID] = Field(None, description="Session this feedback belongs to")
    
    # Core feedback data
    feedback: ThumbsFeedback = Field(..., description="up or down")
    
    # Anonymous user tracking
    user_id: str = Field(default="anonymous")
    
    # Timing
    created_at: datetime = Field(default_factory=datetime.now)
    
    # Optional context
    response_language: str = Field(default="en")
    conversation_type: str = Field(default="unknown")


class FeedbackStats(BaseModel):
    """Statistics for research analysis."""

    total_feedback: int = 0
    positive_count: int = 0  # total_thumbs_up
    negative_count: int = 0  # total_thumbs_down

    satisfaction_rate: float = 0.0  # percentage of thumbs up

    start_conversation_stats: dict = Field(default_factory=dict)
    continue_conversation_stats: dict = Field(default_factory=dict)
    language_stats: dict = Field(default_factory=dict)