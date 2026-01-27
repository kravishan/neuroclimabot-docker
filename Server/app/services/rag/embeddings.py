"""
OpenAI-compatible embedding service for generating text embeddings.
"""

import asyncio
import aiohttp
import json
from typing import List, Dict, Any
from langchain.embeddings.base import Embeddings

from app.config.database import get_milvus_config
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
milvus_config = get_milvus_config()
settings = get_settings()


class OpenAICompatibleEmbeddings(Embeddings):
    """OpenAI-compatible embedding service using a hosted API endpoint."""

    def __init__(self):
        self.api_url = settings.EMBEDDING_API_URL
        self.api_token = settings.EMBEDDING_API_TOKEN
        self.model_name = settings.EMBEDDING_MODEL
        self.embedding_dimension = settings.EMBEDDING_DIMENSION
        self.timeout = settings.EMBEDDING_TIMEOUT

        # Performance tracking
        self.stats = {
            "total_requests": 0,
            "total_texts_embedded": 0,
            "avg_request_time": 0.0,
            "error_count": 0
        }

        logger.info(f"OpenAI-Compatible Embedding Service initialized")
        logger.info(f"API URL: {self.api_url}")
        logger.info(f"Model: {self.model_name}")
        logger.info(f"Expected dimension: {self.embedding_dimension}")

    async def _get_embeddings_from_api(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings from OpenAI-compatible API endpoint."""
        import time
        start_time = time.perf_counter()

        try:
            headers = {
                "Content-Type": "application/json",
            }

            # Add authorization header if token is provided
            if self.api_token:
                headers["Authorization"] = f"Bearer {self.api_token}"

            # OpenAI-compatible embedding API format
            payload = {
                "model": self.model_name,
                "input": [text.replace('\n', ' ').strip() for text in texts]
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Embedding API error {response.status}: {error_text}")

                    result = await response.json()

                    # Parse OpenAI-compatible response format
                    # Response format: {"data": [{"embedding": [...], "index": 0}, ...], "model": "...", "usage": {...}}
                    data = result.get("data", [])

                    if not data:
                        raise Exception("No embedding data returned from API")

                    # Sort by index to ensure correct order
                    sorted_data = sorted(data, key=lambda x: x.get("index", 0))
                    embeddings = []

                    for item in sorted_data:
                        embedding = item.get("embedding", [])

                        if not embedding:
                            raise Exception("Empty embedding in response")

                        # Verify and adjust dimension if needed
                        if len(embedding) != self.embedding_dimension:
                            logger.warning(f"Embedding dimension mismatch: got {len(embedding)}, expected {self.embedding_dimension}")
                            if len(embedding) > self.embedding_dimension:
                                embedding = embedding[:self.embedding_dimension]
                            else:
                                embedding.extend([0.0] * (self.embedding_dimension - len(embedding)))

                        embeddings.append(embedding)

            # Update stats
            request_time = time.perf_counter() - start_time
            self._update_stats(len(texts), request_time)

            logger.debug(f"Generated {len(embeddings)} embeddings in {request_time:.3f}s")
            return embeddings

        except asyncio.TimeoutError:
            self.stats["error_count"] += 1
            logger.error(f"Embedding API request timed out after {self.timeout}s")
            raise Exception("Embedding request timed out")
        except aiohttp.ClientError as e:
            self.stats["error_count"] += 1
            logger.error(f"Embedding API connection error: {e}")
            raise Exception(f"Failed to connect to Embedding API: {str(e)}")
        except Exception as e:
            self.stats["error_count"] += 1
            logger.error(f"Embedding API error: {e}")
            raise Exception(f"Embedding generation failed: {str(e)}")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents."""
        if not texts:
            return []

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self._get_embeddings_from_api(texts))

    def embed_query(self, text: str) -> List[float]:
        """Embed a single query."""
        embeddings = self.embed_documents([text])
        return embeddings[0] if embeddings else [0.0] * self.embedding_dimension

    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        """Async version of embed_documents."""
        if not texts:
            return []
        return await self._get_embeddings_from_api(texts)

    async def aembed_query(self, text: str) -> List[float]:
        """Async version of embed_query."""
        embeddings = await self.aembed_documents([text])
        return embeddings[0] if embeddings else [0.0] * self.embedding_dimension

    def _update_stats(self, text_count: int, request_time: float):
        """Update performance statistics."""
        self.stats["total_requests"] += 1
        self.stats["total_texts_embedded"] += text_count

        # Update running average
        total_requests = self.stats["total_requests"]
        current_avg = self.stats["avg_request_time"]
        new_avg = ((current_avg * (total_requests - 1)) + request_time) / total_requests
        self.stats["avg_request_time"] = new_avg

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the embedding model."""
        return {
            "model_name": self.model_name,
            "dimension": self.embedding_dimension,
            "source": "openai_compatible_api",
            "api_url": self.api_url,
            "metric_type": milvus_config.METRIC_TYPE,
            "nlist": milvus_config.NLIST,
            "stats": self.stats.copy()
        }

    async def health_check(self) -> bool:
        """Check if embedding service is healthy."""
        try:
            test_embedding = await self.aembed_query("health check")

            if len(test_embedding) == self.embedding_dimension:
                logger.debug("Embedding service health check passed")
                return True
            else:
                logger.error(f"Health check failed: wrong dimension {len(test_embedding)}")
                return False

        except Exception as e:
            logger.error(f"Embedding health check failed: {e}")
            return False


# Global embeddings instance
_embeddings_instance = None


def get_embeddings() -> Embeddings:
    """Get the embeddings instance."""
    global _embeddings_instance

    if _embeddings_instance is None:
        _embeddings_instance = OpenAICompatibleEmbeddings()

    return _embeddings_instance


def get_embedding_model_info() -> Dict[str, Any]:
    """Get embedding model information."""
    embeddings = get_embeddings()
    return embeddings.get_model_info()


async def test_embeddings():
    """Test function to verify embeddings are working."""
    logger.info("Testing Embeddings...")

    try:
        embeddings = get_embeddings()

        # Test single query
        logger.info("Testing single query embedding...")
        query_embedding = await embeddings.aembed_query("climate change and renewable energy")
        logger.info(f"Query embedding dimension: {len(query_embedding)}")

        # Test multiple documents
        logger.info("Testing multiple document embeddings...")
        docs = [
            "Solar energy is a renewable energy source",
            "Wind power generates clean electricity",
            "Climate change affects global temperatures"
        ]
        doc_embeddings = await embeddings.aembed_documents(docs)
        logger.info(f"Document embeddings: {len(doc_embeddings)} x {len(doc_embeddings[0]) if doc_embeddings else 0}D")

        # Test similarity
        if len(doc_embeddings) >= 2:
            import numpy as np
            emb1, emb2 = doc_embeddings[0], doc_embeddings[1]
            similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
            logger.info(f"Similarity between docs 1&2: {similarity:.3f}")

        # Show stats
        info = embeddings.get_model_info()
        logger.info(f"Stats: {info['stats']}")

        return True

    except Exception as e:
        logger.error(f"Embedding test failed: {e}")
        return False
