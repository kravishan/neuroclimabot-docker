"""MongoDB database for persistent session stats and feedback storage."""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from pymongo import MongoClient, DESCENDING
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
        self._feedback_entries = None
        self._research_questionnaires = None
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
            self._feedback_entries = self._db['feedback_entries']
            self._research_questionnaires = self._db['research_questionnaires']

            # Create indexes
            self._feedback_entries.create_index([("response_id", 1)], unique=True, name="idx_response_id")
            self._feedback_entries.create_index([("created_at", DESCENDING)], name="idx_created_at")
            self._research_questionnaires.create_index([("created_at", DESCENDING)], name="idx_created_at")

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
        """Add or update feedback entry (tracks by response_id to handle duplicates)."""
        async with self._lock:
            # Check if there's existing feedback for this response_id
            existing = self._feedback_entries.find_one({"response_id": response_id})

            # Get current aggregate stats
            stats_doc = self._feedback_stats.find_one({"_id": "singleton"})
            language_stats = stats_doc.get("language_stats", {}) if stats_doc else {}

            # Prepare update values (start with current values)
            total_up = stats_doc.get("total_thumbs_up", 0) if stats_doc else 0
            total_down = stats_doc.get("total_thumbs_down", 0) if stats_doc else 0
            start_up = stats_doc.get("start_conversation_up", 0) if stats_doc else 0
            start_down = stats_doc.get("start_conversation_down", 0) if stats_doc else 0
            continue_up = stats_doc.get("continue_conversation_up", 0) if stats_doc else 0
            continue_down = stats_doc.get("continue_conversation_down", 0) if stats_doc else 0

            # If there's existing feedback, decrement the old counts first
            if existing:
                old_feedback_type = existing.get("feedback_type")
                old_conversation_type = existing.get("conversation_type")
                old_language = existing.get("language")

                # Decrement old feedback counts
                if old_feedback_type == "thumbs_up":
                    total_up -= 1
                    if old_conversation_type == "start":
                        start_up -= 1
                    else:
                        continue_up -= 1
                else:
                    total_down -= 1
                    if old_conversation_type == "start":
                        start_down -= 1
                    else:
                        continue_down -= 1

                # Decrement old language stats
                if old_language and old_language in language_stats:
                    if old_feedback_type == "thumbs_up":
                        language_stats[old_language]["up"] = max(0, language_stats[old_language].get("up", 0) - 1)
                    else:
                        language_stats[old_language]["down"] = max(0, language_stats[old_language].get("down", 0) - 1)

            # Now increment the new counts
            if feedback_type == "thumbs_up":
                total_up += 1
                if conversation_type == "start":
                    start_up += 1
                else:
                    continue_up += 1
            else:
                total_down += 1
                if conversation_type == "start":
                    start_down += 1
                else:
                    continue_down += 1

            # Increment new language stats
            if language:
                if language not in language_stats:
                    language_stats[language] = {"up": 0, "down": 0}
                if feedback_type == "thumbs_up":
                    language_stats[language]["up"] += 1
                else:
                    language_stats[language]["down"] += 1

            total_feedback = total_up + total_down

            # Update aggregate stats
            self._feedback_stats.update_one(
                {"_id": "singleton"},
                {
                    "$set": {
                        "total_thumbs_up": total_up,
                        "total_thumbs_down": total_down,
                        "total_feedback": total_feedback,
                        "start_conversation_up": start_up,
                        "start_conversation_down": start_down,
                        "continue_conversation_up": continue_up,
                        "continue_conversation_down": continue_down,
                        "language_stats": language_stats,
                        "updated_at": datetime.utcnow()
                    }
                },
                upsert=True
            )

            # Upsert the individual feedback entry
            self._feedback_entries.update_one(
                {"response_id": response_id},
                {
                    "$set": {
                        "response_id": response_id,
                        "feedback_type": feedback_type,
                        "conversation_type": conversation_type,
                        "language": language,
                        "updated_at": datetime.utcnow()
                    },
                    "$setOnInsert": {
                        "created_at": datetime.utcnow()
                    }
                },
                upsert=True
            )

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

            # Clear all individual feedback entries
            self._feedback_entries.delete_many({})

            logger.info("✅ Feedback statistics cleared")

    async def save_research_questionnaire(self, questionnaire_data: Dict[str, Any]) -> str:
        """Save a research questionnaire response with validated instruments."""
        async with self._lock:
            # MongoDB stores nested objects natively, no need for JSON serialization
            document = {
                # Participant Information
                'participant_id': questionnaire_data.get('participant_id'),
                'email': questionnaire_data.get('email'),
                'submission_date': questionnaire_data.get('submission_date'),
                'native_language': questionnaire_data.get('native_language'),
                'country': questionnaire_data.get('country'),

                # Demographics
                'age_range': questionnaire_data.get('age_range'),
                'education_level': questionnaire_data.get('education_level'),
                'field_of_study': questionnaire_data.get('field_of_study'),
                'prior_climate_knowledge_self_rated': questionnaire_data.get('prior_climate_knowledge_self_rated'),

                # Consent
                'consent_agreed': questionnaire_data.get('consent_agreed', False),

                # MACK-12 Pre-Test
                'mack_pre': {
                    str(i): questionnaire_data.get(f'mack_pre_{i}')
                    for i in range(1, 13)
                },

                # Prior AI Experience
                'prior_ai_experience': {
                    'chatbot_usage': questionnaire_data.get('prior_chatbot_usage'),
                    'ai_familiarity': questionnaire_data.get('prior_ai_familiarity'),
                    'ai_trust_general': questionnaire_data.get('prior_ai_trust_general'),
                },

                # Task Tracking
                'tasks_completed': questionnaire_data.get('tasks_completed'),
                'task_queries': {
                    str(i): questionnaire_data.get(f'task_{i}_query')
                    for i in range(1, 6)
                },

                # UEQ-S (8 items)
                'ueq_s': {
                    'obstructive_supportive': questionnaire_data.get('ueq_1_obstructive_supportive'),
                    'complicated_easy': questionnaire_data.get('ueq_2_complicated_easy'),
                    'inefficient_efficient': questionnaire_data.get('ueq_3_inefficient_efficient'),
                    'confusing_clear': questionnaire_data.get('ueq_4_confusing_clear'),
                    'boring_exciting': questionnaire_data.get('ueq_5_boring_exciting'),
                    'not_interesting_interesting': questionnaire_data.get('ueq_6_not_interesting_interesting'),
                    'conventional_inventive': questionnaire_data.get('ueq_7_conventional_inventive'),
                    'usual_leading_edge': questionnaire_data.get('ueq_8_usual_leading_edge'),
                },

                # Trust Scale (12 items)
                'trust_scale': {
                    'reliable_information': questionnaire_data.get('trust_1_reliable_information'),
                    'accurate_responses': questionnaire_data.get('trust_2_accurate_responses'),
                    'trustworthy_system': questionnaire_data.get('trust_3_trustworthy_system'),
                    'confident_using': questionnaire_data.get('trust_4_confident_using'),
                    'dependable': questionnaire_data.get('trust_5_dependable'),
                    'consistent_quality': questionnaire_data.get('trust_6_consistent_quality'),
                    'comfortable_relying': questionnaire_data.get('trust_7_comfortable_relying'),
                    'positive_feelings': questionnaire_data.get('trust_8_positive_feelings'),
                    'emotionally_trustworthy': questionnaire_data.get('trust_9_emotionally_trustworthy'),
                    'sources_increase_trust': questionnaire_data.get('trust_10_sources_increase_trust'),
                    'transparency_helpful': questionnaire_data.get('trust_11_transparency_helpful'),
                    'would_recommend': questionnaire_data.get('trust_12_would_recommend'),
                },

                # NASA-TLX (6 subscales)
                'nasa_tlx': {
                    'mental_demand': questionnaire_data.get('nasa_mental_demand'),
                    'physical_demand': questionnaire_data.get('nasa_physical_demand'),
                    'temporal_demand': questionnaire_data.get('nasa_temporal_demand'),
                    'performance': questionnaire_data.get('nasa_performance'),
                    'effort': questionnaire_data.get('nasa_effort'),
                    'frustration': questionnaire_data.get('nasa_frustration'),
                },

                # RAG Transparency (5 items)
                'rag_transparency': {
                    'source_relevance': questionnaire_data.get('rag_source_relevance'),
                    'citation_quality': questionnaire_data.get('rag_citation_quality'),
                    'verifiability': questionnaire_data.get('rag_verifiability'),
                    'response_accuracy': questionnaire_data.get('rag_response_accuracy'),
                    'limitation_clarity': questionnaire_data.get('rag_limitation_clarity'),
                },

                # STP Evaluation
                'stp_evaluation': {
                    'shown': questionnaire_data.get('stp_shown'),
                    'understanding': questionnaire_data.get('stp_understanding'),
                    'clarity': questionnaire_data.get('stp_clarity'),
                    'influence': questionnaire_data.get('stp_influence'),
                },

                # KG Evaluation
                'kg_evaluation': {
                    'used': questionnaire_data.get('kg_used'),
                    'understanding': questionnaire_data.get('kg_understanding'),
                    'navigation': questionnaire_data.get('kg_navigation'),
                    'task_success': questionnaire_data.get('kg_task_success'),
                },

                # Multilingual Experience
                'multilingual': {
                    'used_non_english': questionnaire_data.get('used_non_english'),
                    'accuracy': questionnaire_data.get('ml_accuracy'),
                    'preference': questionnaire_data.get('ml_preference'),
                },

                # MACK-12 Post-Test
                'mack_post': {
                    str(i): questionnaire_data.get(f'mack_post_{i}')
                    for i in range(1, 13)
                },

                # Behavioral Intentions (5 items)
                'behavioral_intentions': {
                    'change_behavior': questionnaire_data.get('behavior_1_change_behavior'),
                    'discuss_others': questionnaire_data.get('behavior_2_discuss_others'),
                    'seek_information': questionnaire_data.get('behavior_3_seek_information'),
                    'support_policies': questionnaire_data.get('behavior_4_support_policies'),
                    'take_action': questionnaire_data.get('behavior_5_take_action'),
                },

                # Perceived Understanding
                'perceived_understanding': questionnaire_data.get('perceived_understanding'),

                # Open-Ended Feedback
                'most_useful_features': questionnaire_data.get('most_useful_features'),
                'suggested_improvements': questionnaire_data.get('suggested_improvements'),
                'additional_comments': questionnaire_data.get('additional_comments'),

                # Metadata
                'session_id': questionnaire_data.get('session_id'),
                'time_spent_seconds': questionnaire_data.get('time_spent_seconds'),
                'device_type': questionnaire_data.get('device_type'),
                'created_at': datetime.utcnow(),
            }

            result = self._research_questionnaires.insert_one(document)
            questionnaire_id = str(result.inserted_id)
            logger.info(f"✅ Research questionnaire saved with ID: {questionnaire_id}")
            return questionnaire_id

    async def get_research_questionnaires(self, limit: int = 100) -> list:
        """Get all research questionnaire responses."""
        async with self._lock:
            cursor = self._research_questionnaires.find().sort("created_at", DESCENDING).limit(limit)

            results = []
            for doc in cursor:
                doc['id'] = str(doc.pop('_id'))
                if doc.get('created_at'):
                    doc['created_at'] = doc['created_at'].isoformat()
                results.append(doc)

            return results

    async def get_questionnaire_stats(self) -> Dict[str, Any]:
        """Get statistics about questionnaire responses."""
        async with self._lock:
            total = self._research_questionnaires.count_documents({})

            # Note: These aggregations may need adjustment based on actual field names
            # The original SQLite code referenced fields that may not exist in the new structure
            return {
                "total_responses": total,
                "average_experience_rating": 0,  # Placeholder - adjust based on actual data
                "voice_feature_users": 0,  # Placeholder - adjust based on actual data
                "voice_usage_percentage": 0
            }

    async def close(self):
        """Close database connection."""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            self._session_stats = None
            self._feedback_stats = None
            self._feedback_entries = None
            self._research_questionnaires = None
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
