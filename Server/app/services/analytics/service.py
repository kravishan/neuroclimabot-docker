"""
Analytics service with in-memory tracking.
This implementation stores analytics data in memory (no Redis required).
"""

import logging
from typing import List, Dict, Any
from datetime import datetime
from collections import defaultdict, Counter

logger = logging.getLogger(__name__)


class RedisAnalyticsService:
    """
    In-memory analytics service for tracking user interactions.

    Stores data in memory - resets on server restart.
    """

    def __init__(self):
        """Initialize in-memory analytics service."""
        logger.info("Analytics service initialized (in-memory mode)")

        # In-memory storage
        self.queries: List[Dict[str, Any]] = []
        self.documents: List[str] = []
        self.sessions: set = set()
        self.topics: List[str] = []
        # Feedbacks: store last interaction per message_id + user_id
        # Key: "message_id:user_id", Value: {"type": "positive/negative", "timestamp": ...}
        self.feedbacks: Dict[str, Dict[str, Any]] = {}
        self.response_times: List[float] = []

    async def initialize(self):
        """Initialize the service."""
        logger.debug("Analytics service initialization completed")
        pass

    async def track_query(
        self,
        query: str,
        session_id: str,
        user_id: str = None,
        language: str = "en"
    ) -> None:
        """Track a user query."""
        self.queries.append({
            "query": query,
            "session_id": session_id,
            "user_id": user_id,
            "language": language,
            "timestamp": datetime.now().isoformat()
        })
        if session_id:
            self.sessions.add(session_id)
        logger.debug(f"Tracked query: {query[:50]}... (session: {session_id})")

    async def track_document(self, document: str) -> None:
        """Track document usage."""
        self.documents.append(document)
        logger.debug(f"Tracked document: {document}")

    async def track_topic(self, topic: str) -> None:
        """Track topic extraction."""
        if topic:
            self.topics.append(topic)
            logger.debug(f"Tracked topic: {topic}")

    async def track_response_time(self, time_seconds: float) -> None:
        """Track response time."""
        self.response_times.append(time_seconds)

    async def get_popular_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get popular queries."""
        if not self.queries:
            return []

        # Count query occurrences
        query_counts = Counter(q["query"] for q in self.queries)
        popular = [
            {"query": query, "count": count}
            for query, count in query_counts.most_common(limit)
        ]

        logger.debug(f"Returning {len(popular)} popular queries")
        return popular

    async def get_popular_documents(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get popular documents."""
        if not self.documents:
            return []

        # Count document occurrences
        doc_counts = Counter(self.documents)
        popular = [
            {"document": doc, "count": count}
            for doc, count in doc_counts.most_common(limit)
        ]

        logger.debug(f"Returning {len(popular)} popular documents")
        return popular

    async def get_trending_topics(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get trending topics."""
        if not self.topics:
            return []

        # Count topic occurrences
        topic_counts = Counter(self.topics)
        trending = [
            {"topic": topic, "count": count}
            for topic, count in topic_counts.most_common(limit)
        ]

        logger.debug(f"Returning {len(trending)} trending topics")
        return trending

    async def get_topic_distribution(self) -> Dict[str, Any]:
        """Get topic distribution."""
        if not self.topics:
            return {"topics": [], "total_queries": 0}

        topic_counts = Counter(self.topics)
        topics = [
            {"topic": topic, "count": count}
            for topic, count in topic_counts.items()
        ]

        return {
            "topics": topics,
            "total_queries": len(self.queries)
        }

    async def get_today_stats(self) -> Dict[str, Any]:
        """Get today's stats."""
        avg_response_time = (
            sum(self.response_times) / len(self.response_times)
            if self.response_times else 0.0
        )

        stats = {
            "total_queries": len(self.queries),
            "unique_users": len(self.sessions),
            "total_documents": len(set(self.documents)),
            "total_topics": len(set(self.topics)),
            "avg_response_time": round(avg_response_time, 2)
        }

        logger.debug(f"Returning stats: {stats}")
        return stats

    async def track_feedback(
        self,
        feedback_type: str,
        message_id: str,
        user_id: str = "anonymous",
        session_id: str = None
    ) -> None:
        """
        Track user feedback.

        For the same message_id + user_id combination, only the last feedback is saved.
        This ensures that if a user changes from thumbs up to thumbs down (or vice versa),
        only the latest interaction is counted.
        """
        # Create a unique key for this message + user combination
        feedback_key = f"{message_id}:{user_id}"

        # Store/update the feedback (overwrites previous feedback for same message+user)
        self.feedbacks[feedback_key] = {
            "type": feedback_type,  # "positive" or "negative"
            "message_id": message_id,
            "user_id": user_id,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        }

        logger.debug(f"Tracked feedback: {feedback_type} for message {message_id} (user: {user_id})")

    async def get_feedback_stats(self) -> Dict[str, Any]:
        """
        Get feedback statistics.

        Counts unique positive and negative feedbacks across all responses.
        Each message+user combination counts once with their latest feedback.
        """
        positive_count = sum(1 for fb in self.feedbacks.values() if fb["type"] == "positive")
        negative_count = sum(1 for fb in self.feedbacks.values() if fb["type"] == "negative")

        stats = {
            "total_feedback": len(self.feedbacks),
            "positive": positive_count,
            "negative": negative_count,
            "satisfaction_rate": round((positive_count / len(self.feedbacks) * 100), 2) if self.feedbacks else 0
        }

        logger.debug(f"Returning feedback stats: {stats}")
        return stats


# Singleton instance
_analytics_service: RedisAnalyticsService = None


async def get_analytics_service() -> RedisAnalyticsService:
    """
    Get or create the analytics service instance.

    Returns:
        RedisAnalyticsService: The stub analytics service
    """
    global _analytics_service

    if _analytics_service is None:
        _analytics_service = RedisAnalyticsService()
        await _analytics_service.initialize()

    return _analytics_service
