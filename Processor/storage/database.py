"""
Document Processing Tracker
SQLite-based tracking for document processing status across all pipelines
"""

import logging
import sqlite3
import threading
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime

from storage.base import DocumentTrackerBackend

logger = logging.getLogger(__name__)


def get_expected_processes_for_bucket(bucket: str) -> Dict[str, bool]:
    """
    Determine which processes are expected for each bucket type.
    Returns dict with keys: chunks, summary, graphrag, stp
    """
    # Default: all processes enabled
    expected = {
        'chunks': True,
        'summary': True,
        'graphrag': True,
        'stp': True
    }

    # Scientific data: only chunks and summary
    if bucket == "scientificdata":
        expected['graphrag'] = False
        expected['stp'] = False

    # Add more bucket-specific rules here as needed
    # Example: if bucket == "otherbucket": expected['graphrag'] = False

    return expected


class DocumentTracker(DocumentTrackerBackend):
    """
    SQLite-based document processing tracker
    Tracks status for chunks, summaries, GraphRAG, and STP processing
    """

    def __init__(self, db_path: str = "./processing_tracker.db"):
        super().__init__()
        self.db_path = Path(db_path)
        self._local = threading.local()
        self.connect()

    def _get_connection(self):
        """Get thread-local database connection"""
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self._local.connection.execute("PRAGMA journal_mode=WAL")
        return self._local.connection

    def connect(self) -> None:
        """Initialize tracking database with all required tables"""
        try:
            # Ensure parent directory exists
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute("PRAGMA journal_mode=WAL")

                # Main document status table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS document_status (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        doc_name TEXT NOT NULL,
                        bucket_source TEXT NOT NULL,
                        chunks_done BOOLEAN DEFAULT FALSE,
                        chunks_count INTEGER DEFAULT 0,
                        summary_done BOOLEAN DEFAULT FALSE,
                        graphrag_done BOOLEAN DEFAULT FALSE,
                        graphrag_entities_count INTEGER DEFAULT 0,
                        graphrag_relationships_count INTEGER DEFAULT 0,
                        graphrag_communities_count INTEGER DEFAULT 0,
                        stp_done BOOLEAN DEFAULT FALSE,
                        stp_chunks_count INTEGER DEFAULT 0,
                        stp_stp_count INTEGER DEFAULT 0,
                        stp_non_stp_count INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(doc_name, bucket_source)
                    )
                """)

                # News articles tracking table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS news_articles_status (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        source_url TEXT NOT NULL,
                        original_file TEXT NOT NULL,
                        bucket_source TEXT NOT NULL,
                        article_title TEXT,
                        row_index INTEGER,
                        chunks_done BOOLEAN DEFAULT FALSE,
                        chunks_count INTEGER DEFAULT 0,
                        summary_done BOOLEAN DEFAULT FALSE,
                        stp_done BOOLEAN DEFAULT FALSE,
                        stp_chunks_count INTEGER DEFAULT 0,
                        stp_stp_count INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(source_url, original_file, bucket_source)
                    )
                """)

                # Create indexes for performance
                conn.execute("CREATE INDEX IF NOT EXISTS idx_doc_bucket ON document_status(doc_name, bucket_source)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_news_source ON news_articles_status(source_url, original_file)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_stp_status ON document_status(stp_done)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_bucket ON document_status(bucket_source)")

                conn.commit()

            self.connected = True
            logger.info(f"✅ Document tracker initialized: {self.db_path}")

        except Exception as e:
            logger.error(f"❌ Failed to initialize document tracker: {e}")
            raise

    def disconnect(self) -> None:
        """Close database connections"""
        try:
            if hasattr(self._local, 'connection'):
                self._local.connection.close()
            self.connected = False
            logger.info("✅ Document tracker disconnected")
        except Exception as e:
            logger.error(f"❌ Disconnect error: {e}")

    def health_check(self) -> bool:
        """Check database health"""
        try:
            conn = self._get_connection()
            conn.execute("SELECT 1").fetchone()
            return True
        except Exception:
            return False

    def mark_done(self, process_type: str, doc_name: str, bucket: str, **kwargs) -> None:
        """
        Mark a process as complete for a document

        Args:
            process_type: Type of process ('chunks', 'summary', 'graphrag', 'stp')
            doc_name: Document name
            bucket: Bucket source
            **kwargs: Additional process-specific data
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Handle news articles separately if source_url provided
            if bucket == "news" and "source_url" in kwargs:
                self._mark_news_article_done(cursor, process_type, kwargs, doc_name, bucket)

            # Always track at document level
            cursor.execute(
                "INSERT OR IGNORE INTO document_status (doc_name, bucket_source) VALUES (?, ?)",
                (doc_name, bucket)
            )

            # Update based on process type
            if process_type == "chunks":
                cursor.execute(
                    "UPDATE document_status SET chunks_done = TRUE, chunks_count = ?, updated_at = CURRENT_TIMESTAMP WHERE doc_name = ? AND bucket_source = ?",
                    (kwargs.get('count', 0), doc_name, bucket)
                )
            elif process_type == "summary":
                cursor.execute(
                    "UPDATE document_status SET summary_done = TRUE, updated_at = CURRENT_TIMESTAMP WHERE doc_name = ? AND bucket_source = ?",
                    (doc_name, bucket)
                )
            elif process_type == "graphrag":
                cursor.execute(
                    "UPDATE document_status SET graphrag_done = TRUE, graphrag_entities_count = ?, graphrag_relationships_count = ?, graphrag_communities_count = ?, updated_at = CURRENT_TIMESTAMP WHERE doc_name = ? AND bucket_source = ?",
                    (kwargs.get('entities', 0), kwargs.get('relationships', 0), kwargs.get('communities', 0), doc_name, bucket)
                )
            elif process_type == "stp":
                cursor.execute(
                    "UPDATE document_status SET stp_done = TRUE, stp_chunks_count = ?, stp_stp_count = ?, stp_non_stp_count = ?, updated_at = CURRENT_TIMESTAMP WHERE doc_name = ? AND bucket_source = ?",
                    (kwargs.get('total_chunks', 0), kwargs.get('stp_count', 0), kwargs.get('non_stp_count', 0), doc_name, bucket)
                )

            conn.commit()
            logger.info(f"✅ Marked {process_type} done for {doc_name}")

        except Exception as e:
            logger.error(f"❌ Failed to mark {process_type} done for {doc_name}: {e}")
            conn.rollback()
            raise

    def _mark_news_article_done(self, cursor, process_type: str, kwargs: Dict[str, Any], doc_name: str, bucket: str) -> None:
        """Mark individual news article as done"""
        try:
            source_url = kwargs.get('source_url', '')
            article_title = kwargs.get('article_title', '')
            row_index = kwargs.get('row_index', 0)

            # Ensure news article record exists
            cursor.execute("""
                INSERT OR IGNORE INTO news_articles_status
                (source_url, original_file, bucket_source, article_title, row_index)
                VALUES (?, ?, ?, ?, ?)
            """, (source_url, doc_name, bucket, article_title, row_index))

            # Update based on process type
            if process_type == "chunks":
                cursor.execute("""
                    UPDATE news_articles_status
                    SET chunks_done = TRUE, chunks_count = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE source_url = ? AND original_file = ? AND bucket_source = ?
                """, (kwargs.get('count', 0), source_url, doc_name, bucket))
            elif process_type == "summary":
                cursor.execute("""
                    UPDATE news_articles_status
                    SET summary_done = TRUE, updated_at = CURRENT_TIMESTAMP
                    WHERE source_url = ? AND original_file = ? AND bucket_source = ?
                """, (source_url, doc_name, bucket))
            elif process_type == "stp":
                cursor.execute("""
                    UPDATE news_articles_status
                    SET stp_done = TRUE, stp_chunks_count = ?, stp_stp_count = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE source_url = ? AND original_file = ? AND bucket_source = ?
                """, (kwargs.get('total_chunks', 0), kwargs.get('stp_count', 0), source_url, doc_name, bucket))

            logger.info(f"✅ Marked {process_type} done for news article: {source_url}")

        except Exception as e:
            logger.error(f"❌ Failed to mark news article {process_type} done: {e}")
            raise

    def get_status(self, doc_name: str, bucket: str) -> Dict[str, Any]:
        """Get processing status for a document"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            row = cursor.execute(
                "SELECT * FROM document_status WHERE doc_name = ? AND bucket_source = ?",
                (doc_name, bucket)
            ).fetchone()

            if not row:
                return {
                    "doc_name": doc_name,
                    "bucket_source": bucket,
                    "is_complete": False,
                    "status": "not_found"
                }

            # Column mapping
            columns = ['id', 'doc_name', 'bucket_source', 'chunks_done', 'chunks_count',
                      'summary_done', 'graphrag_done', 'graphrag_entities_count',
                      'graphrag_relationships_count', 'graphrag_communities_count',
                      'stp_done', 'stp_chunks_count', 'stp_stp_count', 'stp_non_stp_count',
                      'created_at', 'updated_at']

            status = dict(zip(columns, row))

            # Determine completeness based on expected processes for this bucket
            expected = get_expected_processes_for_bucket(bucket)
            is_complete = True
            if expected['chunks'] and not status['chunks_done']:
                is_complete = False
            if expected['summary'] and not status['summary_done']:
                is_complete = False
            if expected['graphrag'] and not status['graphrag_done']:
                is_complete = False
            if expected['stp'] and not status['stp_done']:
                is_complete = False

            status['is_complete'] = is_complete

            # For news bucket, include article-level status
            if bucket == "news":
                news_articles = cursor.execute("""
                    SELECT source_url, article_title, row_index, chunks_done, chunks_count,
                           summary_done, stp_done, stp_chunks_count, stp_stp_count
                    FROM news_articles_status
                    WHERE original_file = ? AND bucket_source = ?
                    ORDER BY row_index
                """, (doc_name, bucket)).fetchall()

                status['news_articles'] = []
                for article_row in news_articles:
                    status['news_articles'].append({
                        'source_url': article_row[0],
                        'article_title': article_row[1],
                        'row_index': article_row[2],
                        'chunks_done': bool(article_row[3]),
                        'chunks_count': article_row[4],
                        'summary_done': bool(article_row[5]),
                        'stp_done': bool(article_row[6]),
                        'stp_chunks_count': article_row[7],
                        'stp_stp_count': article_row[8]
                    })

            return status

        except Exception as e:
            logger.error(f"❌ Failed to get status for {doc_name}: {e}")
            return {"doc_name": doc_name, "bucket_source": bucket, "is_complete": False, "status": "error"}

    def get_all_documents(self, bucket_filter: str = None) -> List[Dict[str, Any]]:
        """Get all tracked documents"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            query = "SELECT * FROM document_status"
            params = []

            if bucket_filter:
                query += " WHERE bucket_source = ?"
                params.append(bucket_filter)

            query += " ORDER BY updated_at DESC"

            rows = cursor.execute(query, params).fetchall()

            columns = ['id', 'doc_name', 'bucket_source', 'chunks_done', 'chunks_count',
                      'summary_done', 'graphrag_done', 'graphrag_entities_count',
                      'graphrag_relationships_count', 'graphrag_communities_count',
                      'stp_done', 'stp_chunks_count', 'stp_stp_count', 'stp_non_stp_count',
                      'created_at', 'updated_at']

            documents = []
            for row in rows:
                doc = dict(zip(columns, row))

                # Determine completeness based on expected processes for this bucket
                expected = get_expected_processes_for_bucket(doc['bucket_source'])
                is_complete = True
                if expected['chunks'] and not doc['chunks_done']:
                    is_complete = False
                if expected['summary'] and not doc['summary_done']:
                    is_complete = False
                if expected['graphrag'] and not doc['graphrag_done']:
                    is_complete = False
                if expected['stp'] and not doc['stp_done']:
                    is_complete = False

                doc['is_complete'] = is_complete

                # For news documents, add article count
                if doc['bucket_source'] == "news":
                    try:
                        article_count = cursor.execute("""
                            SELECT COUNT(*) FROM news_articles_status
                            WHERE original_file = ? AND bucket_source = ?
                        """, (doc['doc_name'], doc['bucket_source'])).fetchone()[0]
                        doc['article_count'] = article_count
                    except Exception as e:
                        logger.warning(f"⚠️ Could not fetch article count for {doc['doc_name']}: {e}")
                        doc['article_count'] = 0

                documents.append(doc)

            return documents

        except Exception as e:
            logger.error(f"❌ Failed to get all documents: {e}")
            return []

    def is_processed(self, doc_name: str, bucket: str, process_type: str) -> bool:
        """Check if a specific process is complete for a document"""
        status = self.get_status(doc_name, bucket)
        if status.get("status") == "not_found" or status.get("status") == "error":
            return False

        process_field_map = {
            'chunks': 'chunks_done',
            'summary': 'summary_done',
            'graphrag': 'graphrag_done',
            'stp': 'stp_done'
        }

        field = process_field_map.get(process_type)
        if not field:
            return False

        return bool(status.get(field, False))

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive processing statistics"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Document-level stats
            total = cursor.execute("SELECT COUNT(*) FROM document_status").fetchone()[0]
            completed = cursor.execute("""
                SELECT COUNT(*) FROM document_status
                WHERE chunks_done = 1 AND summary_done = 1 AND graphrag_done = 1 AND stp_done = 1
            """).fetchone()[0]
            chunks_done = cursor.execute("SELECT COUNT(*) FROM document_status WHERE chunks_done = 1").fetchone()[0]
            summary_done = cursor.execute("SELECT COUNT(*) FROM document_status WHERE summary_done = 1").fetchone()[0]
            graphrag_done = cursor.execute("SELECT COUNT(*) FROM document_status WHERE graphrag_done = 1").fetchone()[0]
            stp_done = cursor.execute("SELECT COUNT(*) FROM document_status WHERE stp_done = 1").fetchone()[0]

            # STP-specific stats
            total_stp_chunks = cursor.execute("SELECT SUM(stp_stp_count) FROM document_status").fetchone()[0] or 0
            total_non_stp_chunks = cursor.execute("SELECT SUM(stp_non_stp_count) FROM document_status").fetchone()[0] or 0

            # News-specific stats
            news_articles_total = cursor.execute("SELECT COUNT(*) FROM news_articles_status").fetchone()[0]
            news_articles_completed = cursor.execute("""
                SELECT COUNT(*) FROM news_articles_status
                WHERE chunks_done = 1 AND summary_done = 1 AND stp_done = 1
            """).fetchone()[0]

            # Bucket distribution
            cursor.execute("SELECT bucket_source, COUNT(*) FROM document_status GROUP BY bucket_source")
            bucket_stats = {row[0]: row[1] for row in cursor.fetchall()}

            return {
                "total_documents": total,
                "completed_documents": completed,
                "completion_rate": f"{(completed/total)*100:.1f}%" if total > 0 else "0%",
                "process_counts": {
                    "chunks_processed": chunks_done,
                    "summaries_processed": summary_done,
                    "graphrag_processed": graphrag_done,
                    "stp_processed": stp_done
                },
                "stp_statistics": {
                    "total_stp_chunks": total_stp_chunks,
                    "total_non_stp_chunks": total_non_stp_chunks,
                    "stp_ratio": f"{(total_stp_chunks/(total_stp_chunks+total_non_stp_chunks))*100:.1f}%" if (total_stp_chunks+total_non_stp_chunks) > 0 else "0%"
                },
                "news_statistics": {
                    "total_articles": news_articles_total,
                    "completed_articles": news_articles_completed,
                    "completion_rate": f"{(news_articles_completed/news_articles_total)*100:.1f}%" if news_articles_total > 0 else "0%"
                },
                "bucket_distribution": bucket_stats
            }

        except Exception as e:
            logger.error(f"❌ Failed to get stats: {e}")
            return {
                "total_documents": 0,
                "completed_documents": 0,
                "completion_rate": "0%",
                "error": str(e)
            }

    def cleanup_old_records(self, days: int = 90) -> int:
        """Remove tracking records older than specified days"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute(f"""
                DELETE FROM document_status
                WHERE updated_at < datetime('now', '-{days} days')
            """)

            deleted_count = cursor.rowcount
            conn.commit()

            logger.info(f"🗑️ Cleaned up {deleted_count} old tracking records")
            return deleted_count

        except Exception as e:
            logger.error(f"❌ Cleanup failed: {e}")
            return 0



# Global instance
tracker = DocumentTracker()

logger.info("✅ Document tracker loaded")
