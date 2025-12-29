"""
Ollama-based embedding service using the hosted nomic-embed-text model.
"""

import asyncio
import aiohttp
import json
import logging
from typing import List, Dict, Any
from langchain.embeddings.base import Embeddings

from app.config.database import get_milvus_config
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
milvus_config = get_milvus_config()
settings = get_settings()


class OllamaEmbeddings(Embeddings):
    """Ollama-based embedding service using hosted nomic-embed-text model."""
    
    def __init__(self):
        self.ollama_base_url = settings.OLLAMA_BASE_URL
        self.model_name = "nomic-embed-text"  # The model name in Ollama
        self.embedding_dimension = milvus_config.EMBEDDING_DIMENSION  # 768
        self.timeout = 30  # Timeout for embedding requests
        
        # Performance tracking
        self.stats = {
            "total_requests": 0,
            "total_texts_embedded": 0,
            "avg_request_time": 0.0,
            "error_count": 0
        }
        
        logger.info(f"✅ Ollama Embedding Service initialized")
        logger.info(f"🌐 Ollama URL: {self.ollama_base_url}")
        logger.info(f"🤖 Model: {self.model_name}")
        logger.info(f"📏 Expected dimension: {self.embedding_dimension}")
    
    async def _get_embeddings_from_ollama(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings from Ollama server."""
        import time
        start_time = time.perf_counter()
        
        try:
            headers = {
                "Content-Type": "application/json",
            }
            
            embeddings = []
            
            # Process texts individually (Ollama embedding API typically handles one at a time)
            for text in texts:
                payload = {
                    "model": self.model_name,
                    "prompt": text.replace('\n', ' ').strip()  # Clean the text
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.ollama_base_url}/api/embeddings",
                        json=payload,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=self.timeout)
                    ) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            raise Exception(f"Ollama API error {response.status}: {error_text}")
                        
                        result = await response.json()
                        embedding = result.get("embedding", [])
                        
                        if not embedding:
                            raise Exception("No embedding returned from Ollama")
                        
                        # Verify dimension
                        if len(embedding) != self.embedding_dimension:
                            logger.warning(f"Embedding dimension mismatch: got {len(embedding)}, expected {self.embedding_dimension}")
                            # Pad or truncate to match expected dimension
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
            logger.error(f"Ollama embedding request timed out after {self.timeout}s")
            raise Exception("Embedding request timed out")
        except aiohttp.ClientError as e:
            self.stats["error_count"] += 1
            logger.error(f"Ollama connection error: {e}")
            raise Exception(f"Failed to connect to Ollama: {str(e)}")
        except Exception as e:
            self.stats["error_count"] += 1
            logger.error(f"Ollama embedding error: {e}")
            raise Exception(f"Embedding generation failed: {str(e)}")
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents using Ollama."""
        if not texts:
            return []
        
        try:
            # Run async method in sync context
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self._get_embeddings_from_ollama(texts))
    
    def embed_query(self, text: str) -> List[float]:
        """Embed a single query using Ollama."""
        embeddings = self.embed_documents([text])
        return embeddings[0] if embeddings else [0.0] * self.embedding_dimension
    
    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        """Async version of embed_documents."""
        if not texts:
            return []
        return await self._get_embeddings_from_ollama(texts)
    
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
            "source": "ollama_server",
            "base_url": self.ollama_base_url,
            "metric_type": milvus_config.METRIC_TYPE,
            "nlist": milvus_config.NLIST,
            "stats": self.stats.copy()
        }
    
    async def health_check(self) -> bool:
        """Check if Ollama embedding service is healthy."""
        try:
            # Test with a simple embedding
            test_embedding = await self.aembed_query("health check")
            
            # Verify we got a valid embedding
            if len(test_embedding) == self.embedding_dimension:
                logger.debug("✅ Ollama embedding service health check passed")
                return True
            else:
                logger.error(f"❌ Health check failed: wrong dimension {len(test_embedding)}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ollama embedding health check failed: {e}")
            return False


# Global embeddings instance
_ollama_embeddings = None


def get_embeddings() -> Embeddings:
    """Get the Ollama embeddings instance."""
    global _ollama_embeddings
    
    if _ollama_embeddings is None:
        _ollama_embeddings = OllamaEmbeddings()
    
    return _ollama_embeddings


def get_embedding_model_info() -> Dict[str, Any]:
    """Get embedding model information."""
    embeddings = get_embeddings()
    return embeddings.get_model_info()


async def test_ollama_embeddings():
    """Test function to verify Ollama embeddings are working."""
    logger.info("🧪 Testing Ollama Embeddings...")

    try:
        embeddings = get_embeddings()

        # Test single query
        logger.info("📝 Testing single query embedding...")
        query_embedding = await embeddings.aembed_query("climate change and renewable energy")
        logger.info(f"✅ Query embedding dimension: {len(query_embedding)}")

        # Test multiple documents
        logger.info("📄 Testing multiple document embeddings...")
        docs = [
            "Solar energy is a renewable energy source",
            "Wind power generates clean electricity",
            "Climate change affects global temperatures"
        ]
        doc_embeddings = await embeddings.aembed_documents(docs)
        logger.info(f"✅ Document embeddings: {len(doc_embeddings)} x {len(doc_embeddings[0]) if doc_embeddings else 0}D")

        # Test similarity
        if len(doc_embeddings) >= 2:
            import numpy as np
            emb1, emb2 = doc_embeddings[0], doc_embeddings[1]
            similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
            logger.info(f"🔗 Similarity between docs 1&2: {similarity:.3f}")

        # Show stats
        info = embeddings.get_model_info()
        logger.info(f"📊 Stats: {info['stats']}")

        return True

    except Exception as e:
        logger.error(f"❌ Ollama embedding test failed: {e}")
        return False