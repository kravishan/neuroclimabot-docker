"""
Analytics service with Redis persistence.

Stores analytics data in Redis for persistence across server restarts.
Uses Redis Sorted Sets for efficient top-N queries.

Data stored in Redis (DB 2):
- Popular Queries (max 10)
- Popular Documents (max 10)
- Trending Keywords (max 20)
- Today's Overview stats

Data from MongoDB (via StatsDatabase):
- Feedback stats (thumbs up/down)
- Session stats (total_sessions, avg_response_time)
"""

import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, date
import redis.asyncio as redis

from app.config.database import get_redis_config

logger = logging.getLogger(__name__)
redis_config = get_redis_config()


class RedisAnalyticsService:
    """
    Redis-based analytics service for tracking user interactions.

    Data is persisted in Redis and survives server restarts.
    Uses Redis Sorted Sets for efficient ranking of popular items.
    """

    # Redis key names
    POPULAR_QUERIES_KEY = "popular_queries"
    POPULAR_DOCUMENTS_KEY = "popular_documents"
    TRENDING_TOPICS_KEY = "trending_topics"
    DAILY_STATS_KEY = "daily_stats"
    UNIQUE_SESSIONS_KEY = "unique_sessions"

    def __init__(self):
        """Initialize Redis analytics service."""
        self._redis_client: Optional[redis.Redis] = None
        self._initialized = False
        self._prefix = redis_config.ANALYTICS_PREFIX

        # Limits from config
        self._queries_limit = redis_config.POPULAR_QUERIES_LIMIT
        self._documents_limit = redis_config.POPULAR_DOCUMENTS_LIMIT
        self._topics_limit = redis_config.TRENDING_KEYWORDS_LIMIT

        logger.info("Analytics service created (Redis persistence mode)")

    def _key(self, name: str) -> str:
        """Get prefixed Redis key."""
        return f"{self._prefix}{name}"

    def _daily_key(self, name: str) -> str:
        """Get prefixed Redis key with today's date."""
        today = date.today().isoformat()
        return f"{self._prefix}{name}:{today}"

    async def initialize(self):
        """Initialize Redis connection."""
        try:
            if self._redis_client is None:
                self._redis_client = redis.from_url(
                    redis_config.URL,
                    db=redis_config.ANALYTICS_DB,
                    decode_responses=True,
                    socket_timeout=redis_config.SOCKET_TIMEOUT,
                    socket_connect_timeout=redis_config.CONNECTION_TIMEOUT
                )
                # Test connection
                await self._redis_client.ping()
                logger.info("✅ Analytics service Redis connection initialized (DB 2)")
            self._initialized = True
        except Exception as e:
            logger.error(f"❌ Failed to initialize Redis for analytics: {e}")
            raise

    async def _ensure_initialized(self):
        """Ensure Redis client is initialized."""
        if not self._initialized:
            await self.initialize()

    async def close(self):
        """Close Redis connection."""
        if self._redis_client:
            await self._redis_client.close()
            self._redis_client = None
            self._initialized = False
            logger.info("Analytics service Redis connection closed")

    async def track_query(
        self,
        query: str,
        session_id: str,
        user_id: str = None,
        language: str = "en"
    ) -> None:
        """Track a user query."""
        try:
            await self._ensure_initialized()

            # Increment query count in sorted set
            key = self._key(self.POPULAR_QUERIES_KEY)
            await self._redis_client.zincrby(key, 1, query)

            # Trim to keep only top N queries (limit * 2 for buffer)
            await self._redis_client.zremrangebyrank(key, 0, -(self._queries_limit * 2 + 1))

            # Track session for unique users count
            if session_id:
                sessions_key = self._daily_key(self.UNIQUE_SESSIONS_KEY)
                await self._redis_client.sadd(sessions_key, session_id)
                # Set expiry for 7 days
                await self._redis_client.expire(sessions_key, 7 * 24 * 60 * 60)

            # Increment total queries for today
            stats_key = self._daily_key(self.DAILY_STATS_KEY)
            await self._redis_client.hincrby(stats_key, "total_queries", 1)
            await self._redis_client.expire(stats_key, 7 * 24 * 60 * 60)

            logger.debug(f"Tracked query: {query[:50]}... (session: {session_id})")

        except Exception as e:
            logger.error(f"Error tracking query: {e}")

    async def track_document(self, document: str) -> None:
        """Track document usage."""
        try:
            await self._ensure_initialized()

            # Increment document count in sorted set
            key = self._key(self.POPULAR_DOCUMENTS_KEY)
            await self._redis_client.zincrby(key, 1, document)

            # Trim to keep only top N documents
            await self._redis_client.zremrangebyrank(key, 0, -(self._documents_limit * 2 + 1))

            # Increment total documents for today
            stats_key = self._daily_key(self.DAILY_STATS_KEY)
            await self._redis_client.hincrby(stats_key, "total_documents", 1)
            await self._redis_client.expire(stats_key, 7 * 24 * 60 * 60)

            logger.debug(f"Tracked document: {document}")

        except Exception as e:
            logger.error(f"Error tracking document: {e}")

    async def track_topic(self, topic: str) -> None:
        """Track topic/keyword extraction."""
        try:
            if not topic:
                return

            await self._ensure_initialized()

            # Increment topic count in sorted set
            key = self._key(self.TRENDING_TOPICS_KEY)
            await self._redis_client.zincrby(key, 1, topic)

            # Trim to keep only top N topics
            await self._redis_client.zremrangebyrank(key, 0, -(self._topics_limit * 2 + 1))

            # Increment total topics for today
            stats_key = self._daily_key(self.DAILY_STATS_KEY)
            await self._redis_client.hincrby(stats_key, "total_topics", 1)
            await self._redis_client.expire(stats_key, 7 * 24 * 60 * 60)

            logger.debug(f"Tracked topic: {topic}")

        except Exception as e:
            logger.error(f"Error tracking topic: {e}")

    async def track_response_time(self, time_seconds: float) -> None:
        """Track response time (stored in MongoDB via stats_database)."""
        # Response time is tracked in MongoDB for persistence
        # This method is kept for compatibility but delegates to stats_database
        pass

    async def get_popular_queries(self, limit: int = None) -> List[Dict[str, Any]]:
        """Get popular queries (max 10)."""
        try:
            await self._ensure_initialized()

            # Use configured limit, capped at max
            effective_limit = min(limit or self._queries_limit, self._queries_limit)

            key = self._key(self.POPULAR_QUERIES_KEY)
            # Get top N queries with scores (counts), sorted by score descending
            results = await self._redis_client.zrevrange(key, 0, effective_limit - 1, withscores=True)

            popular = [
                {"query": query, "count": int(count)}
                for query, count in results
            ]

            logger.debug(f"Returning {len(popular)} popular queries")
            return popular

        except Exception as e:
            logger.error(f"Error getting popular queries: {e}")
            return []

    async def get_popular_documents(self, limit: int = None) -> List[Dict[str, Any]]:
        """Get popular documents (max 10)."""
        try:
            await self._ensure_initialized()

            # Use configured limit, capped at max
            effective_limit = min(limit or self._documents_limit, self._documents_limit)

            key = self._key(self.POPULAR_DOCUMENTS_KEY)
            # Get top N documents with scores (counts), sorted by score descending
            results = await self._redis_client.zrevrange(key, 0, effective_limit - 1, withscores=True)

            popular = [
                {"document": doc, "count": int(count)}
                for doc, count in results
            ]

            logger.debug(f"Returning {len(popular)} popular documents")
            return popular

        except Exception as e:
            logger.error(f"Error getting popular documents: {e}")
            return []

    async def get_trending_topics(self, limit: int = None) -> List[Dict[str, Any]]:
        """Get trending topics/keywords (max 20)."""
        try:
            await self._ensure_initialized()

            # Use configured limit, capped at max
            effective_limit = min(limit or self._topics_limit, self._topics_limit)

            key = self._key(self.TRENDING_TOPICS_KEY)
            # Get top N topics with scores (counts), sorted by score descending
            results = await self._redis_client.zrevrange(key, 0, effective_limit - 1, withscores=True)

            trending = [
                {"topic": topic, "count": int(count)}
                for topic, count in results
            ]

            logger.debug(f"Returning {len(trending)} trending topics")
            return trending

        except Exception as e:
            logger.error(f"Error getting trending topics: {e}")
            return []

    async def get_topic_distribution(self) -> Dict[str, Any]:
        """Get topic distribution."""
        try:
            await self._ensure_initialized()

            key = self._key(self.TRENDING_TOPICS_KEY)
            # Get all topics with counts
            results = await self._redis_client.zrevrange(key, 0, -1, withscores=True)

            topics = [
                {"topic": topic, "count": int(count)}
                for topic, count in results
            ]

            # Get total queries from daily stats
            stats_key = self._daily_key(self.DAILY_STATS_KEY)
            total_queries = await self._redis_client.hget(stats_key, "total_queries")

            return {
                "topics": topics,
                "total_queries": int(total_queries or 0)
            }

        except Exception as e:
            logger.error(f"Error getting topic distribution: {e}")
            return {"topics": [], "total_queries": 0}

    async def get_today_stats(self) -> Dict[str, Any]:
        """
        Get today's stats.

        Note: total_sessions and avg_response_time come from MongoDB (StatsDatabase).
        This method returns only the Redis-stored stats.
        """
        try:
            await self._ensure_initialized()

            stats_key = self._daily_key(self.DAILY_STATS_KEY)
            sessions_key = self._daily_key(self.UNIQUE_SESSIONS_KEY)

            # Get stats from Redis
            stats_data = await self._redis_client.hgetall(stats_key)
            unique_users = await self._redis_client.scard(sessions_key)

            # Count unique documents and topics
            docs_key = self._key(self.POPULAR_DOCUMENTS_KEY)
            topics_key = self._key(self.TRENDING_TOPICS_KEY)
            total_unique_documents = await self._redis_client.zcard(docs_key)
            total_unique_topics = await self._redis_client.zcard(topics_key)

            stats = {
                "total_queries": int(stats_data.get("total_queries", 0)),
                "unique_users": unique_users,
                "total_documents": total_unique_documents,
                "total_topics": total_unique_topics,
                "avg_response_time": 0.0  # This comes from MongoDB
            }

            logger.debug(f"Returning today's stats: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Error getting today's stats: {e}")
            return {
                "total_queries": 0,
                "unique_users": 0,
                "total_documents": 0,
                "total_topics": 0,
                "avg_response_time": 0.0
            }

    async def track_feedback(
        self,
        feedback_type: str,
        message_id: str,
        user_id: str = "anonymous",
        session_id: str = None
    ) -> None:
        """
        Track user feedback.

        Note: Feedback is stored in MongoDB via StatsDatabase.
        This method is kept for API compatibility but does nothing.
        Use StatsDatabase.add_feedback() instead.
        """
        # Feedback tracking delegated to MongoDB StatsDatabase
        pass

    async def get_feedback_stats(self) -> Dict[str, Any]:
        """
        Get feedback statistics.

        Note: Feedback stats come from MongoDB via StatsDatabase.
        This method returns empty stats - use StatsDatabase.get_feedback_stats() instead.
        """
        # Feedback stats come from MongoDB
        return {
            "total_feedback": 0,
            "positive": 0,
            "negative": 0,
            "satisfaction_rate": 0
        }

    async def health_check(self) -> bool:
        """Check if Redis connection is healthy."""
        try:
            await self._ensure_initialized()
            await self._redis_client.ping()
            return True
        except Exception as e:
            logger.error(f"Analytics service health check failed: {e}")
            return False

    async def clear_analytics(self) -> None:
        """Clear all analytics data (for testing/reset)."""
        try:
            await self._ensure_initialized()

            # Delete all analytics keys
            keys_to_delete = [
                self._key(self.POPULAR_QUERIES_KEY),
                self._key(self.POPULAR_DOCUMENTS_KEY),
                self._key(self.TRENDING_TOPICS_KEY),
            ]

            # Also delete daily keys for the last 7 days
            for i in range(7):
                from datetime import timedelta
                day = (date.today() - timedelta(days=i)).isoformat()
                keys_to_delete.append(f"{self._prefix}{self.DAILY_STATS_KEY}:{day}")
                keys_to_delete.append(f"{self._prefix}{self.UNIQUE_SESSIONS_KEY}:{day}")

            for key in keys_to_delete:
                await self._redis_client.delete(key)

            logger.info("✅ Analytics data cleared")

        except Exception as e:
            logger.error(f"Error clearing analytics: {e}")


# Singleton instance
_analytics_service: RedisAnalyticsService = None


async def get_analytics_service() -> RedisAnalyticsService:
    """
    Get or create the analytics service instance.

    Returns:
        RedisAnalyticsService: The Redis-based analytics service
    """
    global _analytics_service

    if _analytics_service is None:
        _analytics_service = RedisAnalyticsService()
        await _analytics_service.initialize()

    return _analytics_service


async def initialize_analytics_service() -> RedisAnalyticsService:
    """Initialize and return the analytics service instance."""
    global _analytics_service
    if _analytics_service is None:
        _analytics_service = RedisAnalyticsService()
    await _analytics_service.initialize()
    return _analytics_service
