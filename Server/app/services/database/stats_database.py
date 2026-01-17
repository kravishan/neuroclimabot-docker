"""SQLite database for persistent session stats and feedback storage."""

import sqlite3
import json
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from app.utils.logger import get_logger

logger = get_logger(__name__)


class StatsDatabase:
    """Persistent storage for session statistics and feedback data."""

    def __init__(self, db_path: str = "data/stats.db"):
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

            logger.info(f"✅ Stats database initialized at {self.db_path}")

        except Exception as e:
            logger.error(f"Failed to initialize stats database: {e}")
            raise

    async def _create_tables(self):
        """Create database tables if they don't exist."""
        async with self._lock:
            cursor = self.connection.cursor()

            # Session stats table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS session_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    total_sessions INTEGER DEFAULT 0,
                    avg_messages_per_session REAL DEFAULT 0.0,
                    avg_response_time REAL DEFAULT 0.0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Feedback stats table (aggregate counts)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS feedback_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    total_thumbs_up INTEGER DEFAULT 0,
                    total_thumbs_down INTEGER DEFAULT 0,
                    total_feedback INTEGER DEFAULT 0,
                    start_conversation_up INTEGER DEFAULT 0,
                    start_conversation_down INTEGER DEFAULT 0,
                    continue_conversation_up INTEGER DEFAULT 0,
                    continue_conversation_down INTEGER DEFAULT 0,
                    language_stats TEXT DEFAULT '{}',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Individual feedback entries table (to track and replace duplicates by response_id)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS feedback_entries (
                    response_id TEXT PRIMARY KEY,
                    feedback_type TEXT NOT NULL,
                    conversation_type TEXT NOT NULL,
                    language TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Research questionnaire responses table - CHI 2027 validated instruments
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS research_questionnaires (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    -- Participant Information
                    participant_id TEXT,
                    email TEXT,
                    submission_date TEXT NOT NULL,
                    native_language TEXT,
                    country TEXT,

                    -- Demographics (Optional)
                    age_range TEXT,
                    education_level TEXT,
                    field_of_study TEXT,
                    prior_climate_knowledge_self_rated INTEGER,

                    -- Simplified Consent (Single checkbox)
                    consent_agreed INTEGER NOT NULL,

                    -- MACK-12 Climate Knowledge Pre-Test (1-5 scale)
                    mack_pre_1 INTEGER,
                    mack_pre_2 INTEGER,
                    mack_pre_3 INTEGER,
                    mack_pre_4 INTEGER,
                    mack_pre_5 INTEGER,
                    mack_pre_6 INTEGER,
                    mack_pre_7 INTEGER,
                    mack_pre_8 INTEGER,
                    mack_pre_9 INTEGER,
                    mack_pre_10 INTEGER,
                    mack_pre_11 INTEGER,
                    mack_pre_12 INTEGER,

                    -- Prior AI Experience (1-7 Likert)
                    prior_chatbot_usage INTEGER,
                    prior_ai_familiarity INTEGER,
                    prior_ai_trust_general INTEGER,

                    -- Task Completion Tracking
                    tasks_completed TEXT,
                    task_1_query TEXT,
                    task_2_query TEXT,
                    task_3_query TEXT,
                    task_4_query TEXT,
                    task_5_query TEXT,

                    -- UEQ-S User Experience (8 items, 1-7 scale)
                    ueq_1_obstructive_supportive INTEGER,
                    ueq_2_complicated_easy INTEGER,
                    ueq_3_inefficient_efficient INTEGER,
                    ueq_4_confusing_clear INTEGER,
                    ueq_5_boring_exciting INTEGER,
                    ueq_6_not_interesting_interesting INTEGER,
                    ueq_7_conventional_inventive INTEGER,
                    ueq_8_usual_leading_edge INTEGER,

                    -- Human-AI Trust Scale (12 items, 1-7 Likert)
                    trust_1_reliable_information INTEGER,
                    trust_2_accurate_responses INTEGER,
                    trust_3_trustworthy_system INTEGER,
                    trust_4_confident_using INTEGER,
                    trust_5_dependable INTEGER,
                    trust_6_consistent_quality INTEGER,
                    trust_7_comfortable_relying INTEGER,
                    trust_8_positive_feelings INTEGER,
                    trust_9_emotionally_trustworthy INTEGER,
                    trust_10_sources_increase_trust INTEGER,
                    trust_11_transparency_helpful INTEGER,
                    trust_12_would_recommend INTEGER,

                    -- NASA-TLX Cognitive Load (6 subscales, 0-100 scale)
                    nasa_mental_demand INTEGER,
                    nasa_physical_demand INTEGER,
                    nasa_temporal_demand INTEGER,
                    nasa_performance INTEGER,
                    nasa_effort INTEGER,
                    nasa_frustration INTEGER,

                    -- RAG Transparency & Quality (5 items, 1-7 Likert)
                    rag_source_relevance INTEGER,
                    rag_citation_quality INTEGER,
                    rag_verifiability INTEGER,
                    rag_response_accuracy INTEGER,
                    rag_limitation_clarity INTEGER,

                    -- Social Tipping Points Evaluation (if applicable, 1-7 Likert)
                    stp_shown INTEGER,
                    stp_understanding INTEGER,
                    stp_clarity INTEGER,
                    stp_influence INTEGER,

                    -- Knowledge Graph Evaluation (if applicable, 1-7 Likert)
                    kg_used INTEGER,
                    kg_understanding INTEGER,
                    kg_navigation INTEGER,
                    kg_task_success INTEGER,

                    -- Multilingual Experience (if non-English, 1-7 Likert)
                    used_non_english INTEGER,
                    ml_accuracy INTEGER,
                    ml_preference INTEGER,

                    -- MACK-12 Climate Knowledge Post-Test (1-5 scale)
                    mack_post_1 INTEGER,
                    mack_post_2 INTEGER,
                    mack_post_3 INTEGER,
                    mack_post_4 INTEGER,
                    mack_post_5 INTEGER,
                    mack_post_6 INTEGER,
                    mack_post_7 INTEGER,
                    mack_post_8 INTEGER,
                    mack_post_9 INTEGER,
                    mack_post_10 INTEGER,
                    mack_post_11 INTEGER,
                    mack_post_12 INTEGER,

                    -- Behavioral Intentions (5 items, 1-7 Likert)
                    behavior_1_change_behavior INTEGER,
                    behavior_2_discuss_others INTEGER,
                    behavior_3_seek_information INTEGER,
                    behavior_4_support_policies INTEGER,
                    behavior_5_take_action INTEGER,

                    -- Perceived Understanding (1-7 Likert)
                    perceived_understanding INTEGER,

                    -- Open-Ended Feedback
                    most_useful_features TEXT,
                    suggested_improvements TEXT,
                    additional_comments TEXT,

                    -- Metadata
                    session_id TEXT,
                    time_spent_seconds INTEGER,
                    device_type TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            self.connection.commit()

            # Initialize with default values if empty (ensure only ONE record with id=1)
            cursor.execute("SELECT COUNT(*) FROM session_stats")
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                    INSERT INTO session_stats (id, total_sessions, avg_messages_per_session, avg_response_time)
                    VALUES (1, 0, 0.0, 0.0)
                """)
            else:
                # Ensure we only have one record - delete any extras
                cursor.execute("DELETE FROM session_stats WHERE id > 1")

            cursor.execute("SELECT COUNT(*) FROM feedback_stats")
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                    INSERT INTO feedback_stats (
                        id, total_thumbs_up, total_thumbs_down, total_feedback,
                        start_conversation_up, start_conversation_down,
                        continue_conversation_up, continue_conversation_down,
                        language_stats
                    ) VALUES (1, 0, 0, 0, 0, 0, 0, 0, '{}')
                """)
            else:
                # Ensure we only have one record - delete any extras
                cursor.execute("DELETE FROM feedback_stats WHERE id > 1")

            self.connection.commit()

    async def get_session_stats(self) -> Dict[str, Any]:
        """Get current session statistics (always from the single record with id=1)."""
        async with self._lock:
            cursor = self.connection.cursor()
            cursor.execute("SELECT * FROM session_stats WHERE id = 1")
            row = cursor.fetchone()

            if row:
                return {
                    "total_sessions": row["total_sessions"],
                    "avg_messages_per_session": row["avg_messages_per_session"],
                    "avg_response_time": row["avg_response_time"]
                }
            return {
                "total_sessions": 0,
                "avg_messages_per_session": 0.0,
                "avg_response_time": 0.0
            }

    async def update_session_stats(self, total_sessions: int, avg_messages: float, avg_response_time: float):
        """Update session statistics (always updates the single record with id=1)."""
        async with self._lock:
            cursor = self.connection.cursor()
            cursor.execute("""
                UPDATE session_stats
                SET total_sessions = ?,
                    avg_messages_per_session = ?,
                    avg_response_time = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
            """, (total_sessions, avg_messages, avg_response_time))
            self.connection.commit()

    async def increment_session_count(self):
        """Increment total session count (always updates the single record with id=1)."""
        async with self._lock:
            cursor = self.connection.cursor()
            cursor.execute("""
                UPDATE session_stats
                SET total_sessions = total_sessions + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
            """)
            self.connection.commit()

    async def record_session_message(self, message_count: int):
        """Record a completed session's message count and update average (updates single record id=1)."""
        async with self._lock:
            cursor = self.connection.cursor()

            # Get current stats from the single record
            cursor.execute("SELECT total_sessions, avg_messages_per_session FROM session_stats WHERE id = 1")
            row = cursor.fetchone()

            if row:
                current_avg = row["avg_messages_per_session"]
                current_total = row["total_sessions"]

                # Calculate new average using exponential moving average
                # Weight: 90% current avg, 10% new value for stability
                new_avg = (current_avg * 0.9) + (message_count * 0.1) if current_avg > 0 else message_count
                new_total = current_total + 1

                cursor.execute("""
                    UPDATE session_stats
                    SET total_sessions = ?,
                        avg_messages_per_session = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = 1
                """, (new_total, new_avg))
                self.connection.commit()

    async def record_response_time(self, response_time: float):
        """Record a response time and update average (updates single record id=1)."""
        async with self._lock:
            cursor = self.connection.cursor()

            # Get current stats from the single record
            cursor.execute("SELECT avg_response_time FROM session_stats WHERE id = 1")
            row = cursor.fetchone()

            if row:
                current_avg = row["avg_response_time"]

                # Use exponential moving average for response time
                # Weight: 90% current avg, 10% new value
                new_avg = (current_avg * 0.9) + (response_time * 0.1) if current_avg > 0 else response_time

                cursor.execute("""
                    UPDATE session_stats
                    SET avg_response_time = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = 1
                """, (new_avg,))
                self.connection.commit()

    async def get_feedback_stats(self) -> Dict[str, Any]:
        """Get ALL feedback statistics (from the single record with id=1)."""
        async with self._lock:
            cursor = self.connection.cursor()
            cursor.execute("SELECT * FROM feedback_stats WHERE id = 1")
            row = cursor.fetchone()

            if row:
                language_stats = json.loads(row["language_stats"])
                return {
                    "total_thumbs_up": row["total_thumbs_up"],
                    "total_thumbs_down": row["total_thumbs_down"],
                    "total_feedback": row["total_feedback"],
                    "start_conversation_stats": {
                        "up": row["start_conversation_up"],
                        "down": row["start_conversation_down"]
                    },
                    "continue_conversation_stats": {
                        "up": row["continue_conversation_up"],
                        "down": row["continue_conversation_down"]
                    },
                    "language_stats": language_stats
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
            cursor = self.connection.cursor()

            # Check if there's existing feedback for this response_id
            cursor.execute(
                "SELECT feedback_type, conversation_type, language FROM feedback_entries WHERE response_id = ?",
                (response_id,)
            )
            existing = cursor.fetchone()

            # Get current aggregate stats
            cursor.execute("SELECT * FROM feedback_stats WHERE id = 1")
            row = cursor.fetchone()

            # Parse current language stats
            language_stats = json.loads(row["language_stats"]) if row else {}

            # Prepare update values (start with current values)
            total_up = row["total_thumbs_up"] if row else 0
            total_down = row["total_thumbs_down"] if row else 0
            start_up = row["start_conversation_up"] if row else 0
            start_down = row["start_conversation_down"] if row else 0
            continue_up = row["continue_conversation_up"] if row else 0
            continue_down = row["continue_conversation_down"] if row else 0

            # If there's existing feedback, decrement the old counts first
            if existing:
                old_feedback_type = existing["feedback_type"]
                old_conversation_type = existing["conversation_type"]
                old_language = existing["language"]

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
                        language_stats[old_language]["up"] = max(0, language_stats[old_language]["up"] - 1)
                    else:
                        language_stats[old_language]["down"] = max(0, language_stats[old_language]["down"] - 1)

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
            cursor.execute("""
                UPDATE feedback_stats
                SET total_thumbs_up = ?,
                    total_thumbs_down = ?,
                    total_feedback = ?,
                    start_conversation_up = ?,
                    start_conversation_down = ?,
                    continue_conversation_up = ?,
                    continue_conversation_down = ?,
                    language_stats = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
            """, (
                total_up, total_down, total_feedback,
                start_up, start_down, continue_up, continue_down,
                json.dumps(language_stats)
            ))

            # Insert or update the individual feedback entry
            cursor.execute("""
                INSERT INTO feedback_entries (response_id, feedback_type, conversation_type, language, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(response_id) DO UPDATE SET
                    feedback_type = excluded.feedback_type,
                    conversation_type = excluded.conversation_type,
                    language = excluded.language,
                    updated_at = CURRENT_TIMESTAMP
            """, (response_id, feedback_type, conversation_type, language))

            self.connection.commit()

    async def clear_feedback_stats(self):
        """Clear all feedback statistics (resets the single record with id=1 and clears all entries)."""
        async with self._lock:
            cursor = self.connection.cursor()

            # Clear aggregate stats
            cursor.execute("""
                UPDATE feedback_stats
                SET total_thumbs_up = 0,
                    total_thumbs_down = 0,
                    total_feedback = 0,
                    start_conversation_up = 0,
                    start_conversation_down = 0,
                    continue_conversation_up = 0,
                    continue_conversation_down = 0,
                    language_stats = '{}',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
            """)

            # Clear all individual feedback entries
            cursor.execute("DELETE FROM feedback_entries")

            self.connection.commit()
            logger.info("✅ Feedback statistics cleared")

    async def save_research_questionnaire(self, questionnaire_data: Dict[str, Any]) -> int:
        """Save a research questionnaire response with validated instruments."""
        async with self._lock:
            cursor = self.connection.cursor()

            # Prepare fields for all validated instruments
            fields = [
                'participant_id', 'email', 'submission_date', 'native_language', 'country',
                'age_range', 'education_level', 'field_of_study', 'prior_climate_knowledge_self_rated',
                'consent_agreed',
                # MACK-12 Pre
                'mack_pre_1', 'mack_pre_2', 'mack_pre_3', 'mack_pre_4', 'mack_pre_5', 'mack_pre_6',
                'mack_pre_7', 'mack_pre_8', 'mack_pre_9', 'mack_pre_10', 'mack_pre_11', 'mack_pre_12',
                # Prior AI Experience
                'prior_chatbot_usage', 'prior_ai_familiarity', 'prior_ai_trust_general',
                # Task Tracking
                'tasks_completed', 'task_1_query', 'task_2_query', 'task_3_query', 'task_4_query', 'task_5_query',
                # UEQ-S
                'ueq_1_obstructive_supportive', 'ueq_2_complicated_easy', 'ueq_3_inefficient_efficient',
                'ueq_4_confusing_clear', 'ueq_5_boring_exciting', 'ueq_6_not_interesting_interesting',
                'ueq_7_conventional_inventive', 'ueq_8_usual_leading_edge',
                # Trust Scale
                'trust_1_reliable_information', 'trust_2_accurate_responses', 'trust_3_trustworthy_system',
                'trust_4_confident_using', 'trust_5_dependable', 'trust_6_consistent_quality',
                'trust_7_comfortable_relying', 'trust_8_positive_feelings', 'trust_9_emotionally_trustworthy',
                'trust_10_sources_increase_trust', 'trust_11_transparency_helpful', 'trust_12_would_recommend',
                # NASA-TLX
                'nasa_mental_demand', 'nasa_physical_demand', 'nasa_temporal_demand',
                'nasa_performance', 'nasa_effort', 'nasa_frustration',
                # RAG Transparency
                'rag_source_relevance', 'rag_citation_quality', 'rag_verifiability',
                'rag_response_accuracy', 'rag_limitation_clarity',
                # STP Evaluation
                'stp_shown', 'stp_understanding', 'stp_clarity', 'stp_influence',
                # KG Evaluation
                'kg_used', 'kg_understanding', 'kg_navigation', 'kg_task_success',
                # Multilingual
                'used_non_english', 'ml_accuracy', 'ml_preference',
                # MACK-12 Post
                'mack_post_1', 'mack_post_2', 'mack_post_3', 'mack_post_4', 'mack_post_5', 'mack_post_6',
                'mack_post_7', 'mack_post_8', 'mack_post_9', 'mack_post_10', 'mack_post_11', 'mack_post_12',
                # Behavioral Intentions
                'behavior_1_change_behavior', 'behavior_2_discuss_others', 'behavior_3_seek_information',
                'behavior_4_support_policies', 'behavior_5_take_action',
                # Perceived Understanding
                'perceived_understanding',
                # Open-Ended
                'most_useful_features', 'suggested_improvements', 'additional_comments',
                # Metadata
                'session_id', 'time_spent_seconds', 'device_type'
            ]

            # Build VALUES placeholder
            placeholders = ', '.join(['?'] * len(fields))
            field_names = ', '.join(fields)

            # Get values from questionnaire_data
            values = []
            for field in fields:
                value = questionnaire_data.get(field)
                # Handle JSON serialization for tasks_completed
                if field == 'tasks_completed' and isinstance(value, (list, dict)):
                    value = json.dumps(value)
                # Convert boolean to int for consent_agreed
                elif field == 'consent_agreed' and isinstance(value, bool):
                    value = 1 if value else 0
                values.append(value)

            cursor.execute(f"""
                INSERT INTO research_questionnaires ({field_names})
                VALUES ({placeholders})
            """, tuple(values))

            self.connection.commit()
            questionnaire_id = cursor.lastrowid
            logger.info(f"✅ Research questionnaire saved with ID: {questionnaire_id}")
            return questionnaire_id

    async def get_research_questionnaires(self, limit: int = 100) -> list:
        """Get all research questionnaire responses."""
        async with self._lock:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT * FROM research_questionnaires
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))

            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_questionnaire_stats(self) -> Dict[str, Any]:
        """Get statistics about questionnaire responses."""
        async with self._lock:
            cursor = self.connection.cursor()

            # Total responses
            cursor.execute("SELECT COUNT(*) as total FROM research_questionnaires")
            total = cursor.fetchone()['total']

            # Average experience rating
            cursor.execute("SELECT AVG(overall_experience_rating) as avg_rating FROM research_questionnaires WHERE overall_experience_rating IS NOT NULL")
            avg_rating = cursor.fetchone()['avg_rating'] or 0

            # Voice feature usage
            cursor.execute("SELECT COUNT(*) as voice_users FROM research_questionnaires WHERE used_voice_feature = 1")
            voice_users = cursor.fetchone()['voice_users']

            return {
                "total_responses": total,
                "average_experience_rating": round(avg_rating, 2),
                "voice_feature_users": voice_users,
                "voice_usage_percentage": round((voice_users / total * 100) if total > 0 else 0, 2)
            }

    async def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
            logger.info("✅ Stats database connection closed")

    async def health_check(self) -> bool:
        """Check database health."""
        try:
            if not self.connection:
                return False

            cursor = self.connection.cursor()
            cursor.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Stats database health check failed: {e}")
            return False


# Global instance
stats_database = StatsDatabase()


async def get_stats_database() -> StatsDatabase:
    """Get the stats database instance."""
    if not stats_database.connection:
        await stats_database.initialize()
    return stats_database
