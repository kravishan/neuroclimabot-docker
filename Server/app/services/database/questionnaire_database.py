"""MongoDB database for research questionnaire storage."""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime

from pymongo import MongoClient, DESCENDING
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from bson import ObjectId

from app.utils.logger import get_logger
from app.config.database import get_mongodb_config

logger = get_logger(__name__)


class QuestionnaireDatabase:
    """Persistent storage for research questionnaire responses using MongoDB."""

    def __init__(self):
        """Initialize database connection."""
        self._client: Optional[MongoClient] = None
        self._db = None
        self._collection = None
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

            # Get database and collection
            self._db = self._client[mongodb_config.DATABASE]
            self._collection = self._db['questionnaire_responses']

            # Create indexes
            self._collection.create_index([("created_at", DESCENDING)], name="idx_created_at")
            self._collection.create_index([("participant_id", DESCENDING)], name="idx_participant_id")
            self._collection.create_index([("email", DESCENDING)], name="idx_email")

            self.connected = True
            logger.info(f"✅ Questionnaire database initialized: MongoDB {mongodb_config.HOST}:{mongodb_config.PORT}/{mongodb_config.DATABASE}")

        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize questionnaire database: {e}")
            raise

    async def save_questionnaire(self, questionnaire_data: Dict[str, Any]) -> str:
        """Save a research questionnaire response."""
        async with self._lock:
            try:
                # Prepare document - MongoDB stores nested objects natively
                document = {
                    # Participant Information
                    'participant_id': questionnaire_data.get('participant_id'),
                    'email': questionnaire_data.get('email'),

                    # Demographics
                    'age_range': questionnaire_data.get('age_range'),
                    'education_level': questionnaire_data.get('education_level'),
                    'country': questionnaire_data.get('country'),
                    'native_language': questionnaire_data.get('native_language'),
                    'prior_climate_knowledge': questionnaire_data.get('prior_climate_knowledge'),
                    'prior_ai_experience': questionnaire_data.get('prior_ai_experience'),

                    # Consent
                    'consent_all': questionnaire_data.get('consent_all', False),

                    # Section 1: Your Recent Experience
                    'primary_purpose': questionnaire_data.get('primary_purpose'),
                    'other_purpose': questionnaire_data.get('other_purpose'),
                    'task_type': questionnaire_data.get('task_type', []),

                    # Section 2: Task Success & Completion
                    'task_success': questionnaire_data.get('task_success', {}),
                    'info_finding': questionnaire_data.get('info_finding', {}),

                    # Section 3: Document & Source Quality
                    'doc_quality': questionnaire_data.get('doc_quality', {}),
                    'info_adequacy': questionnaire_data.get('info_adequacy', {}),

                    # Section 4: UEQ-S
                    'ueq_s': questionnaire_data.get('ueq_s', {}),

                    # Section 5: Trust Scale
                    'trust_scale': questionnaire_data.get('trust_scale', {}),

                    # Section 6: NASA-TLX
                    'nasa_tlx': questionnaire_data.get('nasa_tlx', {}),

                    # Section 7: Conversational Quality
                    'conversational_quality': questionnaire_data.get('conversational_quality', {}),

                    # Section 8: Feature-Specific Evaluations
                    'stp_evaluation': questionnaire_data.get('stp_evaluation', {}),
                    'kg_visualization': questionnaire_data.get('kg_visualization', {}),
                    'multilingual': questionnaire_data.get('multilingual', {}),
                    'used_kg_viz': questionnaire_data.get('used_kg_viz', False),
                    'used_non_english': questionnaire_data.get('used_non_english', False),

                    # Section 9: RAG Transparency & Behavioral Intentions (deprecated but kept)
                    'rag_transparency': questionnaire_data.get('rag_transparency', {}),
                    'behavioral_intentions': questionnaire_data.get('behavioral_intentions', {}),

                    # Section 10: Open-Ended Feedback
                    'most_useful_features': questionnaire_data.get('most_useful_features'),
                    'suggested_improvements': questionnaire_data.get('suggested_improvements'),
                    'additional_comments': questionnaire_data.get('additional_comments'),

                    # Metadata
                    'submission_date': questionnaire_data.get('submission_date'),
                    'time_started': questionnaire_data.get('time_started'),
                    'time_per_section': questionnaire_data.get('time_per_section', {}),
                    'total_time_seconds': questionnaire_data.get('total_time_seconds'),

                    'created_at': datetime.utcnow(),
                }

                result = self._collection.insert_one(document)
                questionnaire_id = str(result.inserted_id)
                logger.info(f"✅ Questionnaire saved successfully with ID: {questionnaire_id}")
                return questionnaire_id

            except Exception as e:
                logger.error(f"Error saving questionnaire: {e}", exc_info=True)
                raise

    async def get_questionnaires(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all questionnaire responses."""
        async with self._lock:
            cursor = self._collection.find().sort("created_at", DESCENDING).limit(limit)

            results = []
            for doc in cursor:
                # Convert ObjectId to string for JSON serialization
                doc['id'] = str(doc.pop('_id'))
                # Convert datetime to ISO string
                if doc.get('created_at'):
                    doc['created_at'] = doc['created_at'].isoformat()
                results.append(doc)

            return results

    async def get_questionnaire_by_id(self, questionnaire_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific questionnaire response by ID."""
        async with self._lock:
            try:
                doc = self._collection.find_one({"_id": ObjectId(questionnaire_id)})
                if doc:
                    doc['id'] = str(doc.pop('_id'))
                    if doc.get('created_at'):
                        doc['created_at'] = doc['created_at'].isoformat()
                    return doc
                return None
            except Exception as e:
                logger.error(f"Error getting questionnaire by ID: {e}")
                return None

    async def get_questionnaire_count(self) -> int:
        """Get total count of questionnaire responses."""
        async with self._lock:
            return self._collection.count_documents({})

    async def close(self):
        """Close database connection."""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            self._collection = None
            self.connected = False
            logger.info("✅ Questionnaire database connection closed")

    async def health_check(self) -> bool:
        """Check database health."""
        try:
            if not self._client:
                return False
            self._client.admin.command('ping')
            return True
        except Exception as e:
            logger.error(f"Questionnaire database health check failed: {e}")
            return False

    # Property for backward compatibility
    @property
    def connection(self):
        """Backward compatibility property."""
        return self._client


# Global instance
questionnaire_database = QuestionnaireDatabase()


async def get_questionnaire_database() -> QuestionnaireDatabase:
    """Get the questionnaire database instance."""
    if not questionnaire_database.connected:
        await questionnaire_database.initialize()
    return questionnaire_database
