"""
Query Embedding Service for Retrieval Operations
Uses external Ollama API for fast query embeddings with GPU acceleration
"""

import logging
from typing import List
import aiohttp
import asyncio

logger = logging.getLogger(__name__)


class QueryEmbeddingService:
    """
    Service for generating query embeddings using external Ollama API.
    Used for retrieval/search operations, not document processing.
    """

    def __init__(self, api_url: str, model: str, embedding_dim: int, timeout: int = 30):
        """
        Initialize query embedding service.

        Args:
            api_url: Ollama API URL (e.g., 'http://86.50.23.167:11434')
            model: Embedding model name (e.g., 'qwen3-embedding:0.6b')
            embedding_dim: Expected embedding dimension
            timeout: Request timeout in seconds
        """
        self.api_url = api_url.rstrip('/')
        self.embedding_url = f"{self.api_url}/api/embeddings"
        self.model = model
        self.embedding_dim = embedding_dim
        self.timeout = timeout
        self._session = None

        logger.info(f"🔧 QueryEmbeddingService initialized")
        logger.info(f"   API: {self.embedding_url}")
        logger.info(f"   Model: {self.model} ({self.embedding_dim}D)")

    async def _get_session(self):
        """Get or create aiohttp session"""
        if self._session is None:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )
        return self._session

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a query text using external Ollama API.

        Args:
            text: Query text to encode

        Returns:
            List of floats representing the embedding vector
        """
        if not text or not text.strip():
            logger.warning("Empty text provided, returning zero embedding")
            return [0.0] * self.embedding_dim

        cleaned_text = text.strip()

        payload = {
            "model": self.model,
            "prompt": cleaned_text
        }

        try:
            session = await self._get_session()

            async with session.post(self.embedding_url, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"❌ Embedding API error {response.status}: {error_text[:200]}")
                    return [0.0] * self.embedding_dim

                result = await response.json()
                embedding = result.get("embedding", [])

                if not embedding:
                    logger.error("❌ Empty embedding returned from API")
                    return [0.0] * self.embedding_dim

                if len(embedding) != self.embedding_dim:
                    logger.warning(
                        f"⚠️  Embedding dimension mismatch: got {len(embedding)}, expected {self.embedding_dim}"
                    )

                return embedding

        except asyncio.TimeoutError:
            logger.error(f"❌ Embedding generation timeout after {self.timeout}s")
            return [0.0] * self.embedding_dim
        except Exception as e:
            logger.error(f"❌ Embedding generation failed: {e}")
            return [0.0] * self.embedding_dim

    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to encode

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        # Generate embeddings concurrently
        tasks = [self.generate_embedding(text) for text in texts]
        embeddings = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions
        result = []
        for i, embedding in enumerate(embeddings):
            if isinstance(embedding, Exception):
                logger.error(f"❌ Failed to generate embedding for text {i}: {embedding}")
                result.append([0.0] * self.embedding_dim)
            else:
                result.append(embedding)

        return result

    async def cleanup(self):
        """Close aiohttp session"""
        if self._session:
            await self._session.close()
            self._session = None
            logger.info("✅ QueryEmbeddingService session closed")

    def get_info(self):
        """Get service information"""
        return {
            "service": "QueryEmbeddingService",
            "api_url": self.api_url,
            "embedding_url": self.embedding_url,
            "model": self.model,
            "embedding_dim": self.embedding_dim,
            "timeout": self.timeout,
        }


# Global query embedding service instance
_query_embedding_service = None


def get_query_embedding_service() -> QueryEmbeddingService:
    """Get the global query embedding service instance"""
    global _query_embedding_service
    if _query_embedding_service is None:
        raise RuntimeError(
            "Query embedding service not initialized. "
            "Call initialize_query_embedding_service() first."
        )
    return _query_embedding_service


def initialize_query_embedding_service(
    api_url: str,
    model: str,
    embedding_dim: int,
    timeout: int = 30
):
    """
    Initialize the global query embedding service.

    Args:
        api_url: Ollama API URL
        model: Embedding model name
        embedding_dim: Embedding dimension
        timeout: Request timeout in seconds
    """
    global _query_embedding_service

    if _query_embedding_service is not None:
        logger.warning("Query embedding service already initialized, recreating...")

    _query_embedding_service = QueryEmbeddingService(
        api_url=api_url,
        model=model,
        embedding_dim=embedding_dim,
        timeout=timeout
    )

    logger.info("✅ Query embedding service initialized successfully")
    return _query_embedding_service
