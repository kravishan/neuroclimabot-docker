"""MongoDB-based database for persistent session stats and feedback storage.

Replaces SQLite for multi-replica support in Kubernetes.
All Server replicas share the same MongoDB database.
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime

from app.services.database.mongodb_service import get_mongodb_service, MongoDBService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class StatsDatabase:
    """
    Persistent storage for session statistics and feedback data.
    Uses MongoDB for multi-replica support.
    """

    def __init__(self):
        """Initialize database wrapper."""
        self._mongodb: Optional[MongoDBService] = None
        self._initialized = False

    async def initialize(self):
        """Initialize MongoDB connection."""
        if self._initialized:
            return

        try:
            self._mongodb = await get_mongodb_service()
            self._initialized = True
            logger.info("✅ Stats database initialized (MongoDB)")

        except Exception as e:
            logger.error(f"Failed to initialize stats database: {e}")
            raise

    async def get_session_stats(self) -> Dict[str, Any]:
        """Get current session statistics."""
        return await self._mongodb.get_session_stats()

    async def update_session_stats(self, total_sessions: int, avg_messages: float, avg_response_time: float):
        """Update session statistics."""
        await self._mongodb.update_session_stats(total_sessions, avg_messages, avg_response_time)

    async def increment_session_count(self):
        """Increment total session count."""
        await self._mongodb.increment_session_count()

    async def record_session_message(self, message_count: int):
        """Record a completed session's message count and update average."""
        await self._mongodb.record_session_message(message_count)

    async def record_response_time(self, response_time: float):
        """Record a response time and update average."""
        await self._mongodb.record_response_time(response_time)

    async def get_feedback_stats(self) -> Dict[str, Any]:
        """Get ALL feedback statistics."""
        return await self._mongodb.get_feedback_stats()

    async def add_feedback(
        self,
        response_id: str,
        feedback_type: str,  # "thumbs_up" or "thumbs_down"
        conversation_type: str,  # "start" or "continue"
        language: Optional[str] = None
    ):
        """Add or update feedback entry."""
        await self._mongodb.add_feedback(response_id, feedback_type, conversation_type, language)

    async def clear_feedback_stats(self):
        """Clear all feedback statistics."""
        await self._mongodb.clear_feedback_stats()

    async def save_research_questionnaire(self, questionnaire_data: Dict[str, Any]) -> str:
        """Save a research questionnaire response."""
        return await self._mongodb.save_questionnaire(questionnaire_data)

    async def get_research_questionnaires(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all research questionnaire responses."""
        return await self._mongodb.get_questionnaires(limit)

    async def get_questionnaire_stats(self) -> Dict[str, Any]:
        """Get statistics about questionnaire responses."""
        return await self._mongodb.get_questionnaire_stats()

    async def close(self):
        """Close database connection."""
        if self._mongodb:
            await self._mongodb.close()
            logger.info("✅ Stats database connection closed")

    async def health_check(self) -> bool:
        """Check database health."""
        if not self._mongodb:
            return False
        return await self._mongodb.health_check()


# Global instance
stats_database = StatsDatabase()


async def get_stats_database() -> StatsDatabase:
    """Get the stats database instance."""
    if not stats_database._initialized:
        await stats_database.initialize()
    return stats_database
