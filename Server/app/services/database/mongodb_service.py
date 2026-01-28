"""
MongoDB service for persistent data storage.
Handles questionnaires, feedback, and session statistics.
Replaces SQLite databases for multi-replica support in Kubernetes.
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import IndexModel, ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError

from app.config.database import get_mongodb_config
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MongoDBService:
    """
    MongoDB service for persistent data storage.
    Supports concurrent access from multiple Server/Processor replicas.
    """

    def __init__(self):
        self.config = get_mongodb_config()
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
        self._initialized = False

    async def initialize(self):
        """Initialize MongoDB connection and create indexes."""
        if self._initialized:
            return

        try:
            # Create async client
            self.client = AsyncIOMotorClient(**self.config.connection_kwargs)
            self.db = self.client[self.config.DATABASE]

            # Test connection
            await self.client.admin.command('ping')

            # Create indexes
            await self._create_indexes()

            # Initialize singleton stats documents
            await self._init_stats_documents()

            self._initialized = True
            logger.info(f"MongoDB initialized: {self.config.HOST}:{self.config.PORT}/{self.config.DATABASE}")

        except Exception as e:
            logger.error(f"Failed to initialize MongoDB: {e}")
            raise

    async def _create_indexes(self):
        """Create indexes for all collections."""
        try:
            # Questionnaires collection indexes
            questionnaires = self.db[self.config.COLLECTION_QUESTIONNAIRES]
            await questionnaires.create_indexes([
                IndexModel([("participant_id", ASCENDING)]),
                IndexModel([("email", ASCENDING)]),
                IndexModel([("created_at", DESCENDING)]),
            ])

            # Feedback collection indexes
            feedback = self.db[self.config.COLLECTION_FEEDBACK]
            await feedback.create_indexes([
                IndexModel([("response_id", ASCENDING)], unique=True),
                IndexModel([("session_id", ASCENDING)]),
                IndexModel([("created_at", DESCENDING)]),
            ])

            # Session stats - single document pattern
            session_stats = self.db[self.config.COLLECTION_SESSION_STATS]
            await session_stats.create_indexes([
                IndexModel([("_id", ASCENDING)]),
            ])

            # Feedback stats - single document pattern
            feedback_stats = self.db[self.config.COLLECTION_FEEDBACK_STATS]
            await feedback_stats.create_indexes([
                IndexModel([("_id", ASCENDING)]),
            ])

            logger.info("MongoDB indexes created successfully")

        except Exception as e:
            logger.warning(f"Index creation warning (may already exist): {e}")

    async def _init_stats_documents(self):
        """Initialize singleton stats documents if they don't exist."""
        try:
            # Initialize session stats singleton
            session_stats = self.db[self.config.COLLECTION_SESSION_STATS]
            await session_stats.update_one(
                {"_id": "stats"},
                {"$setOnInsert": {
                    "total_sessions": 0,
                    "avg_messages_per_session": 0.0,
                    "avg_response_time": 0.0,
                    "updated_at": datetime.utcnow()
                }},
                upsert=True
            )

            # Initialize feedback stats singleton
            feedback_stats = self.db[self.config.COLLECTION_FEEDBACK_STATS]
            await feedback_stats.update_one(
                {"_id": "stats"},
                {"$setOnInsert": {
                    "total_thumbs_up": 0,
                    "total_thumbs_down": 0,
                    "total_feedback": 0,
                    "start_conversation_up": 0,
                    "start_conversation_down": 0,
                    "continue_conversation_up": 0,
                    "continue_conversation_down": 0,
                    "language_stats": {},
                    "updated_at": datetime.utcnow()
                }},
                upsert=True
            )

        except Exception as e:
            logger.warning(f"Stats initialization warning: {e}")

    # =========================================================================
    # Session Statistics Methods
    # =========================================================================

    async def get_session_stats(self) -> Dict[str, Any]:
        """Get current session statistics."""
        try:
            collection = self.db[self.config.COLLECTION_SESSION_STATS]
            doc = await collection.find_one({"_id": "stats"})

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
        except Exception as e:
            logger.error(f"Error getting session stats: {e}")
            return {"total_sessions": 0, "avg_messages_per_session": 0.0, "avg_response_time": 0.0}

    async def update_session_stats(self, total_sessions: int, avg_messages: float, avg_response_time: float):
        """Update session statistics."""
        try:
            collection = self.db[self.config.COLLECTION_SESSION_STATS]
            await collection.update_one(
                {"_id": "stats"},
                {"$set": {
                    "total_sessions": total_sessions,
                    "avg_messages_per_session": avg_messages,
                    "avg_response_time": avg_response_time,
                    "updated_at": datetime.utcnow()
                }},
                upsert=True
            )
        except Exception as e:
            logger.error(f"Error updating session stats: {e}")

    async def increment_session_count(self):
        """Atomically increment total session count."""
        try:
            collection = self.db[self.config.COLLECTION_SESSION_STATS]
            await collection.update_one(
                {"_id": "stats"},
                {
                    "$inc": {"total_sessions": 1},
                    "$set": {"updated_at": datetime.utcnow()}
                },
                upsert=True
            )
        except Exception as e:
            logger.error(f"Error incrementing session count: {e}")

    async def record_session_message(self, message_count: int):
        """Record a completed session's message count using exponential moving average."""
        try:
            collection = self.db[self.config.COLLECTION_SESSION_STATS]
            doc = await collection.find_one({"_id": "stats"})

            current_avg = doc.get("avg_messages_per_session", 0.0) if doc else 0.0
            # EMA: 90% current avg, 10% new value
            new_avg = (current_avg * 0.9) + (message_count * 0.1) if current_avg > 0 else float(message_count)

            await collection.update_one(
                {"_id": "stats"},
                {
                    "$inc": {"total_sessions": 1},
                    "$set": {
                        "avg_messages_per_session": new_avg,
                        "updated_at": datetime.utcnow()
                    }
                },
                upsert=True
            )
        except Exception as e:
            logger.error(f"Error recording session message: {e}")

    async def record_response_time(self, response_time: float):
        """Record a response time using exponential moving average."""
        try:
            collection = self.db[self.config.COLLECTION_SESSION_STATS]
            doc = await collection.find_one({"_id": "stats"})

            current_avg = doc.get("avg_response_time", 0.0) if doc else 0.0
            # EMA: 90% current avg, 10% new value
            new_avg = (current_avg * 0.9) + (response_time * 0.1) if current_avg > 0 else response_time

            await collection.update_one(
                {"_id": "stats"},
                {"$set": {
                    "avg_response_time": new_avg,
                    "updated_at": datetime.utcnow()
                }},
                upsert=True
            )
        except Exception as e:
            logger.error(f"Error recording response time: {e}")

    # =========================================================================
    # Feedback Methods
    # =========================================================================

    async def get_feedback_stats(self) -> Dict[str, Any]:
        """Get all feedback statistics."""
        try:
            collection = self.db[self.config.COLLECTION_FEEDBACK_STATS]
            doc = await collection.find_one({"_id": "stats"})

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
        except Exception as e:
            logger.error(f"Error getting feedback stats: {e}")
            return {
                "total_thumbs_up": 0, "total_thumbs_down": 0, "total_feedback": 0,
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
        """Add or update feedback entry with atomic stats update."""
        try:
            feedback_collection = self.db[self.config.COLLECTION_FEEDBACK]
            stats_collection = self.db[self.config.COLLECTION_FEEDBACK_STATS]

            # Check for existing feedback
            existing = await feedback_collection.find_one({"response_id": response_id})

            # Prepare atomic update operations
            inc_ops = {}
            set_ops = {"updated_at": datetime.utcnow()}

            # If there's existing feedback, reverse the old counts first
            if existing:
                old_type = existing.get("feedback_type")
                old_conv = existing.get("conversation_type")
                old_lang = existing.get("language")

                # Decrement old counts
                if old_type == "thumbs_up":
                    inc_ops["total_thumbs_up"] = inc_ops.get("total_thumbs_up", 0) - 1
                    if old_conv == "start":
                        inc_ops["start_conversation_up"] = inc_ops.get("start_conversation_up", 0) - 1
                    else:
                        inc_ops["continue_conversation_up"] = inc_ops.get("continue_conversation_up", 0) - 1
                else:
                    inc_ops["total_thumbs_down"] = inc_ops.get("total_thumbs_down", 0) - 1
                    if old_conv == "start":
                        inc_ops["start_conversation_down"] = inc_ops.get("start_conversation_down", 0) - 1
                    else:
                        inc_ops["continue_conversation_down"] = inc_ops.get("continue_conversation_down", 0) - 1

                # Decrement old language stats
                if old_lang:
                    lang_key = f"language_stats.{old_lang}.{'up' if old_type == 'thumbs_up' else 'down'}"
                    inc_ops[lang_key] = inc_ops.get(lang_key, 0) - 1
            else:
                # New feedback - increment total
                inc_ops["total_feedback"] = 1

            # Increment new counts
            if feedback_type == "thumbs_up":
                inc_ops["total_thumbs_up"] = inc_ops.get("total_thumbs_up", 0) + 1
                if conversation_type == "start":
                    inc_ops["start_conversation_up"] = inc_ops.get("start_conversation_up", 0) + 1
                else:
                    inc_ops["continue_conversation_up"] = inc_ops.get("continue_conversation_up", 0) + 1
            else:
                inc_ops["total_thumbs_down"] = inc_ops.get("total_thumbs_down", 0) + 1
                if conversation_type == "start":
                    inc_ops["start_conversation_down"] = inc_ops.get("start_conversation_down", 0) + 1
                else:
                    inc_ops["continue_conversation_down"] = inc_ops.get("continue_conversation_down", 0) + 1

            # Increment new language stats
            if language:
                lang_key = f"language_stats.{language}.{'up' if feedback_type == 'thumbs_up' else 'down'}"
                inc_ops[lang_key] = inc_ops.get(lang_key, 0) + 1

            # Update stats atomically
            update_ops = {"$set": set_ops}
            if inc_ops:
                update_ops["$inc"] = inc_ops

            await stats_collection.update_one(
                {"_id": "stats"},
                update_ops,
                upsert=True
            )

            # Upsert the feedback entry
            await feedback_collection.update_one(
                {"response_id": response_id},
                {"$set": {
                    "response_id": response_id,
                    "feedback_type": feedback_type,
                    "conversation_type": conversation_type,
                    "language": language,
                    "updated_at": datetime.utcnow()
                },
                "$setOnInsert": {
                    "created_at": datetime.utcnow()
                }},
                upsert=True
            )

        except Exception as e:
            logger.error(f"Error adding feedback: {e}")
            raise

    async def clear_feedback_stats(self):
        """Clear all feedback statistics and entries."""
        try:
            feedback_collection = self.db[self.config.COLLECTION_FEEDBACK]
            stats_collection = self.db[self.config.COLLECTION_FEEDBACK_STATS]

            # Clear feedback entries
            await feedback_collection.delete_many({})

            # Reset stats
            await stats_collection.update_one(
                {"_id": "stats"},
                {"$set": {
                    "total_thumbs_up": 0,
                    "total_thumbs_down": 0,
                    "total_feedback": 0,
                    "start_conversation_up": 0,
                    "start_conversation_down": 0,
                    "continue_conversation_up": 0,
                    "continue_conversation_down": 0,
                    "language_stats": {},
                    "updated_at": datetime.utcnow()
                }},
                upsert=True
            )
            logger.info("Feedback statistics cleared")

        except Exception as e:
            logger.error(f"Error clearing feedback stats: {e}")
            raise

    # =========================================================================
    # Questionnaire Methods
    # =========================================================================

    async def save_questionnaire(self, questionnaire_data: Dict[str, Any]) -> str:
        """Save a research questionnaire response."""
        try:
            collection = self.db[self.config.COLLECTION_QUESTIONNAIRES]

            # Add metadata
            questionnaire_data["created_at"] = datetime.utcnow()

            result = await collection.insert_one(questionnaire_data)
            questionnaire_id = str(result.inserted_id)

            logger.info(f"Questionnaire saved with ID: {questionnaire_id}")
            return questionnaire_id

        except Exception as e:
            logger.error(f"Error saving questionnaire: {e}")
            raise

    async def get_questionnaires(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all questionnaire responses."""
        try:
            collection = self.db[self.config.COLLECTION_QUESTIONNAIRES]
            cursor = collection.find().sort("created_at", DESCENDING).limit(limit)

            results = []
            async for doc in cursor:
                doc["_id"] = str(doc["_id"])  # Convert ObjectId to string
                results.append(doc)

            return results

        except Exception as e:
            logger.error(f"Error getting questionnaires: {e}")
            return []

    async def get_questionnaire_by_id(self, questionnaire_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific questionnaire response by ID."""
        try:
            from bson import ObjectId
            collection = self.db[self.config.COLLECTION_QUESTIONNAIRES]
            doc = await collection.find_one({"_id": ObjectId(questionnaire_id)})

            if doc:
                doc["_id"] = str(doc["_id"])
                return doc
            return None

        except Exception as e:
            logger.error(f"Error getting questionnaire: {e}")
            return None

    async def get_questionnaire_count(self) -> int:
        """Get total count of questionnaire responses."""
        try:
            collection = self.db[self.config.COLLECTION_QUESTIONNAIRES]
            return await collection.count_documents({})
        except Exception as e:
            logger.error(f"Error getting questionnaire count: {e}")
            return 0

    async def get_questionnaire_stats(self) -> Dict[str, Any]:
        """Get statistics about questionnaire responses."""
        try:
            collection = self.db[self.config.COLLECTION_QUESTIONNAIRES]

            total = await collection.count_documents({})

            # Use aggregation for averages
            pipeline = [
                {"$group": {
                    "_id": None,
                    "avg_rating": {"$avg": "$overall_experience_rating"},
                    "voice_users": {"$sum": {"$cond": [{"$eq": ["$used_voice_feature", True]}, 1, 0]}}
                }}
            ]

            result = await collection.aggregate(pipeline).to_list(1)

            if result:
                return {
                    "total_responses": total,
                    "average_experience_rating": round(result[0].get("avg_rating", 0) or 0, 2),
                    "voice_feature_users": result[0].get("voice_users", 0),
                    "voice_usage_percentage": round((result[0].get("voice_users", 0) / total * 100) if total > 0 else 0, 2)
                }

            return {
                "total_responses": total,
                "average_experience_rating": 0,
                "voice_feature_users": 0,
                "voice_usage_percentage": 0
            }

        except Exception as e:
            logger.error(f"Error getting questionnaire stats: {e}")
            return {"total_responses": 0, "average_experience_rating": 0, "voice_feature_users": 0, "voice_usage_percentage": 0}

    # =========================================================================
    # Health Check
    # =========================================================================

    async def health_check(self) -> bool:
        """Check MongoDB connection health."""
        try:
            if not self.client:
                return False
            await self.client.admin.command('ping')
            return True
        except Exception as e:
            logger.error(f"MongoDB health check failed: {e}")
            return False

    async def close(self):
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            self._initialized = False
            logger.info("MongoDB connection closed")


# Global instance
_mongodb_service: Optional[MongoDBService] = None


async def get_mongodb_service() -> MongoDBService:
    """Get the MongoDB service instance."""
    global _mongodb_service
    if _mongodb_service is None:
        _mongodb_service = MongoDBService()
        await _mongodb_service.initialize()
    return _mongodb_service
