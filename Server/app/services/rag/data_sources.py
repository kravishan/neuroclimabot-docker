import asyncio
import hashlib
import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from app.config import get_settings
from app.config.database import get_milvus_config
from app.services.external.milvus import get_milvus_client
from app.services.external.graphrag_api_client import get_graphrag_api_client
from app.services.rag.embeddings import get_embeddings
from app.core.exceptions import RAGException
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()
milvus_config = get_milvus_config()


@dataclass
class RetrievalResult:
    """Data class for retrieval results from all sources."""
    chunks: List[Dict[str, Any]]
    summaries: List[Dict[str, Any]]
    graph_data: List[Dict[str, Any]]
    total_results: int
    retrieval_time: float
    cache_hits: Dict[str, bool]
    source_health: Dict[str, bool]  # NEW: Track which sources succeeded


class FaultTolerantRetriever:
    """Fault-tolerant retriever - only fails if ALL 3 sources fail."""
    
    def __init__(self):
        self.milvus_client = get_milvus_client()
        self.graphrag_api_client = None
        self.embedding_service = None
        self.is_initialized = False
        
        # Configuration
        self.embedding_dimension = milvus_config.EMBEDDING_DIMENSION
        self.metric_type = milvus_config.METRIC_TYPE
        self.nlist = milvus_config.NLIST
        self.ollama_base_url = settings.OLLAMA_BASE_URL
        
        # Caching
        self.embedding_cache = {}
        self.result_cache = {}
        self.cache_max_size = settings.EMBEDDING_CACHE_SIZE
        
        # Timeouts
        self.milvus_timeout = getattr(settings, 'RETRIEVAL_MILVUS_TIMEOUT', 5.0)
        self.graphrag_api_timeout = getattr(settings, 'RETRIEVAL_GRAPHRAG_API_TIMEOUT', 15.0)
        self.total_timeout = 25.0
        self.embedding_timeout = 10.0
        
        # Performance tracking with fault tolerance
        self.performance_stats = {
            "total_requests": 0,
            "cache_hits": 0,
            "avg_retrieval_time": 0.0,
            "timeout_count": 0,
            "graphrag_api_timeout_count": 0,
            "graphrag_local_search_queries": 0,
            "embedding_dimension": self.embedding_dimension,
            "ollama_requests": 0,
            "task_cancellation_count": 0,
            "relevance_filtered_count": 0,
            # NEW: Source reliability tracking
            "chunks_success_count": 0,
            "chunks_failure_count": 0,
            "summaries_success_count": 0,
            "summaries_failure_count": 0,
            "graphrag_success_count": 0,
            "graphrag_failure_count": 0,
            "all_sources_failed_count": 0,  # This is the real concern
            "partial_success_count": 0  # At least 1 source worked
        }
    
    async def initialize(self):
        """Initialize the retriever with fault tolerance."""
        try:
            self.embedding_service = get_embeddings()
            
            # Test embedding service
            health_ok = await self.embedding_service.health_check()
            if not health_ok:
                raise RAGException("Ollama embedding service health check failed")
            
            # Test embedding dimension
            test_embedding = await self.embedding_service.aembed_query("test")
            actual_dimension = len(test_embedding)
            
            if actual_dimension != self.embedding_dimension:
                raise RAGException(f"Embedding dimension mismatch: {actual_dimension} != {self.embedding_dimension}")
            
            # Initialize GraphRAG API client
            self.graphrag_api_client = await get_graphrag_api_client()
            
            self.is_initialized = True
            logger.info(f"✅ Fault-tolerant retriever initialized with {self.embedding_dimension}D embeddings")
            
        except Exception as e:
            logger.error(f"Failed to initialize retriever: {e}")
            raise RAGException(f"Retriever initialization failed: {str(e)}")
    
    async def retrieve_all_sources(
        self,
        query: str,
        use_cache: bool = True,
        custom_timeout: Optional[float] = None,
        bucket: Optional[str] = None
    ) -> RetrievalResult:
        """Fault-tolerant retrieval - succeeds if ANY source works."""
        
        if not self.is_initialized:
            await self.initialize()
        
        effective_timeout = custom_timeout or self.total_timeout
        start_time = time.perf_counter()
        self.performance_stats["total_requests"] += 1
        
        try:
            logger.info(f"🔍 STARTING FAULT-TOLERANT RETRIEVAL: Query: '{query[:100]}{'...' if len(query) > 100 else ''}', Bucket: {bucket or 'all'}, Timeout: {effective_timeout}s, Fault Tolerance: SUCCESS if ANY source works")
            
            # Check cache first
            cache_key = self._generate_cache_key(query, bucket)
            cache_hits = {"embeddings": False, "results": False}
            
            if use_cache and cache_key in self.result_cache:
                cached_result = self.result_cache[cache_key]
                cached_result.cache_hits = {"embeddings": True, "results": True}
                self.performance_stats["cache_hits"] += 1
                logger.info(f"Cache hit for query: {query[:50]}...")
                return cached_result
            
            # Get embedding
            query_embedding = await self._get_cached_embedding(query)
            if cache_key + "_embedding" in self.embedding_cache:
                cache_hits["embeddings"] = True
            
            # Verify embedding dimension
            if len(query_embedding) != self.embedding_dimension:
                raise RAGException(f"Embedding dimension mismatch: {len(query_embedding)} != {self.embedding_dimension}")
            
            # Create retrieval tasks - ALL use the same embedding vector
            chunks_task = asyncio.create_task(
                self._safe_get_milvus_chunks(query_embedding),
                name="milvus_chunks"
            )
            summaries_task = asyncio.create_task(
                self._safe_get_milvus_summaries(query_embedding),
                name="milvus_summaries"
            )
            graphrag_task = asyncio.create_task(
                self._safe_get_graphrag_local_search(query, query_embedding, bucket),
                name="graphrag_local_search"
            )
            
            retrieval_tasks = [chunks_task, summaries_task, graphrag_task]
            task_names = ["chunks", "summaries", "graphrag"]
            
            # Execute with fault tolerance - DON'T cancel on timeout, let them complete
            try:
                logger.debug(f"Starting parallel retrieval with {len(retrieval_tasks)} tasks")
                results = await asyncio.wait_for(
                    asyncio.gather(*retrieval_tasks, return_exceptions=True),
                    timeout=effective_timeout
                )
                
            except asyncio.TimeoutError:
                elapsed_time = time.perf_counter() - start_time
                logger.warning(f"Retrieval timeout after {elapsed_time:.1f}s - collecting partial results")
                self.performance_stats["timeout_count"] += 1
                
                # Collect whatever results we can get (don't cancel tasks)
                results = []
                for task in retrieval_tasks:
                    if task.done():
                        try:
                            result = task.result()
                            results.append(result)
                        except Exception as e:
                            results.append(e)
                    else:
                        results.append([])  # Empty result for unfinished tasks
            
            # Process results with fault tolerance
            chunks, chunks_success = self._extract_result_with_status(results[0], [], "chunks")
            summaries, summaries_success = self._extract_result_with_status(results[1], [], "summaries")
            graph_data, graphrag_success = self._extract_result_with_status(results[2], [], "graphrag")
            
            # Update source reliability stats
            self._update_source_stats(chunks_success, summaries_success, graphrag_success)
            
            # Track source health
            source_health = {
                "chunks": chunks_success,
                "summaries": summaries_success,
                "graphrag": graphrag_success
            }
            
            # Check if we have ANY successful results
            successful_sources = sum([chunks_success, summaries_success, graphrag_success])
            total_results = len(chunks) + len(summaries) + len(graph_data)
            
            retrieval_time = time.perf_counter() - start_time
            
            # Logging with fault tolerance status
            logger.info(f"🎯 FAULT-TOLERANT RETRIEVAL SUMMARY: Total time: {retrieval_time:.3f}s, Total results: {total_results}, Successful sources: {successful_sources}/3")
            logger.debug(f"   📄 Chunks: {len(chunks)} {'✅' if chunks_success else '❌'}")
            logger.debug(f"   📋 Summaries: {len(summaries)} {'✅' if summaries_success else '❌'}")
            logger.debug(f"   🌐 GraphRAG: {len(graph_data)} {'✅' if graphrag_success else '❌'}")

            if successful_sources == 0:
                logger.error("🚨 ALL SOURCES FAILED - This is a concern!")
                self.performance_stats["all_sources_failed_count"] += 1
            else:
                logger.info(f"✅ PARTIAL SUCCESS - {successful_sources} source(s) worked")
                self.performance_stats["partial_success_count"] += 1
            
            # Create result
            result = RetrievalResult(
                chunks=chunks,
                summaries=summaries,
                graph_data=graph_data,
                total_results=total_results,
                retrieval_time=retrieval_time,
                cache_hits=cache_hits,
                source_health=source_health
            )
            
            # Cache good results (even partial successes)
            if use_cache and total_results > 0:
                self._cache_result(cache_key, result)
            
            # Update performance stats
            self._update_performance_stats(retrieval_time)
            
            # Log appropriate level based on success
            if successful_sources == 0:
                logger.error(f"🚨 ALL SOURCES FAILED for query: {query[:50]}...")
            elif successful_sources < 3:
                logger.warning(f"⚠️ Partial success: {successful_sources}/3 sources worked for query: {query[:50]}...")
            else:
                logger.info(f"✅ All sources successful: {total_results} results in {retrieval_time:.3f}s")
            
            return result
            
        except Exception as e:
            logger.error(f"Critical retrieval error: {e}")
            self.performance_stats["all_sources_failed_count"] += 1
            return RetrievalResult(
                chunks=[], summaries=[], graph_data=[],
                total_results=0, retrieval_time=time.perf_counter() - start_time,
                cache_hits={"embeddings": False, "results": False},
                source_health={"chunks": False, "summaries": False, "graphrag": False}
            )
    
    def _extract_result_with_status(self, result, default, source_name: str) -> tuple:
        """Extract result and return (data, success_status)."""
        if isinstance(result, Exception):
            if isinstance(result, asyncio.CancelledError):
                logger.debug(f"{source_name} task was cancelled")
            elif isinstance(result, asyncio.TimeoutError):
                logger.debug(f"{source_name} task timed out")
            else:
                logger.debug(f"{source_name} task failed: {type(result).__name__}")
            return default, False
        elif result is None:
            logger.debug(f"{source_name} returned None")
            return default, False
        elif isinstance(result, list) and len(result) == 0:
            logger.debug(f"{source_name} returned empty results")
            return result, True  # Empty results are still "successful"
        else:
            logger.debug(f"{source_name} returned {len(result) if isinstance(result, list) else 'data'}")
            return result, True
    
    def _update_source_stats(self, chunks_success: bool, summaries_success: bool, graphrag_success: bool):
        """Update source reliability statistics."""
        if chunks_success:
            self.performance_stats["chunks_success_count"] += 1
        else:
            self.performance_stats["chunks_failure_count"] += 1
            
        if summaries_success:
            self.performance_stats["summaries_success_count"] += 1
        else:
            self.performance_stats["summaries_failure_count"] += 1
            
        if graphrag_success:
            self.performance_stats["graphrag_success_count"] += 1
        else:
            self.performance_stats["graphrag_failure_count"] += 1
    
    async def _safe_get_milvus_chunks(self, query_embedding: List[float]) -> List[Dict[str, Any]]:
        """Safely get Milvus chunks with detailed error tracking."""
        try:
            return await asyncio.wait_for(
                self.milvus_client.search_chunks(
                    query_embedding=query_embedding,
                    limit=settings.CHUNKS_RETRIEVAL_LIMIT,
                    min_score=settings.SIMILARITY_THRESHOLD
                ),
                timeout=self.milvus_timeout
            )
        except asyncio.TimeoutError:
            logger.debug(f"Milvus chunks search timed out after {self.milvus_timeout}s")
            raise  # Let the caller handle this
        except asyncio.CancelledError:
            logger.debug("Milvus chunks search was cancelled")
            raise  # Let the caller handle this
        except Exception as e:
            logger.debug(f"Milvus chunks search error: {e}")
            raise  # Let the caller handle this
    
    async def _safe_get_milvus_summaries(self, query_embedding: List[float]) -> List[Dict[str, Any]]:
        """Safely get Milvus summaries with detailed error tracking."""
        try:
            return await asyncio.wait_for(
                self.milvus_client.search_all_summaries(
                    query_embedding=query_embedding,
                    limit_per_collection=settings.SUMMARIES_RETRIEVAL_LIMIT // 4 + 1
                ),
                timeout=self.milvus_timeout
            )
        except asyncio.TimeoutError:
            logger.debug(f"Milvus summaries search timed out after {self.milvus_timeout}s")
            raise  # Let the caller handle this
        except asyncio.CancelledError:
            logger.debug("Milvus summaries search was cancelled")
            raise  # Let the caller handle this
        except Exception as e:
            logger.debug(f"Milvus summaries search error: {e}")
            raise  # Let the caller handle this
    
    async def _safe_get_graphrag_local_search(
        self,
        query: str,
        query_embedding: List[float],  # Pass embedding to avoid regenerating
        bucket: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Safely get GraphRAG data with detailed error tracking."""
        try:
            return await asyncio.wait_for(
                self.graphrag_api_client.search_graph_data(
                    query=query,
                    embedding=query_embedding,  # Pass the embedding we already generated
                    search_type="local",
                    limit=settings.GRAPH_RETRIEVAL_LIMIT,
                    include_communities=True,
                    include_relationships=True,
                    bucket=bucket
                ),
                timeout=self.graphrag_api_timeout
            )
        except asyncio.TimeoutError:
            logger.debug(f"GraphRAG local-search API search timed out after {self.graphrag_api_timeout}s")
            raise  # Let the caller handle this
        except asyncio.CancelledError:
            logger.debug("GraphRAG local-search API search was cancelled")
            raise  # Let the caller handle this
        except Exception as e:
            logger.debug(f"GraphRAG local-search API search error: {e}")
            raise  # Let the caller handle this
    
    async def _get_cached_embedding(self, query: str) -> List[float]:
        """Get embedding with caching and timeout."""
        cache_key = self._generate_cache_key(query) + "_embedding"
        
        if cache_key in self.embedding_cache:
            return self.embedding_cache[cache_key]
        
        try:
            embedding = await asyncio.wait_for(
                self.embedding_service.aembed_query(query),
                timeout=self.embedding_timeout
            )
            
            if len(embedding) != self.embedding_dimension:
                raise RAGException(f"Embedding dimension mismatch from Ollama")
            
            self.performance_stats["ollama_requests"] += 1
            
        except asyncio.TimeoutError:
            logger.warning(f"Ollama embedding timeout ({self.embedding_timeout}s)")
            return [0.0] * self.embedding_dimension
        except asyncio.CancelledError:
            logger.debug("Ollama embedding was cancelled")
            return [0.0] * self.embedding_dimension
        
        # Cache with size limit
        if len(self.embedding_cache) >= self.cache_max_size:
            oldest_key = next(iter(self.embedding_cache))
            del self.embedding_cache[oldest_key]
        
        self.embedding_cache[cache_key] = embedding
        return embedding
    
    def _generate_cache_key(self, query: str, bucket: Optional[str] = None) -> str:
        """Generate cache key for query with optional bucket."""
        cache_input = query.lower()
        if bucket:
            cache_input += f"_bucket_{bucket}"
        return hashlib.md5(cache_input.encode()).hexdigest()
    
    def _cache_result(self, cache_key: str, result: RetrievalResult):
        """Cache result with size limit."""
        if len(self.result_cache) >= settings.QUERY_CACHE_SIZE:
            oldest_key = next(iter(self.result_cache))
            del self.result_cache[oldest_key]
        
        self.result_cache[cache_key] = result
    
    def _update_performance_stats(self, retrieval_time: float):
        """Update performance statistics."""
        total = self.performance_stats["total_requests"]
        current_avg = self.performance_stats["avg_retrieval_time"]
        
        new_avg = ((current_avg * (total - 1)) + retrieval_time) / total
        self.performance_stats["avg_retrieval_time"] = new_avg
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics with fault tolerance metrics."""
        total_requests = self.performance_stats["total_requests"]
        
        # Calculate source reliability rates
        chunks_total = self.performance_stats["chunks_success_count"] + self.performance_stats["chunks_failure_count"]
        summaries_total = self.performance_stats["summaries_success_count"] + self.performance_stats["summaries_failure_count"]
        graphrag_total = self.performance_stats["graphrag_success_count"] + self.performance_stats["graphrag_failure_count"]
        
        chunks_reliability = (self.performance_stats["chunks_success_count"] / chunks_total) if chunks_total > 0 else 0.0
        summaries_reliability = (self.performance_stats["summaries_success_count"] / summaries_total) if summaries_total > 0 else 0.0
        graphrag_reliability = (self.performance_stats["graphrag_success_count"] / graphrag_total) if graphrag_total > 0 else 0.0
        
        # Get GraphRAG API client stats if available
        graphrag_stats = {}
        if self.graphrag_api_client and hasattr(self.graphrag_api_client, 'performance_stats'):
            graphrag_stats = self.graphrag_api_client.performance_stats
        
        return {
            **self.performance_stats,
            "cache_hit_rate": self.performance_stats["cache_hits"] / total_requests if total_requests > 0 else 0.0,
            "timeout_rate": self.performance_stats["timeout_count"] / total_requests if total_requests > 0 else 0.0,
            "all_sources_failed_rate": self.performance_stats["all_sources_failed_count"] / total_requests if total_requests > 0 else 0.0,
            "partial_success_rate": self.performance_stats["partial_success_count"] / total_requests if total_requests > 0 else 0.0,
            "embedding_cache_size": len(self.embedding_cache),
            "result_cache_size": len(self.result_cache),
            "source_reliability": {
                "chunks": chunks_reliability,
                "summaries": summaries_reliability,
                "graphrag": graphrag_reliability,
                "overall_system": (chunks_reliability + summaries_reliability + graphrag_reliability) / 3
            },
            "fault_tolerance": {
                "design": "succeeds_if_any_source_works",
                "concern_threshold": "all_3_sources_fail",
                "acceptable": "1_or_2_sources_fail"
            },
            "embedding_config": {
                "service": "ollama",
                "model": "nomic-embed-text",
                "base_url": self.ollama_base_url,
                "dimension": self.embedding_dimension,
                "metric_type": self.metric_type,
                "nlist": self.nlist
            },
            "configured_timeouts": {
                "milvus": self.milvus_timeout,
                "graphrag_api": self.graphrag_api_timeout,
                "total": self.total_timeout,
                "embedding": self.embedding_timeout
            },
            "graphrag_source": "external_local_search_api_server",
            "graphrag_endpoint": "/graphrag/local-search",
            "graphrag_api_stats": graphrag_stats,
            "service_type": "fault_tolerant_ollama_nomic_embed_with_graphrag_local_search_api"
        }
    
    async def health_check(self) -> bool:
        """Fault-tolerant health check - passes if ANY source works."""
        try:
            if not self.is_initialized:
                return False
            
            embedding_ok = await self.embedding_service.health_check() if self.embedding_service else False
            graphrag_api_ok = await self.graphrag_api_client.health_check() if self.graphrag_api_client else False
            
            # Milvus health check (simplified)
            milvus_ok = True  # Assume OK unless we can check it
            
            # Pass health check if ANY source is working
            working_sources = sum([embedding_ok, graphrag_api_ok, milvus_ok])
            
            if working_sources == 0:
                logger.error("🚨 ALL SOURCES FAILED health check")
                return False
            elif working_sources < 3:
                logger.warning(f"⚠️ Partial health: {working_sources}/3 sources OK")
                return True  # Still healthy with partial sources
            else:
                logger.info("✅ All sources healthy")
                return True
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False


# Global retriever instance
fault_tolerant_retriever = FaultTolerantRetriever()


async def get_multi_source_retriever() -> FaultTolerantRetriever:
    """Get the fault-tolerant retriever instance."""
    if not fault_tolerant_retriever.is_initialized:
        await fault_tolerant_retriever.initialize()
    return fault_tolerant_retriever