"""SQLite database for research questionnaire storage."""

import sqlite3
import json
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

from app.utils.logger import get_logger

logger = get_logger(__name__)


class QuestionnaireDatabase:
    """Persistent storage for research questionnaire responses."""

    def __init__(self, db_path: str = "data/questionnaire.db"):
        """Initialize database connection."""
        self.db_path = db_path
        self.connection: Optional[sqlite3.Connection] = None
        self._lock = asyncio.Lock()

    async def initialize(self):
        """Initialize database and create tables."""
        try:
            # Ensure directory exists
            db_dir = Path(self.db_path).parent
            db_dir.mkdir(parents=True, exist_ok=True)

            # Create connection
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row

            # Create tables
            await self._create_tables()

            logger.info(f"✅ Questionnaire database initialized at {self.db_path}")

        except Exception as e:
            logger.error(f"Failed to initialize questionnaire database: {e}")
            raise

    async def _create_tables(self):
        """Create database tables if they don't exist."""
        async with self._lock:
            cursor = self.connection.cursor()

            # Questionnaire responses table - stores all questionnaire data as JSON for flexibility
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS questionnaire_responses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    -- Participant Information
                    participant_id TEXT,
                    email TEXT,

                    -- Demographics (simple fields)
                    age_range TEXT,
                    education_level TEXT,
                    country TEXT,
                    native_language TEXT,
                    prior_climate_knowledge INTEGER,
                    prior_ai_experience INTEGER,

                    -- Consent
                    consent_all INTEGER NOT NULL,

                    -- Section 1: Your Recent Experience
                    primary_purpose TEXT,
                    other_purpose TEXT,
                    task_type TEXT,  -- JSON array

                    -- Section 2: Task Success & Completion (JSON)
                    task_success TEXT,  -- JSON object
                    info_finding TEXT,  -- JSON object

                    -- Section 3: Document & Source Quality (JSON)
                    doc_quality TEXT,  -- JSON object
                    info_adequacy TEXT,  -- JSON object

                    -- Section 4: UEQ-S (JSON)
                    ueq_s TEXT,  -- JSON object with 8 items

                    -- Section 5: Trust Scale (JSON)
                    trust_scale TEXT,  -- JSON object with 12 items

                    -- Section 6: NASA-TLX (JSON)
                    nasa_tlx TEXT,  -- JSON object with 6 subscales

                    -- Section 7: Conversational Quality (JSON)
                    conversational_quality TEXT,  -- JSON object with 5 items

                    -- Section 8: Feature-Specific Evaluations (JSON)
                    stp_evaluation TEXT,  -- JSON object
                    kg_visualization TEXT,  -- JSON object
                    multilingual TEXT,  -- JSON object
                    used_kg_viz INTEGER,
                    used_non_english INTEGER,

                    -- Section 9: RAG Transparency & Behavioral Intentions (JSON)
                    rag_transparency TEXT,  -- JSON object
                    behavioral_intentions TEXT,  -- JSON object

                    -- Section 10: Open-Ended Feedback
                    most_useful_features TEXT,
                    suggested_improvements TEXT,
                    additional_comments TEXT,

                    -- Metadata
                    submission_date TEXT,
                    time_started TEXT,
                    time_per_section TEXT,  -- JSON object
                    total_time_seconds REAL,

                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            self.connection.commit()
            logger.info("✅ Questionnaire tables created successfully")

    async def save_questionnaire(self, questionnaire_data: Dict[str, Any]) -> int:
        """Save a research questionnaire response."""
        async with self._lock:
            cursor = self.connection.cursor()

            try:
                # Extract and prepare fields
                fields = {
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

                    # Consent (convert boolean to int)
                    'consent_all': 1 if questionnaire_data.get('consent_all') else 0,

                    # Section 1: Your Recent Experience
                    'primary_purpose': questionnaire_data.get('primary_purpose'),
                    'other_purpose': questionnaire_data.get('other_purpose'),
                    'task_type': json.dumps(questionnaire_data.get('task_type', [])),

                    # Section 2: Task Success & Completion
                    'task_success': json.dumps(questionnaire_data.get('task_success', {})),
                    'info_finding': json.dumps(questionnaire_data.get('info_finding', {})),

                    # Section 3: Document & Source Quality
                    'doc_quality': json.dumps(questionnaire_data.get('doc_quality', {})),
                    'info_adequacy': json.dumps(questionnaire_data.get('info_adequacy', {})),

                    # Section 4: UEQ-S
                    'ueq_s': json.dumps(questionnaire_data.get('ueq_s', {})),

                    # Section 5: Trust Scale
                    'trust_scale': json.dumps(questionnaire_data.get('trust_scale', {})),

                    # Section 6: NASA-TLX
                    'nasa_tlx': json.dumps(questionnaire_data.get('nasa_tlx', {})),

                    # Section 7: Conversational Quality
                    'conversational_quality': json.dumps(questionnaire_data.get('conversational_quality', {})),

                    # Section 8: Feature-Specific Evaluations
                    'stp_evaluation': json.dumps(questionnaire_data.get('stp_evaluation', {})),
                    'kg_visualization': json.dumps(questionnaire_data.get('kg_visualization', {})),
                    'multilingual': json.dumps(questionnaire_data.get('multilingual', {})),
                    'used_kg_viz': 1 if questionnaire_data.get('used_kg_viz') else 0,
                    'used_non_english': 1 if questionnaire_data.get('used_non_english') else 0,

                    # Section 9: RAG Transparency & Behavioral Intentions
                    'rag_transparency': json.dumps(questionnaire_data.get('rag_transparency', {})),
                    'behavioral_intentions': json.dumps(questionnaire_data.get('behavioral_intentions', {})),

                    # Section 10: Open-Ended Feedback
                    'most_useful_features': questionnaire_data.get('most_useful_features'),
                    'suggested_improvements': questionnaire_data.get('suggested_improvements'),
                    'additional_comments': questionnaire_data.get('additional_comments'),

                    # Metadata
                    'submission_date': questionnaire_data.get('submission_date'),
                    'time_started': questionnaire_data.get('time_started'),
                    'time_per_section': json.dumps(questionnaire_data.get('time_per_section', {})),
                    'total_time_seconds': questionnaire_data.get('total_time_seconds'),
                }

                # Build SQL query
                field_names = ', '.join(fields.keys())
                placeholders = ', '.join(['?'] * len(fields))
                values = tuple(fields.values())

                cursor.execute(f"""
                    INSERT INTO questionnaire_responses ({field_names})
                    VALUES ({placeholders})
                """, values)

                self.connection.commit()
                questionnaire_id = cursor.lastrowid
                logger.info(f"✅ Questionnaire saved successfully with ID: {questionnaire_id}")
                return questionnaire_id

            except Exception as e:
                logger.error(f"Error saving questionnaire: {e}", exc_info=True)
                raise

    async def get_questionnaires(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all questionnaire responses."""
        async with self._lock:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT * FROM questionnaire_responses
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))

            rows = cursor.fetchall()

            # Convert rows to dicts and parse JSON fields
            results = []
            for row in rows:
                row_dict = dict(row)

                # Parse JSON fields
                json_fields = [
                    'task_type', 'task_success', 'info_finding', 'doc_quality',
                    'info_adequacy', 'ueq_s', 'trust_scale', 'nasa_tlx',
                    'conversational_quality', 'stp_evaluation', 'kg_visualization',
                    'multilingual', 'rag_transparency', 'behavioral_intentions',
                    'time_per_section'
                ]

                for field in json_fields:
                    if row_dict.get(field):
                        try:
                            row_dict[field] = json.loads(row_dict[field])
                        except:
                            row_dict[field] = {}

                results.append(row_dict)

            return results

    async def get_questionnaire_by_id(self, questionnaire_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific questionnaire response by ID."""
        async with self._lock:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT * FROM questionnaire_responses
                WHERE id = ?
            """, (questionnaire_id,))

            row = cursor.fetchone()
            if row:
                row_dict = dict(row)

                # Parse JSON fields
                json_fields = [
                    'task_type', 'task_success', 'info_finding', 'doc_quality',
                    'info_adequacy', 'ueq_s', 'trust_scale', 'nasa_tlx',
                    'conversational_quality', 'stp_evaluation', 'kg_visualization',
                    'multilingual', 'rag_transparency', 'behavioral_intentions',
                    'time_per_section'
                ]

                for field in json_fields:
                    if row_dict.get(field):
                        try:
                            row_dict[field] = json.loads(row_dict[field])
                        except:
                            row_dict[field] = {}

                return row_dict
            return None

    async def get_questionnaire_count(self) -> int:
        """Get total count of questionnaire responses."""
        async with self._lock:
            cursor = self.connection.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM questionnaire_responses")
            return cursor.fetchone()['count']

    async def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
            logger.info("✅ Questionnaire database connection closed")

    async def health_check(self) -> bool:
        """Check database health."""
        try:
            if not self.connection:
                return False

            cursor = self.connection.cursor()
            cursor.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Questionnaire database health check failed: {e}")
            return False


# Global instance
questionnaire_database = QuestionnaireDatabase()


async def get_questionnaire_database() -> QuestionnaireDatabase:
    """Get the questionnaire database instance."""
    if not questionnaire_database.connection:
        await questionnaire_database.initialize()
    return questionnaire_database
