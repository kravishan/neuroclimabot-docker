"""
Storage Base Classes and Interfaces

This module defines abstract base classes and common interfaces for all storage backends
in the NeuroClima Document Processor. It provides a unified abstraction layer for:

- Vector storage (Milvus) for chunks and summaries
- Graph storage (LanceDB) for GraphRAG knowledge graphs
- Document tracking (SQLite) for processing state management
- Embedding generation (Ollama) for vector creation

All storage implementations must inherit from these base classes to ensure
consistent interfaces and enable dependency injection throughout the application.

"""

import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class BaseStorage(ABC):
    """
    Abstract base class for all storage backends.

    All storage implementations (Milvus, LanceDB, SQLite) inherit from this class
    and must implement the required abstract methods for connection management,
    health checking, and statistics reporting.

    Attributes:
        config (Dict[str, Any]): Storage-specific configuration parameters
        connected (bool): Connection status flag
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize storage backend with configuration.

        Args:
            config: Optional configuration dictionary for the storage backend
        """
        self.config = config or {}
        self.connected = False

    @abstractmethod
    def connect(self) -> None:
        """
        Establish connection to storage backend.

        This method should initialize the connection to the underlying storage system,
        perform authentication, and set self.connected = True on success.

        Raises:
            ConnectionError: If connection cannot be established
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """
        Close connection to storage backend.

        This method should gracefully close all connections, release resources,
        and set self.connected = False.
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """
        Check if storage backend is healthy and responsive.

        Returns:
            bool: True if storage is healthy and operational, False otherwise
        """
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics and metrics.

        Returns:
            Dict[str, Any]: Storage-specific statistics (e.g., record counts, sizes)
        """
        pass


class VectorStorageBackend(BaseStorage):
    """
    Abstract base class for vector storage operations.

    Defines the interface for vector databases like Milvus that store and retrieve
    document embeddings for similarity search. Implementations handle:
    - Collection/index creation and management
    - Vector insertion and deletion
    - Similarity search with filtering
    - Collection statistics and monitoring
    """

    @abstractmethod
    def create_collection(self, collection_name: str, schema: Dict[str, Any]) -> bool:
        """
        Create a collection with specified schema.

        Args:
            collection_name: Name of the collection to create
            schema: Collection schema defining fields and indexes

        Returns:
            bool: True if collection created successfully, False otherwise
        """
        pass

    @abstractmethod
    def insert_vectors(self, collection_name: str, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Insert vectors into collection.

        Args:
            collection_name: Target collection name
            data: List of records containing vectors and metadata

        Returns:
            Dict[str, Any]: Insert result with IDs and status
        """
        pass

    @abstractmethod
    def search_vectors(self, collection_name: str, query_vector: List[float],
                      limit: int = 10, filter_expr: str = None) -> List[Dict[str, Any]]:
        """
        Search for similar vectors using cosine similarity.

        Args:
            collection_name: Collection to search in
            query_vector: Query embedding vector
            limit: Maximum number of results to return
            filter_expr: Optional filter expression for metadata filtering

        Returns:
            List[Dict[str, Any]]: List of search results with similarity scores
        """
        pass

    @abstractmethod
    def delete_vectors(self, collection_name: str, filter_expr: str) -> bool:
        """
        Delete vectors matching filter expression.

        Args:
            collection_name: Collection to delete from
            filter_expr: Filter expression defining records to delete

        Returns:
            bool: True if deletion successful, False otherwise
        """
        pass

    @abstractmethod
    def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """
        Get statistics for specific collection.

        Args:
            collection_name: Collection to get stats for

        Returns:
            Dict[str, Any]: Statistics including record count, size, etc.
        """
        pass


