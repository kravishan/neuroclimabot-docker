"""
Document Processing Tracker
MongoDB-based tracking for document processing status across all pipelines
Supports multi-replica deployments in Kubernetes environments
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta

from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from storage.base import DocumentTrackerBackend
from config import config

logger = logging.getLogger(__name__)


class DocumentTracker(DocumentTrackerBackend):
    """
    MongoDB-based document processing tracker
    Tracks status for chunks, summaries, GraphRAG, and STP processing
    Designed for multi-replica Kubernetes deployments
    """

    def __init__(self):
        super().__init__()
        self._client = None
        self._db = None
        self._document_status = None
        self._news_articles_status = None
        self.connect()

    def _get_client(self) -> MongoClient:
        """Get or create MongoDB client with connection pooling"""
        if self._client is None:
            mongodb_config = config.get_mongodb_config()

            self._client = MongoClient(
                mongodb_config['connection_uri'],
                maxPoolSize=mongodb_config.get('max_pool_size', 100),
                minPoolSize=mongodb_config.get('min_pool_size', 10),
                serverSelectionTimeoutMS=mongodb_config.get('server_selection_timeout_ms', 5000),
                connectTimeoutMS=mongodb_config.get('connect_timeout_ms', 10000),
            )

            # Get database
            self._db = self._client[mongodb_config['database']]

            # Get collections
            self._document_status = self._db[mongodb_config['collections']['document_status']]
            self._news_articles_status = self._db[mongodb_config['collections']['news_articles_status']]

        return self._client

    def connect(self) -> None:
        """Initialize MongoDB connection and create indexes"""
        try:
            mongodb_config = config.get_mongodb_config()

            # Initialize client
            self._get_client()

            # Test connection
            self._client.admin.command('ping')

            # Create indexes for document_status collection
            self._document_status.create_index(
                [("doc_name", ASCENDING), ("bucket_source", ASCENDING)],
                unique=True,
                name="idx_doc_bucket"
            )
            self._document_status.create_index(
                [("stp_done", ASCENDING)],
                name="idx_stp_status"
            )
            self._document_status.create_index(
                [("bucket_source", ASCENDING)],
                name="idx_bucket"
            )
            self._document_status.create_index(
                [("updated_at", DESCENDING)],
                name="idx_updated_at"
            )

            # Create indexes for news_articles_status collection
            self._news_articles_status.create_index(
                [("source_url", ASCENDING), ("original_file", ASCENDING), ("bucket_source", ASCENDING)],
                unique=True,
                name="idx_news_source"
            )
            self._news_articles_status.create_index(
                [("original_file", ASCENDING), ("bucket_source", ASCENDING)],
                name="idx_original_file"
            )

            self.connected = True
            logger.info(f"MongoDB tracker initialized: {mongodb_config['host']}:{mongodb_config['port']}/{mongodb_config['database']}")

        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize MongoDB tracker: {e}")
            raise

    def disconnect(self) -> None:
        """Close MongoDB connection"""
        try:
            if self._client:
                self._client.close()
                self._client = None
                self._db = None
                self._document_status = None
                self._news_articles_status = None
            self.connected = False
            logger.info("MongoDB tracker disconnected")
        except Exception as e:
            logger.error(f"Disconnect error: {e}")

    def health_check(self) -> bool:
        """Check MongoDB connection health"""
        try:
            if self._client is None:
                return False
            self._client.admin.command('ping')
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
            now = datetime.utcnow()

            # Handle news articles separately if source_url provided
            if bucket == "news" and "source_url" in kwargs:
                self._mark_news_article_done(process_type, kwargs, doc_name, bucket, now)

            # Always track at document level
            # Build update document based on process type
            update_fields = {"updated_at": now}

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
            self._document_status.update_one(
                {"doc_name": doc_name, "bucket_source": bucket},
                {
                    "$set": update_fields,
                    "$setOnInsert": {
                        "doc_name": doc_name,
                        "bucket_source": bucket,
                        "chunks_done": process_type == "chunks",
                        "chunks_count": kwargs.get('count', 0) if process_type == "chunks" else 0,
                        "summary_done": process_type == "summary",
                        "graphrag_done": process_type == "graphrag",
                        "graphrag_entities_count": kwargs.get('entities', 0) if process_type == "graphrag" else 0,
                        "graphrag_relationships_count": kwargs.get('relationships', 0) if process_type == "graphrag" else 0,
                        "graphrag_communities_count": kwargs.get('communities', 0) if process_type == "graphrag" else 0,
                        "stp_done": process_type == "stp",
                        "stp_chunks_count": kwargs.get('total_chunks', 0) if process_type == "stp" else 0,
                        "stp_stp_count": kwargs.get('stp_count', 0) if process_type == "stp" else 0,
                        "stp_non_stp_count": kwargs.get('non_stp_count', 0) if process_type == "stp" else 0,
                        "created_at": now,
                    }
                },
                upsert=True
            )

            logger.info(f"Marked {process_type} done for {doc_name}")

        except Exception as e:
            logger.error(f"Failed to mark {process_type} done for {doc_name}: {e}")
            raise

    def _mark_news_article_done(self, process_type: str, kwargs: Dict[str, Any],
                                 doc_name: str, bucket: str, now: datetime) -> None:
        """Mark individual news article as done"""
        try:
            source_url = kwargs.get('source_url', '')
            article_title = kwargs.get('article_title', '')
            row_index = kwargs.get('row_index', 0)

            update_fields = {"updated_at": now}

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
            self._news_articles_status.update_one(
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
                        "chunks_done": process_type == "chunks",
                        "chunks_count": kwargs.get('count', 0) if process_type == "chunks" else 0,
                        "summary_done": process_type == "summary",
                        "stp_done": process_type == "stp",
                        "stp_chunks_count": kwargs.get('total_chunks', 0) if process_type == "stp" else 0,
                        "stp_stp_count": kwargs.get('stp_count', 0) if process_type == "stp" else 0,
                        "created_at": now,
                    }
                },
                upsert=True
            )

            logger.info(f"Marked {process_type} done for news article: {source_url}")

        except Exception as e:
            logger.error(f"Failed to mark news article {process_type} done: {e}")
            raise

    def get_status(self, doc_name: str, bucket: str) -> Dict[str, Any]:
        """Get processing status for a document"""
        try:
            doc = self._document_status.find_one(
                {"doc_name": doc_name, "bucket_source": bucket}
            )

            if not doc:
                return {
                    "doc_name": doc_name,
                    "bucket_source": bucket,
                    "is_complete": False,
                    "status": "not_found"
                }

            # Build status response
            status = {
                "id": str(doc.get("_id", "")),
                "doc_name": doc.get("doc_name"),
                "bucket_source": doc.get("bucket_source"),
                "chunks_done": doc.get("chunks_done", False),
                "chunks_count": doc.get("chunks_count", 0),
                "summary_done": doc.get("summary_done", False),
                "graphrag_done": doc.get("graphrag_done", False),
                "graphrag_entities_count": doc.get("graphrag_entities_count", 0),
                "graphrag_relationships_count": doc.get("graphrag_relationships_count", 0),
                "graphrag_communities_count": doc.get("graphrag_communities_count", 0),
                "stp_done": doc.get("stp_done", False),
                "stp_chunks_count": doc.get("stp_chunks_count", 0),
                "stp_stp_count": doc.get("stp_stp_count", 0),
                "stp_non_stp_count": doc.get("stp_non_stp_count", 0),
                "created_at": doc.get("created_at", "").isoformat() if doc.get("created_at") else None,
                "updated_at": doc.get("updated_at", "").isoformat() if doc.get("updated_at") else None,
            }

            status['is_complete'] = (
                status['chunks_done'] and
                status['summary_done'] and
                status['graphrag_done'] and
                status['stp_done']
            )

            # For news bucket, include article-level status
            if bucket == "news":
                news_articles = list(self._news_articles_status.find(
                    {"original_file": doc_name, "bucket_source": bucket}
                ).sort("row_index", ASCENDING))

                status['news_articles'] = []
                for article in news_articles:
                    status['news_articles'].append({
                        'source_url': article.get('source_url'),
                        'article_title': article.get('article_title'),
                        'row_index': article.get('row_index'),
                        'chunks_done': article.get('chunks_done', False),
                        'chunks_count': article.get('chunks_count', 0),
                        'summary_done': article.get('summary_done', False),
                        'stp_done': article.get('stp_done', False),
                        'stp_chunks_count': article.get('stp_chunks_count', 0),
                        'stp_stp_count': article.get('stp_stp_count', 0)
                    })

            return status

        except Exception as e:
            logger.error(f"Failed to get status for {doc_name}: {e}")
            return {"doc_name": doc_name, "bucket_source": bucket, "is_complete": False, "status": "error"}

    def get_all_documents(self, bucket_filter: str = None) -> List[Dict[str, Any]]:
        """Get all tracked documents"""
        try:
            query = {}
            if bucket_filter:
                query["bucket_source"] = bucket_filter

            docs = list(self._document_status.find(query).sort("updated_at", DESCENDING))

            documents = []
            for doc in docs:
                document = {
                    "id": str(doc.get("_id", "")),
                    "doc_name": doc.get("doc_name"),
                    "bucket_source": doc.get("bucket_source"),
                    "chunks_done": doc.get("chunks_done", False),
                    "chunks_count": doc.get("chunks_count", 0),
                    "summary_done": doc.get("summary_done", False),
                    "graphrag_done": doc.get("graphrag_done", False),
                    "graphrag_entities_count": doc.get("graphrag_entities_count", 0),
                    "graphrag_relationships_count": doc.get("graphrag_relationships_count", 0),
                    "graphrag_communities_count": doc.get("graphrag_communities_count", 0),
                    "stp_done": doc.get("stp_done", False),
                    "stp_chunks_count": doc.get("stp_chunks_count", 0),
                    "stp_stp_count": doc.get("stp_stp_count", 0),
                    "stp_non_stp_count": doc.get("stp_non_stp_count", 0),
                    "created_at": doc.get("created_at", "").isoformat() if doc.get("created_at") else None,
                    "updated_at": doc.get("updated_at", "").isoformat() if doc.get("updated_at") else None,
                }

                document['is_complete'] = (
                    document['chunks_done'] and
                    document['summary_done'] and
                    document['graphrag_done'] and
                    document['stp_done']
                )

                # For news documents, add article count
                if document['bucket_source'] == "news":
                    try:
                        article_count = self._news_articles_status.count_documents({
                            "original_file": document['doc_name'],
                            "bucket_source": document['bucket_source']
                        })
                        document['article_count'] = article_count
                    except Exception as e:
                        logger.warning(f"Could not fetch article count for {document['doc_name']}: {e}")
                        document['article_count'] = 0

                documents.append(document)

            return documents

        except Exception as e:
            logger.error(f"Failed to get all documents: {e}")
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
            # Document-level stats using aggregation
            total = self._document_status.count_documents({})

            completed = self._document_status.count_documents({
                "chunks_done": True,
                "summary_done": True,
                "graphrag_done": True,
                "stp_done": True
            })

            chunks_done = self._document_status.count_documents({"chunks_done": True})
            summary_done = self._document_status.count_documents({"summary_done": True})
            graphrag_done = self._document_status.count_documents({"graphrag_done": True})
            stp_done = self._document_status.count_documents({"stp_done": True})

            # STP-specific stats using aggregation
            stp_pipeline = [
                {"$group": {
                    "_id": None,
                    "total_stp_chunks": {"$sum": "$stp_stp_count"},
                    "total_non_stp_chunks": {"$sum": "$stp_non_stp_count"}
                }}
            ]
            stp_result = list(self._document_status.aggregate(stp_pipeline))
            total_stp_chunks = stp_result[0].get("total_stp_chunks", 0) if stp_result else 0
            total_non_stp_chunks = stp_result[0].get("total_non_stp_chunks", 0) if stp_result else 0

            # News-specific stats
            news_articles_total = self._news_articles_status.count_documents({})
            news_articles_completed = self._news_articles_status.count_documents({
                "chunks_done": True,
                "summary_done": True,
                "stp_done": True
            })

            # Bucket distribution using aggregation
            bucket_pipeline = [
                {"$group": {"_id": "$bucket_source", "count": {"$sum": 1}}}
            ]
            bucket_result = list(self._document_status.aggregate(bucket_pipeline))
            bucket_stats = {item["_id"]: item["count"] for item in bucket_result}

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
                "bucket_distribution": bucket_stats,
                "storage_backend": "mongodb"
            }

        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {
                "total_documents": 0,
                "completed_documents": 0,
                "completion_rate": "0%",
                "error": str(e),
                "storage_backend": "mongodb"
            }

    def cleanup_old_records(self, days: int = 90) -> int:
        """Remove tracking records older than specified days"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            # Delete old document status records
            doc_result = self._document_status.delete_many({
                "updated_at": {"$lt": cutoff_date}
            })

            # Delete old news article status records
            news_result = self._news_articles_status.delete_many({
                "updated_at": {"$lt": cutoff_date}
            })

            total_deleted = doc_result.deleted_count + news_result.deleted_count
            logger.info(f"Cleaned up {total_deleted} old tracking records (docs: {doc_result.deleted_count}, news: {news_result.deleted_count})")
            return total_deleted

        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            return 0


# Global instance
tracker = DocumentTracker()

logger.info("MongoDB document tracker loaded")
