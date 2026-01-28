"""
MongoDB-based Document Processing Tracker
Replaces SQLite tracker for multi-replica support in Kubernetes.
All Processor replicas can read/write to the same MongoDB database.
"""

import logging
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from pymongo import MongoClient, IndexModel, ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError

from storage.base import DocumentTrackerBackend

logger = logging.getLogger(__name__)


class MongoDBDocumentTracker(DocumentTrackerBackend):
    """
    MongoDB-based document processing tracker.
    Supports concurrent access from multiple Processor replicas.
    Tracks status for chunks, summaries, GraphRAG, and STP processing.
    """

    def __init__(
        self,
        host: str = None,
        port: int = None,
        username: str = None,
        password: str = None,
        database: str = None
    ):
        """Initialize MongoDB tracker with connection parameters from env or args."""
        super().__init__()

        # Get config from environment variables with fallbacks
        self.host = host or os.getenv("MONGODB_HOST", "mongodb")
        self.port = port or int(os.getenv("MONGODB_PORT", "27017"))
        self.username = username or os.getenv("MONGODB_USERNAME")
        self.password = password or os.getenv("MONGODB_PASSWORD")
        self.database_name = database or os.getenv("MONGODB_DATABASE", "neuroclima")

        # Collection names
        self.doc_status_collection = "document_status"
        self.news_articles_collection = "news_articles_status"

        self.client: Optional[MongoClient] = None
        self.db = None

    def _get_connection_uri(self) -> str:
        """Build MongoDB connection URI."""
        if self.username and self.password:
            return f"mongodb://{self.username}:{self.password}@{self.host}:{self.port}/{self.database_name}?authSource=admin"
        return f"mongodb://{self.host}:{self.port}/{self.database_name}"

    def connect(self) -> None:
        """Initialize MongoDB connection and create indexes."""
        try:
            # Create client with connection pooling
            self.client = MongoClient(
                self._get_connection_uri(),
                maxPoolSize=50,
                minPoolSize=10,
                maxIdleTimeMS=30000
            )

            # Test connection
            self.client.admin.command('ping')

            # Get database
            self.db = self.client[self.database_name]

            # Create indexes
            self._create_indexes()

            self.connected = True
            logger.info(f"MongoDB document tracker connected: {self.host}:{self.port}/{self.database_name}")

        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    def _create_indexes(self):
        """Create indexes for efficient querying."""
        try:
            # Document status indexes
            doc_collection = self.db[self.doc_status_collection]
            doc_collection.create_indexes([
                IndexModel([("doc_name", ASCENDING), ("bucket_source", ASCENDING)], unique=True),
                IndexModel([("bucket_source", ASCENDING)]),
                IndexModel([("stp_done", ASCENDING)]),
                IndexModel([("updated_at", DESCENDING)]),
            ])

            # News articles indexes
            news_collection = self.db[self.news_articles_collection]
            news_collection.create_indexes([
                IndexModel([
                    ("source_url", ASCENDING),
                    ("original_file", ASCENDING),
                    ("bucket_source", ASCENDING)
                ], unique=True),
                IndexModel([("original_file", ASCENDING), ("bucket_source", ASCENDING)]),
            ])

            logger.info("MongoDB indexes created successfully")

        except Exception as e:
            logger.warning(f"Index creation warning (may already exist): {e}")

    def disconnect(self) -> None:
        """Close MongoDB connection."""
        try:
            if self.client:
                self.client.close()
            self.connected = False
            logger.info("MongoDB document tracker disconnected")
        except Exception as e:
            logger.error(f"Disconnect error: {e}")

    def health_check(self) -> bool:
        """Check MongoDB connection health."""
        try:
            if not self.client:
                return False
            self.client.admin.command('ping')
            return True
        except Exception:
            return False

    def mark_done(self, process_type: str, doc_name: str, bucket: str, **kwargs) -> None:
        """
        Mark a process as complete for a document.

        Args:
            process_type: Type of process ('chunks', 'summary', 'graphrag', 'stp')
            doc_name: Document name
            bucket: Bucket source
            **kwargs: Additional process-specific data
        """
        try:
            collection = self.db[self.doc_status_collection]

            # Handle news articles separately if source_url provided
            if bucket == "news" and "source_url" in kwargs:
                self._mark_news_article_done(process_type, kwargs, doc_name, bucket)

            # Prepare update based on process type
            update_fields = {"updated_at": datetime.utcnow()}

            if process_type == "chunks":
                update_fields["chunks_done"] = True
                update_fields["chunks_count"] = kwargs.get('count', 0)
            elif process_type == "summary":
                update_fields["summary_done"] = True
            elif process_type == "graphrag":
                update_fields["graphrag_done"] = True
                update_fields["graphrag_entities_count"] = kwargs.get('entities', 0)
                update_fields["graphrag_relationships_count"] = kwargs.get('relationships', 0)
                update_fields["graphrag_communities_count"] = kwargs.get('communities', 0)
            elif process_type == "stp":
                update_fields["stp_done"] = True
                update_fields["stp_chunks_count"] = kwargs.get('total_chunks', 0)
                update_fields["stp_stp_count"] = kwargs.get('stp_count', 0)
                update_fields["stp_non_stp_count"] = kwargs.get('non_stp_count', 0)

            # Upsert document status
            collection.update_one(
                {"doc_name": doc_name, "bucket_source": bucket},
                {
                    "$set": update_fields,
                    "$setOnInsert": {
                        "doc_name": doc_name,
                        "bucket_source": bucket,
                        "chunks_done": False,
                        "chunks_count": 0,
                        "summary_done": False,
                        "graphrag_done": False,
                        "graphrag_entities_count": 0,
                        "graphrag_relationships_count": 0,
                        "graphrag_communities_count": 0,
                        "stp_done": False,
                        "stp_chunks_count": 0,
                        "stp_stp_count": 0,
                        "stp_non_stp_count": 0,
                        "created_at": datetime.utcnow()
                    }
                },
                upsert=True
            )

            logger.info(f"Marked {process_type} done for {doc_name}")

        except Exception as e:
            logger.error(f"Failed to mark {process_type} done for {doc_name}: {e}")
            raise

    def _mark_news_article_done(self, process_type: str, kwargs: Dict[str, Any], doc_name: str, bucket: str) -> None:
        """Mark individual news article as done."""
        try:
            collection = self.db[self.news_articles_collection]

            source_url = kwargs.get('source_url', '')
            article_title = kwargs.get('article_title', '')
            row_index = kwargs.get('row_index', 0)

            # Prepare update based on process type
            update_fields = {"updated_at": datetime.utcnow()}

            if process_type == "chunks":
                update_fields["chunks_done"] = True
                update_fields["chunks_count"] = kwargs.get('count', 0)
            elif process_type == "summary":
                update_fields["summary_done"] = True
            elif process_type == "stp":
                update_fields["stp_done"] = True
                update_fields["stp_chunks_count"] = kwargs.get('total_chunks', 0)
                update_fields["stp_stp_count"] = kwargs.get('stp_count', 0)

            # Upsert news article status
            collection.update_one(
                {
                    "source_url": source_url,
                    "original_file": doc_name,
                    "bucket_source": bucket
                },
                {
                    "$set": update_fields,
                    "$setOnInsert": {
                        "source_url": source_url,
                        "original_file": doc_name,
                        "bucket_source": bucket,
                        "article_title": article_title,
                        "row_index": row_index,
                        "chunks_done": False,
                        "chunks_count": 0,
                        "summary_done": False,
                        "stp_done": False,
                        "stp_chunks_count": 0,
                        "stp_stp_count": 0,
                        "created_at": datetime.utcnow()
                    }
                },
                upsert=True
            )

            logger.info(f"Marked {process_type} done for news article: {source_url}")

        except Exception as e:
            logger.error(f"Failed to mark news article {process_type} done: {e}")
            raise

    def get_status(self, doc_name: str, bucket: str) -> Dict[str, Any]:
        """Get processing status for a document."""
        try:
            collection = self.db[self.doc_status_collection]
            doc = collection.find_one({"doc_name": doc_name, "bucket_source": bucket})

            if not doc:
                return {
                    "doc_name": doc_name,
                    "bucket_source": bucket,
                    "is_complete": False,
                    "status": "not_found"
                }

            # Convert ObjectId to string
            doc["_id"] = str(doc["_id"])

            # Calculate is_complete
            doc["is_complete"] = (
                doc.get("chunks_done", False) and
                doc.get("summary_done", False) and
                doc.get("graphrag_done", False) and
                doc.get("stp_done", False)
            )

            # For news bucket, include article-level status
            if bucket == "news":
                news_collection = self.db[self.news_articles_collection]
                news_articles = list(news_collection.find(
                    {"original_file": doc_name, "bucket_source": bucket}
                ).sort("row_index", ASCENDING))

                doc["news_articles"] = []
                for article in news_articles:
                    doc["news_articles"].append({
                        "source_url": article.get("source_url"),
                        "article_title": article.get("article_title"),
                        "row_index": article.get("row_index"),
                        "chunks_done": article.get("chunks_done", False),
                        "chunks_count": article.get("chunks_count", 0),
                        "summary_done": article.get("summary_done", False),
                        "stp_done": article.get("stp_done", False),
                        "stp_chunks_count": article.get("stp_chunks_count", 0),
                        "stp_stp_count": article.get("stp_stp_count", 0)
                    })

            return doc

        except Exception as e:
            logger.error(f"Failed to get status for {doc_name}: {e}")
            return {"doc_name": doc_name, "bucket_source": bucket, "is_complete": False, "status": "error"}

    def get_all_documents(self, bucket_filter: str = None) -> List[Dict[str, Any]]:
        """Get all tracked documents."""
        try:
            collection = self.db[self.doc_status_collection]

            query = {}
            if bucket_filter:
                query["bucket_source"] = bucket_filter

            documents = list(collection.find(query).sort("updated_at", DESCENDING))

            result = []
            for doc in documents:
                doc["_id"] = str(doc["_id"])
                doc["is_complete"] = (
                    doc.get("chunks_done", False) and
                    doc.get("summary_done", False) and
                    doc.get("graphrag_done", False) and
                    doc.get("stp_done", False)
                )

                # For news documents, add article count
                if doc.get("bucket_source") == "news":
                    news_collection = self.db[self.news_articles_collection]
                    doc["article_count"] = news_collection.count_documents({
                        "original_file": doc["doc_name"],
                        "bucket_source": doc["bucket_source"]
                    })

                result.append(doc)

            return result

        except Exception as e:
            logger.error(f"Failed to get all documents: {e}")
            return []

    def is_processed(self, doc_name: str, bucket: str, process_type: str) -> bool:
        """Check if a specific process is complete for a document."""
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
        """Get comprehensive processing statistics."""
        try:
            collection = self.db[self.doc_status_collection]
            news_collection = self.db[self.news_articles_collection]

            # Document-level stats using aggregation
            pipeline = [
                {
                    "$group": {
                        "_id": None,
                        "total": {"$sum": 1},
                        "completed": {
                            "$sum": {
                                "$cond": [
                                    {"$and": [
                                        {"$eq": ["$chunks_done", True]},
                                        {"$eq": ["$summary_done", True]},
                                        {"$eq": ["$graphrag_done", True]},
                                        {"$eq": ["$stp_done", True]}
                                    ]},
                                    1, 0
                                ]
                            }
                        },
                        "chunks_done": {"$sum": {"$cond": ["$chunks_done", 1, 0]}},
                        "summary_done": {"$sum": {"$cond": ["$summary_done", 1, 0]}},
                        "graphrag_done": {"$sum": {"$cond": ["$graphrag_done", 1, 0]}},
                        "stp_done": {"$sum": {"$cond": ["$stp_done", 1, 0]}},
                        "total_stp_chunks": {"$sum": "$stp_stp_count"},
                        "total_non_stp_chunks": {"$sum": "$stp_non_stp_count"}
                    }
                }
            ]

            result = list(collection.aggregate(pipeline))
            stats = result[0] if result else {
                "total": 0, "completed": 0, "chunks_done": 0, "summary_done": 0,
                "graphrag_done": 0, "stp_done": 0, "total_stp_chunks": 0, "total_non_stp_chunks": 0
            }

            # News-specific stats
            news_total = news_collection.count_documents({})
            news_completed = news_collection.count_documents({
                "chunks_done": True,
                "summary_done": True,
                "stp_done": True
            })

            # Bucket distribution
            bucket_pipeline = [
                {"$group": {"_id": "$bucket_source", "count": {"$sum": 1}}}
            ]
            bucket_result = list(collection.aggregate(bucket_pipeline))
            bucket_stats = {item["_id"]: item["count"] for item in bucket_result}

            total = stats.get("total", 0)
            completed = stats.get("completed", 0)
            total_stp = stats.get("total_stp_chunks", 0)
            total_non_stp = stats.get("total_non_stp_chunks", 0)

            return {
                "total_documents": total,
                "completed_documents": completed,
                "completion_rate": f"{(completed/total)*100:.1f}%" if total > 0 else "0%",
                "process_counts": {
                    "chunks_processed": stats.get("chunks_done", 0),
                    "summaries_processed": stats.get("summary_done", 0),
                    "graphrag_processed": stats.get("graphrag_done", 0),
                    "stp_processed": stats.get("stp_done", 0)
                },
                "stp_statistics": {
                    "total_stp_chunks": total_stp,
                    "total_non_stp_chunks": total_non_stp,
                    "stp_ratio": f"{(total_stp/(total_stp+total_non_stp))*100:.1f}%" if (total_stp+total_non_stp) > 0 else "0%"
                },
                "news_statistics": {
                    "total_articles": news_total,
                    "completed_articles": news_completed,
                    "completion_rate": f"{(news_completed/news_total)*100:.1f}%" if news_total > 0 else "0%"
                },
                "bucket_distribution": bucket_stats
            }

        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {
                "total_documents": 0,
                "completed_documents": 0,
                "completion_rate": "0%",
                "error": str(e)
            }

    def cleanup_old_records(self, days: int = 90) -> int:
        """Remove tracking records older than specified days."""
        try:
            from datetime import timedelta
            collection = self.db[self.doc_status_collection]

            cutoff_date = datetime.utcnow() - timedelta(days=days)
            result = collection.delete_many({"updated_at": {"$lt": cutoff_date}})

            deleted_count = result.deleted_count
            logger.info(f"Cleaned up {deleted_count} old tracking records")
            return deleted_count

        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            return 0


# Factory function for creating tracker based on environment
def create_document_tracker():
    """
    Create a document tracker based on environment configuration.
    Uses MongoDB if MONGODB_HOST is set, otherwise falls back to SQLite.
    """
    mongodb_host = os.getenv("MONGODB_HOST")

    if mongodb_host:
        logger.info("Using MongoDB document tracker")
        tracker = MongoDBDocumentTracker()
        tracker.connect()
        return tracker
    else:
        logger.info("Using SQLite document tracker (MONGODB_HOST not set)")
        from storage.database import DocumentTracker
        return DocumentTracker()


# Global instance - will be set based on environment
tracker = None


def get_tracker():
    """Get or create the global tracker instance."""
    global tracker
    if tracker is None:
        tracker = create_document_tracker()
    return tracker


logger.info("MongoDB document tracker module loaded")
