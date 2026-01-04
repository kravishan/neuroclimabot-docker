"""
Processing Tracker Utilities
Helper functions and utilities for tracking document processing
"""

import logging
from typing import Dict, Any, List
from pathlib import Path

from storage.database import tracker

logger = logging.getLogger(__name__)


class ProcessingTracker:
    """
    Wrapper class for document tracking with convenience methods

    """

    def __init__(self):
        self.tracker = tracker

    def mark_chunks_done(self, doc_name: str, bucket_source: str, chunks_count: int):
        """Mark chunks processing as complete"""
        self.tracker.mark_done('chunks', doc_name, bucket_source, count=chunks_count)

    def mark_summary_done(self, doc_name: str, bucket_source: str):
        """Mark summary processing as complete"""
        self.tracker.mark_done('summary', doc_name, bucket_source)

    def mark_graphrag_done(self, doc_name: str, bucket_source: str,
                          entities_count: int = 0, relationships_count: int = 0,
                          communities_count: int = 0):
        """Mark GraphRAG processing as complete"""
        self.tracker.mark_done(
            'graphrag', doc_name, bucket_source,
            entities=entities_count,
            relationships=relationships_count,
            communities=communities_count
        )

    def mark_stp_done(self, doc_name: str, bucket_source: str,
                     total_chunks: int = 0, stp_count: int = 0, non_stp_count: int = 0):
        """Mark STP processing as complete"""
        self.tracker.mark_done(
            'stp', doc_name, bucket_source,
            total_chunks=total_chunks,
            stp_count=stp_count,
            non_stp_count=non_stp_count
        )

    def get_document_status(self, doc_name: str, bucket_source: str) -> Dict[str, Any]:
        """Get processing status for a document"""
        return self.tracker.get_status(doc_name, bucket_source)

    def get_all_documents(self, bucket_filter: str = None) -> List[Dict[str, Any]]:
        """Get all processed documents"""
        return self.tracker.get_all_documents(bucket_filter)

    def is_document_processed(self, doc_name: str, bucket_source: str,
                            require_chunks: bool = True, require_summary: bool = True,
                            require_graphrag: bool = False, require_stp: bool = False) -> bool:
        """
        Check if document meets processing requirements

        Args:
            doc_name: Document name
            bucket_source: Bucket source
            require_chunks: Require chunks processing
            require_summary: Require summary processing
            require_graphrag: Require GraphRAG processing
            require_stp: Require STP processing

        Returns:
            True if all required processing is complete
        """
        status = self.tracker.get_status(doc_name, bucket_source)

        if status.get("status") == "not_found" or status.get("status") == "error":
            return False

        checks = []
        if require_chunks:
            checks.append(status.get("chunks_done", False))
        if require_summary:
            checks.append(status.get("summary_done", False))
        if require_graphrag:
            checks.append(status.get("graphrag_done", False))
        if require_stp:
            checks.append(status.get("stp_done", False))

        return all(checks) if checks else False

    def get_summary_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        return self.tracker.get_stats()

    def _calculate_progress(self, chunks_done: bool, summary_done: bool,
                          graphrag_done: bool, stp_done: bool) -> int:
        """Calculate progress percentage"""
        completed = sum([chunks_done, summary_done, graphrag_done, stp_done])
        return int((completed / 4) * 100)

    def cleanup_old_records(self, days: int = 90) -> int:
        """Clean up old tracking records"""
        return self.tracker.cleanup_old_records(days)

    def health_check(self) -> bool:
        """Check tracker health"""
        return self.tracker.health_check()


# Global processing tracker instance
processing_tracker = ProcessingTracker()


# Convenience functions
def mark_chunks_complete(doc_name: str, bucket: str, count: int):
    """Mark chunks processing complete"""
    processing_tracker.mark_chunks_done(doc_name, bucket, count)


def mark_summary_complete(doc_name: str, bucket: str):
    """Mark summary processing complete"""
    processing_tracker.mark_summary_done(doc_name, bucket)


def mark_graphrag_complete(doc_name: str, bucket: str,
                          entities: int = 0, relationships: int = 0, communities: int = 0):
    """Mark GraphRAG processing complete"""
    processing_tracker.mark_graphrag_done(doc_name, bucket, entities, relationships, communities)


def mark_stp_complete(doc_name: str, bucket: str,
                     total: int = 0, stp: int = 0, non_stp: int = 0):
    """Mark STP processing complete"""
    processing_tracker.mark_stp_done(doc_name, bucket, total, stp, non_stp)


def get_document_status(doc_name: str, bucket: str) -> Dict[str, Any]:
    """Get document processing status"""
    return processing_tracker.get_document_status(doc_name, bucket)


def is_document_complete(doc_name: str, bucket: str) -> bool:
    """Check if document is fully processed"""
    return processing_tracker.is_document_processed(
        doc_name, bucket,
        require_chunks=True,
        require_summary=True,
        require_graphrag=True,
        require_stp=True
    )


def get_processing_stats() -> Dict[str, Any]:
    """Get overall processing statistics"""
    return processing_tracker.get_summary_stats()


logger.info("✅ Processing tracker utilities loaded")
