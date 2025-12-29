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