class DocumentTrackerBackend(BaseStorage):
    """Abstract base class for document tracking operations"""

    @abstractmethod
    def mark_done(self, process_type: str, doc_name: str, bucket: str, **kwargs) -> None:
        """Mark a process as complete for a document"""
        pass

    @abstractmethod
    def get_status(self, doc_name: str, bucket: str) -> Dict[str, Any]:
        """Get processing status for a document"""
        pass

    @abstractmethod
    def get_all_documents(self, bucket_filter: str = None) -> List[Dict[str, Any]]:
        """Get all tracked documents"""
        pass

    @abstractmethod
    def is_processed(self, doc_name: str, bucket: str, process_type: str) -> bool:
        """Check if a specific process is complete for a document"""
        pass


class EmbeddingGenerator(ABC):
    """Abstract base class for embedding generation"""

    def __init__(self, model_name: str, model_url: str = None):
        self.model_name = model_name
        self.model_url = model_url

    @abstractmethod
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        pass

    @abstractmethod
    def generate_embeddings_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        pass

    def get_embedding_dimension(self) -> int:
        """Get the dimensionality of embeddings"""
        # Override in subclass with actual dimension
        return 768


class StorageManager:
    """
    Unified storage manager that coordinates multiple storage backends
    Manages chunks, summaries, STP data, and document tracking
    """

    def __init__(self):
        self.backends: Dict[str, BaseStorage] = {}
        self.primary_backend: Optional[str] = None
        logger.info("🔧 Storage Manager initialized")

    def register_backend(self, name: str, backend: BaseStorage, is_primary: bool = False):
        """Register a storage backend"""
        self.backends[name] = backend
        if is_primary or not self.primary_backend:
            self.primary_backend = name
        logger.info(f"✅ Registered storage backend: {name}")

    def get_backend(self, name: str = None) -> Optional[BaseStorage]:
        """Get a storage backend by name, or primary if name not specified"""
        if name:
            return self.backends.get(name)
        return self.backends.get(self.primary_backend) if self.primary_backend else None

    def connect_all(self) -> Dict[str, bool]:
        """Connect to all registered backends"""
        results = {}
        for name, backend in self.backends.items():
            try:
                backend.connect()
                results[name] = True
                logger.info(f"✅ Connected to {name}")
            except Exception as e:
                results[name] = False
                logger.error(f"❌ Failed to connect to {name}: {e}")
        return results

    def disconnect_all(self):
        """Disconnect from all backends"""
        for name, backend in self.backends.items():
            try:
                backend.disconnect()
                logger.info(f"✅ Disconnected from {name}")
            except Exception as e:
                logger.error(f"❌ Failed to disconnect from {name}: {e}")

    def health_check_all(self) -> Dict[str, bool]:
        """Check health of all backends"""
        health_status = {}
        for name, backend in self.backends.items():
            try:
                health_status[name] = backend.health_check()
            except Exception as e:
                logger.error(f"❌ Health check failed for {name}: {e}")
                health_status[name] = False
        return health_status

    def get_all_stats(self) -> Dict[str, Any]:
        """Get statistics from all backends"""
        all_stats = {
            "backends": {},
            "total_backends": len(self.backends),
            "connected_backends": 0,
            "primary_backend": self.primary_backend
        }

        for name, backend in self.backends.items():
            try:
                if backend.connected:
                    all_stats["backends"][name] = backend.get_stats()
                    all_stats["connected_backends"] += 1
                else:
                    all_stats["backends"][name] = {"status": "disconnected"}
            except Exception as e:
                all_stats["backends"][name] = {"error": str(e)}

        return all_stats


# Utility functions
def validate_embedding_dimension(embedding: List[float], expected_dim: int) -> bool:
    """Validate embedding dimension"""
    if not embedding or len(embedding) != expected_dim:
        logger.error(f"❌ Invalid embedding dimension: expected {expected_dim}, got {len(embedding) if embedding else 0}")
        return False
    return True


def format_timestamp(dt: datetime = None) -> str:
    """Format timestamp for storage"""
    if dt is None:
        dt = datetime.now()
    return dt.isoformat()


def sanitize_text_field(text: str, max_length: int) -> str:
    """Sanitize and truncate text field"""
    if not text:
        return ""
    text = str(text).strip()
    if len(text) > max_length:
        text = text[:max_length]
    return text


logger.info("✅ Storage base classes loaded")
