"""
Embedding service wrapper for query embedding generation.
Provides a consistent interface for generating embeddings across the application.
"""

from typing import List
from app.services.rag.embeddings import get_embeddings, OllamaEmbeddings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class EmbeddingService:
    """Service for generating query embeddings."""

    def __init__(self):
        """Initialize the embedding service with Ollama embeddings."""
        self.embeddings: OllamaEmbeddings = get_embeddings()
        logger.info("✅ EmbeddingService initialized")

    async def generate_query_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a query text.

        Args:
            text: The query text to embed

        Returns:
            List of float values representing the embedding (768 dimensions)
        """
        try:
            embedding = await self.embeddings.aembed_query(text)
            logger.debug(f"Generated query embedding: {len(embedding)} dimensions")
            return embedding
        except Exception as e:
            logger.error(f"Failed to generate query embedding: {e}")
            raise

    async def generate_document_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple documents.

        Args:
            texts: List of document texts to embed

        Returns:
            List of embeddings, each with 768 dimensions
        """
        try:
            embeddings = await self.embeddings.aembed_documents(texts)
            logger.debug(f"Generated {len(embeddings)} document embeddings")
            return embeddings
        except Exception as e:
            logger.error(f"Failed to generate document embeddings: {e}")
            raise

    def get_embedding_dimension(self) -> int:
        """Get the embedding dimension."""
        return self.embeddings.embedding_dimension

    async def health_check(self) -> bool:
        """Check if embedding service is healthy."""
        return await self.embeddings.health_check()


# Global embedding service instance
_embedding_service = None


def get_embedding_service() -> EmbeddingService:
    """Get the global embedding service instance."""
    global _embedding_service

    if _embedding_service is None:
        _embedding_service = EmbeddingService()

    return _embedding_service
