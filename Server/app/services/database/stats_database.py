"""MongoDB database for persistent session stats and feedback storage."""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from app.utils.logger import get_logger
from app.config.database import get_mongodb_config

logger = get_logger(__name__)


class StatsDatabase:
    """Persistent storage for session statistics and feedback data using MongoDB."""

    def __init__(self):
        """Initialize database connection."""
        self._client: Optional[MongoClient] = None
        self._db = None
        self._session_stats = None
        self._feedback_stats = None
        self._lock = asyncio.Lock()
        self.connected = False

    async def initialize(self):
        """Initialize MongoDB connection and create indexes."""
        try:
            mongodb_config = get_mongodb_config()

            # Create MongoDB client with connection pooling
            self._client = MongoClient(
                mongodb_config.connection_uri,
                maxPoolSize=mongodb_config.MAX_POOL_SIZE,
                minPoolSize=mongodb_config.MIN_POOL_SIZE,
                serverSelectionTimeoutMS=mongodb_config.SERVER_SELECTION_TIMEOUT,
                connectTimeoutMS=mongodb_config.CONNECT_TIMEOUT,
            )

            # Test connection
            self._client.admin.command('ping')

            # Get database and collections
            self._db = self._client[mongodb_config.DATABASE]
            self._session_stats = self._db['session_stats']
            self._feedback_stats = self._db['feedback_stats']

            # Initialize singleton documents if they don't exist
            await self._ensure_singleton_documents()

            self.connected = True
            logger.info(f"✅ Stats database initialized: MongoDB {mongodb_config.HOST}:{mongodb_config.PORT}/{mongodb_config.DATABASE}")

        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize stats database: {e}")
            raise

    async def _ensure_singleton_documents(self):
        """Ensure singleton documents exist for stats collections."""
        # Session stats singleton
        if self._session_stats.count_documents({"_id": "singleton"}) == 0:
            self._session_stats.insert_one({
                "_id": "singleton",
                "total_sessions": 0,
                "avg_messages_per_session": 0.0,
                "avg_response_time": 0.0,
                "updated_at": datetime.utcnow()
            })

        # Feedback stats singleton
        if self._feedback_stats.count_documents({"_id": "singleton"}) == 0:
            self._feedback_stats.insert_one({
                "_id": "singleton",
                "total_thumbs_up": 0,
                "total_thumbs_down": 0,
                "total_feedback": 0,
                "start_conversation_up": 0,
                "start_conversation_down": 0,
                "continue_conversation_up": 0,
                "continue_conversation_down": 0,
                "language_stats": {},
                "updated_at": datetime.utcnow()
            })

    async def get_session_stats(self) -> Dict[str, Any]:
        """Get current session statistics."""
        async with self._lock:
            doc = self._session_stats.find_one({"_id": "singleton"})

            if doc:
                return {
                    "total_sessions": doc.get("total_sessions", 0),
                    "avg_messages_per_session": doc.get("avg_messages_per_session", 0.0),
                    "avg_response_time": doc.get("avg_response_time", 0.0)
                }
            return {
                "total_sessions": 0,
                "avg_messages_per_session": 0.0,
                "avg_response_time": 0.0
            }

    async def update_session_stats(self, total_sessions: int, avg_messages: float, avg_response_time: float):
        """Update session statistics."""
        async with self._lock:
            self._session_stats.update_one(
                {"_id": "singleton"},
                {
                    "$set": {
                        "total_sessions": total_sessions,
                        "avg_messages_per_session": avg_messages,
                        "avg_response_time": avg_response_time,
                        "updated_at": datetime.utcnow()
                    }
                },
                upsert=True
            )

    async def increment_session_count(self):
        """Increment total session count."""
        async with self._lock:
            self._session_stats.update_one(
                {"_id": "singleton"},
                {
                    "$inc": {"total_sessions": 1},
                    "$set": {"updated_at": datetime.utcnow()}
                },
                upsert=True
            )

    async def record_session_message(self, message_count: int):
        """Record a completed session's message count and update average."""
        async with self._lock:
            doc = self._session_stats.find_one({"_id": "singleton"})

            if doc:
                current_avg = doc.get("avg_messages_per_session", 0.0)
                current_total = doc.get("total_sessions", 0)

                # Calculate new average using exponential moving average
                # Weight: 90% current avg, 10% new value for stability
                new_avg = (current_avg * 0.9) + (message_count * 0.1) if current_avg > 0 else message_count
                new_total = current_total + 1

                self._session_stats.update_one(
                    {"_id": "singleton"},
                    {
                        "$set": {
                            "total_sessions": new_total,
                            "avg_messages_per_session": new_avg,
                            "updated_at": datetime.utcnow()
                        }
                    }
                )

    async def record_response_time(self, response_time: float):
        """Record a response time and update average."""
        async with self._lock:
            doc = self._session_stats.find_one({"_id": "singleton"})

            if doc:
                current_avg = doc.get("avg_response_time", 0.0)

                # Use exponential moving average for response time
                # Weight: 90% current avg, 10% new value
                new_avg = (current_avg * 0.9) + (response_time * 0.1) if current_avg > 0 else response_time

                self._session_stats.update_one(
                    {"_id": "singleton"},
                    {
                        "$set": {
                            "avg_response_time": new_avg,
                            "updated_at": datetime.utcnow()
                        }
                    }
                )

    async def get_feedback_stats(self) -> Dict[str, Any]:
        """Get ALL feedback statistics."""
        async with self._lock:
            doc = self._feedback_stats.find_one({"_id": "singleton"})

            if doc:
                return {
                    "total_thumbs_up": doc.get("total_thumbs_up", 0),
                    "total_thumbs_down": doc.get("total_thumbs_down", 0),
                    "total_feedback": doc.get("total_feedback", 0),
                    "start_conversation_stats": {
                        "up": doc.get("start_conversation_up", 0),
                        "down": doc.get("start_conversation_down", 0)
                    },
                    "continue_conversation_stats": {
                        "up": doc.get("continue_conversation_up", 0),
                        "down": doc.get("continue_conversation_down", 0)
                    },
                    "language_stats": doc.get("language_stats", {})
                }
            return {
                "total_thumbs_up": 0,
                "total_thumbs_down": 0,
                "total_feedback": 0,
                "start_conversation_stats": {"up": 0, "down": 0},
                "continue_conversation_stats": {"up": 0, "down": 0},
                "language_stats": {}
            }

    async def add_feedback(
        self,
        response_id: str,
        feedback_type: str,  # "thumbs_up" or "thumbs_down"
        conversation_type: str,  # "start" or "continue"
        language: Optional[str] = None
    ):
        """Add feedback and update aggregate statistics."""
        async with self._lock:
            # Prepare increments based on feedback type and conversation type
            inc_fields = {"total_feedback": 1}

            if feedback_type == "thumbs_up":
                inc_fields["total_thumbs_up"] = 1
                if conversation_type == "start":
                    inc_fields["start_conversation_up"] = 1
                else:
                    inc_fields["continue_conversation_up"] = 1
            else:
                inc_fields["total_thumbs_down"] = 1
                if conversation_type == "start":
                    inc_fields["start_conversation_down"] = 1
                else:
                    inc_fields["continue_conversation_down"] = 1

            # Update aggregate stats with increments
            update_ops = {
                "$inc": inc_fields,
                "$set": {"updated_at": datetime.utcnow()}
            }

            # Handle language stats separately using dot notation
            if language:
                update_ops["$inc"][f"language_stats.{language}.{'up' if feedback_type == 'thumbs_up' else 'down'}"] = 1

            self._feedback_stats.update_one(
                {"_id": "singleton"},
                update_ops,
                upsert=True
            )

            logger.debug(f"Feedback recorded: {feedback_type} for response {response_id}")

    async def clear_feedback_stats(self):
        """Clear all feedback statistics."""
        async with self._lock:
            # Reset aggregate stats
            self._feedback_stats.update_one(
                {"_id": "singleton"},
                {
                    "$set": {
                        "total_thumbs_up": 0,
                        "total_thumbs_down": 0,
                        "total_feedback": 0,
                        "start_conversation_up": 0,
                        "start_conversation_down": 0,
                        "continue_conversation_up": 0,
                        "continue_conversation_down": 0,
                        "language_stats": {},
                        "updated_at": datetime.utcnow()
                    }
                }
            )

            logger.info("✅ Feedback statistics cleared")

    async def close(self):
        """Close database connection."""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            self._session_stats = None
            self._feedback_stats = None
            self.connected = False
            logger.info("✅ Stats database connection closed")

    async def health_check(self) -> bool:
        """Check database health."""
        try:
            if not self._client:
                return False
            self._client.admin.command('ping')
            return True
        except Exception as e:
            logger.error(f"Stats database health check failed: {e}")
            return False

    # Property for backward compatibility
    @property
    def connection(self):
        """Backward compatibility property."""
        return self._client


# Global instance
stats_database = StatsDatabase()


async def get_stats_database() -> StatsDatabase:
    """Get the stats database instance."""
    if not stats_database.connected:
        await stats_database.initialize()
    return stats_database
