"""
Updated Milvus client for new database structure with parallel collection searches.
"""

import asyncio
from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor

from pymilvus import (
    Collection,
    connections,
    utility,
)

from app.config.database import get_milvus_config
from app.config import get_settings
from app.core.exceptions import VectorStoreError
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class MilvusClient:
    """Updated Milvus vector database client with parallel searches."""
    
    def __init__(self):
        self.config = get_milvus_config()
        self.is_connected = False
        self.chunks_connection = "chunks_db"
        self.summaries_connection = "summaries_db"
        # Thread pool for parallel Milvus operations
        self.thread_pool = ThreadPoolExecutor(max_workers=8)
    
    async def initialize(self):
        """Initialize Milvus connections."""
        try:
            # Connect to chunks database (mvp_latest_chunks)
            await self._connect_to_chunks_db()
            
            # Connect to summaries database (mvp_latest_summaries)
            await self._connect_to_summaries_db()
            
            self.is_connected = True
            logger.info("✅ Connected to updated Milvus databases")
            logger.info(f"✅ Chunks DB: {self.config.DB_CHUNKS}")
            logger.info(f"✅ Summaries DB: {self.config.DB_SUMMARIES}")
            logger.info(f"✅ Collections: {', '.join(self.config.chunks_collections)}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Milvus: {e}")
            raise VectorStoreError(f"Milvus initialization failed: {str(e)}")
    
    async def _connect_to_chunks_db(self):
        """Connect to the chunks database."""
        try:
            connections.connect(
                alias=self.chunks_connection,
                host=self.config.HOST,
                port=self.config.PORT,
                user=self.config.USER,
                password=self.config.PASSWORD,
                db_name=self.config.DB_CHUNKS  # mvp_latest_chunks
            )
            logger.info(f"Connected to chunks database: {self.config.DB_CHUNKS}")
            
        except Exception as e:
            logger.error(f"Failed to connect to chunks database: {e}")
            raise
    
    async def _connect_to_summaries_db(self):
        """Connect to the summaries database."""
        try:
            connections.connect(
                alias=self.summaries_connection,
                host=self.config.HOST,
                port=self.config.PORT,
                user=self.config.USER,
                password=self.config.PASSWORD,
                db_name=self.config.DB_SUMMARIES  # mvp_latest_summaries
            )
            logger.info(f"Connected to summaries database: {self.config.DB_SUMMARIES}")
            
        except Exception as e:
            logger.warning(f"Failed to connect to summaries database: {e}")
    
    async def search_chunks(
        self,
        query_embedding: List[float],
        limit: int = 10,
        min_score: float = None
    ) -> List[Dict[str, Any]]:
        """Search for document chunks across all collections IN PARALLEL."""
        
        if min_score is None:
            min_score = settings.SIMILARITY_THRESHOLD
        
        try:
            # Create parallel search tasks for all collections
            search_tasks = []
            for collection_name in self.config.chunks_collections:
                task = asyncio.create_task(
                    self._search_chunks_in_collection_async(
                        collection_name, query_embedding, limit, min_score
                    )
                )
                search_tasks.append((collection_name, task))
            
            # Execute all searches in parallel with timeout
            try:
                completed_tasks = await asyncio.wait_for(
                    asyncio.gather(*[task for _, task in search_tasks], return_exceptions=True),
                    timeout=settings.RETRIEVAL_MILVUS_TIMEOUT
                )
            except asyncio.TimeoutError:
                logger.warning(f"Parallel chunk searches timed out after {settings.RETRIEVAL_MILVUS_TIMEOUT}s")
                # Cancel remaining tasks
                for _, task in search_tasks:
                    if not task.done():
                        task.cancel()
                completed_tasks = []
            
            # Combine results from all collections
            all_chunks = []
            for i, (collection_name, task) in enumerate(search_tasks):
                if i < len(completed_tasks) and not isinstance(completed_tasks[i], Exception):
                    collection_chunks = completed_tasks[i]
                    all_chunks.extend(collection_chunks)
                    if collection_chunks:
                        logger.debug(f"   ✅ {collection_name}: {len(collection_chunks)} chunks")
                elif i < len(completed_tasks):
                    logger.warning(f"   ❌ {collection_name}: Error - {str(completed_tasks[i])[:50]}")
                else:
                    logger.warning(f"   ⏱️ {collection_name}: Timed out")

            # Sort by score and return top results
            all_chunks.sort(key=lambda x: x.get("score", 0.0), reverse=True)
            final_chunks = all_chunks[:limit]

            # Log chunks results
            total_found = len(all_chunks)
            logger.info(f"🔍 CHUNKS DATABASE RESULTS (PARALLEL): Total found: {total_found}, Returned: {len(final_chunks)} (limit: {limit})")
            
            logger.debug(f"Retrieved {len(final_chunks)} chunks from {len(self.config.chunks_collections)} collections in parallel")
            
            return final_chunks
            
        except Exception as e:
            logger.error(f"Error in parallel chunk search: {e}")
            return []
    
    async def _search_chunks_in_collection_async(
        self,
        collection_name: str,
        query_embedding: List[float],
        limit: int,
        min_score: float
    ) -> List[Dict[str, Any]]:
        """Search chunks in a specific collection using async executor."""
        
        try:
            # Use thread pool to run synchronous Milvus operations
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.thread_pool,
                self._search_chunks_in_collection_sync,
                collection_name, query_embedding, limit, min_score
            )
            return result
            
        except Exception as e:
            logger.warning(f"Async search failed for {collection_name}: {e}")
            return []
    
    def _search_chunks_in_collection_sync(
        self,
        collection_name: str,
        query_embedding: List[float],
        limit: int,
        min_score: float
    ) -> List[Dict[str, Any]]:
        """Synchronous collection search for thread pool execution."""
        
        try:
            # Check if collection exists
            if not utility.has_collection(collection_name, using=self.chunks_connection):
                return []
            
            # Get collection
            collection = Collection(name=collection_name, using=self.chunks_connection)
            collection.load()
            
            # Get field mapping for this collection
            field_map = self.config.get_chunks_field_map(collection_name)
            
            # Search parameters - optimized for speed
            search_params = {
                "metric_type": "COSINE",
                "params": {"nprobe": min(self.config.NLIST // 4, 64)}
            }
            
            # Define output fields based on collection type
            output_fields = [
                field_map["doc_name_field"],  # doc_name or source_url
                field_map["content_field"],   # chunk_text
                field_map["bucket_field"]     # bucket_source
            ]
            
            # Execute search
            results = collection.search(
                data=[query_embedding],
                anns_field=field_map["embedding_field"],  # embedding
                param=search_params,
                limit=limit,
                output_fields=output_fields
            )
            
            # Process results
            chunks = []
            
            for hits in results:
                for hit in hits:
                    score = float(hit.score)
                    
                    # Apply similarity threshold
                    if score >= min_score:
                        # Get doc_name (handle both doc_name and source_url)
                        doc_name_value = hit.entity.get(field_map["doc_name_field"], "Unknown Document")
                        content = hit.entity.get(field_map["content_field"], "")
                        bucket_source = hit.entity.get(field_map["bucket_field"], "")
                        
                        chunk_data = {
                            "doc_name": doc_name_value,  # This could be doc_name or source_url
                            "content": content,
                            "bucket_source": bucket_source,
                            "score": score,
                            "similarity_score": score,
                            "source": "chunk",
                            "database": "chunks",
                            "collection": collection_name,
                            "source_type": "document_chunk",
                            "is_news": collection_name == self.config.COLLECTION_NEWS  # Flag for news items
                        }
                        
                        chunks.append(chunk_data)
            
            collection.release()
            return chunks
            
        except Exception as e:
            logger.error(f"Sync search error for {collection_name}: {e}")
            return []
    
    async def search_all_summaries(
        self,
        query_embedding: List[float],
        limit_per_collection: int = 5,
        min_score: float = None
    ) -> List[Dict[str, Any]]:
        """Search across all summary collections IN PARALLEL."""
        
        if min_score is None:
            min_score = settings.SIMILARITY_THRESHOLD
        
        try:
            # Create parallel search tasks for all summary collections
            search_tasks = []
            for collection_name in self.config.summaries_collections:
                task = asyncio.create_task(
                    self._search_summaries_in_collection_async(
                        collection_name, query_embedding, limit_per_collection, min_score
                    )
                )
                search_tasks.append((collection_name, task))
            
            # Execute all searches in parallel with timeout
            try:
                completed_tasks = await asyncio.wait_for(
                    asyncio.gather(*[task for _, task in search_tasks], return_exceptions=True),
                    timeout=settings.RETRIEVAL_MILVUS_TIMEOUT
                )
            except asyncio.TimeoutError:
                logger.warning(f"Parallel summary searches timed out after {settings.RETRIEVAL_MILVUS_TIMEOUT}s")
                # Cancel remaining tasks
                for _, task in search_tasks:
                    if not task.done():
                        task.cancel()
                completed_tasks = []
            
            # Combine results from all collections
            all_summaries = []
            for i, (collection_name, task) in enumerate(search_tasks):
                if i < len(completed_tasks) and not isinstance(completed_tasks[i], Exception):
                    collection_summaries = completed_tasks[i]
                    all_summaries.extend(collection_summaries)
                    if collection_summaries:
                        logger.debug(f"   ✅ {collection_name}: {len(collection_summaries)} summaries")
                elif i < len(completed_tasks):
                    logger.warning(f"   ❌ {collection_name}: Error - {str(completed_tasks[i])[:50]}")
                else:
                    logger.warning(f"   ⏱️ {collection_name}: Timed out")
            
            # Sort by score and return results
            all_summaries.sort(key=lambda x: x.get("score", 0.0), reverse=True)

            # Log summaries results
            total_found = len(all_summaries)
            logger.info(f"🔍 SUMMARIES DATABASE RESULTS (PARALLEL): Total found: {total_found}")
            
            logger.debug(f"Retrieved {len(all_summaries)} summaries from {len(self.config.summaries_collections)} collections in parallel")
            
            return all_summaries
            
        except Exception as e:
            logger.error(f"Error in parallel summary search: {e}")
            return []
    
    async def _search_summaries_in_collection_async(
        self,
        collection_name: str,
        query_embedding: List[float],
        limit: int,
        min_score: float
    ) -> List[Dict[str, Any]]:
        """Search summaries in a specific collection using async executor."""
        
        try:
            # Use thread pool to run synchronous Milvus operations
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.thread_pool,
                self._search_summaries_in_collection_sync,
                collection_name, query_embedding, limit, min_score
            )
            return result
            
        except Exception as e:
            logger.warning(f"Async summary search failed for {collection_name}: {e}")
            return []
    
    def _search_summaries_in_collection_sync(
        self,
        collection_name: str,
        query_embedding: List[float],
        limit: int,
        min_score: float
    ) -> List[Dict[str, Any]]:
        """Synchronous summary collection search for thread pool execution."""
        
        try:
            # Check if collection exists
            if not utility.has_collection(collection_name, using=self.summaries_connection):
                return []
            
            # Get collection
            collection = Collection(name=collection_name, using=self.summaries_connection)
            collection.load()
            
            # Get field mapping for this collection
            field_map = self.config.get_summaries_field_map(collection_name)
            
            # Search parameters - optimized for speed
            search_params = {
                "metric_type": "COSINE",
                "params": {"nprobe": min(self.config.NLIST // 4, 64)}
            }
            
            # Define output fields based on collection type
            output_fields = [
                field_map["doc_name_field"],  # doc_name or source_url
                field_map["content_field"],   # abstractive_summary
                field_map["bucket_field"]     # bucket_source
            ]
            
            # Execute search
            results = collection.search(
                data=[query_embedding],
                anns_field=field_map["embedding_field"],  # embedding
                param=search_params,
                limit=limit,
                output_fields=output_fields
            )
            
            # Process results
            summaries = []
            
            for hits in results:
                for hit in hits:
                    score = float(hit.score)
                    
                    # Apply similarity threshold
                    if score >= min_score:
                        # Get doc_name (handle both doc_name and source_url)
                        doc_name_value = hit.entity.get(field_map["doc_name_field"], "Unknown Document")
                        summary_text = hit.entity.get(field_map["content_field"], "")
                        bucket_source = hit.entity.get(field_map["bucket_field"], "")
                        
                        # Determine type based on collection name
                        summary_type = self._get_summary_type(collection_name)
                        
                        summary_data = {
                            "doc_name": doc_name_value,  # This could be doc_name or source_url
                            "title": doc_name_value,     # Use same value for title
                            "summary": summary_text,
                            "content": summary_text,
                            "bucket_source": bucket_source,
                            "type": summary_type,
                            "score": score,
                            "similarity_score": score,
                            "source": "summary",
                            "database": "summaries",
                            "collection": collection_name,
                            "source_type": "document_summary",
                            "is_news": collection_name == self.config.COLLECTION_NEWS,  # Flag for news items
                            "metadata": {"collection": collection_name}
                        }
                        
                        summaries.append(summary_data)
            
            collection.release()
            return summaries
            
        except Exception as e:
            logger.error(f"Sync summary search error for {collection_name}: {e}")
            return []
    
    def _get_summary_type(self, collection_name: str) -> str:
        """Get summary type based on collection name."""
        if collection_name == self.config.COLLECTION_NEWS:
            return "news"
        elif collection_name == self.config.COLLECTION_POLICY:
            return "policy"
        elif collection_name == self.config.COLLECTION_RESEARCH_PAPERS:
            return "research_papers"
        elif collection_name == self.config.COLLECTION_SCIENTIFIC_DATA:
            return "scientific_data"
        else:
            return "unknown"
    
    async def search_documents(
        self,
        query_embedding: List[float],
        limit: int = 10,
        collection_name: Optional[str] = None,
        filter_expr: Optional[str] = None,
        min_score: float = None
    ) -> List[Dict[str, Any]]:
        """
        Fallback search method for backward compatibility.
        This will search the chunks database by default.
        """
        if collection_name is None:
            return await self.search_chunks(query_embedding, limit, min_score)
        
        if min_score is None:
            min_score = settings.SIMILARITY_THRESHOLD
        
        try:
            # Determine which database connection to use
            connection_alias = self.chunks_connection
            if collection_name in self.config.summaries_collections:
                connection_alias = self.summaries_connection
            
            # Check if collection exists
            if not utility.has_collection(collection_name, using=connection_alias):
                logger.debug(f"Collection {collection_name} not found")
                return []
            
            # Get collection
            collection = Collection(name=collection_name, using=connection_alias)
            collection.load()
            
            # Search parameters - updated for your COSINE setup  
            search_params = {
                "metric_type": "COSINE",  # Matches your metric_type
                "params": {"nprobe": min(self.config.NLIST // 4, 64)}  # Dynamic nprobe based on nlist
            }
            
            # Execute search
            results = collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param=search_params,
                limit=limit,
                expr=filter_expr,
                output_fields=["*"]
            )
            
            # Process results
            documents = []
            for hits in results:
                for hit in hits:
                    score = float(hit.score)
                    
                    # Apply similarity threshold
                    if score >= min_score:
                        doc_data = {
                            "id": str(hit.id),
                            "similarity_score": score,
                            "score": score,
                            "collection": collection_name,
                            "metadata": {}
                        }
                        
                        # Add all entity fields
                        for field_name, field_value in hit.entity._row_data.items():
                            doc_data[field_name] = field_value
                            doc_data["metadata"][field_name] = field_value
                        
                        documents.append(doc_data)
            
            collection.release()
            logger.debug(f"Retrieved {len(documents)} documents from {collection_name}")
            return documents
            
        except Exception as e:
            logger.error(f"Error in search_documents: {e}")
            return []
    
    async def health_check(self) -> bool:
        """Check Milvus health."""
        try:
            if not self.is_connected:
                return False
            
            # Test chunks database
            chunks_collections = utility.list_collections(using=self.chunks_connection)
            
            # Test summaries database (optional)
            try:
                summaries_collections = utility.list_collections(using=self.summaries_connection)
            except:
                pass
            
            return True
            
        except Exception as e:
            logger.error(f"Milvus health check failed: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get statistics for both databases."""
        try:
            stats = {
                "connected": self.is_connected,
                "config": {
                    "host": self.config.HOST,
                    "port": self.config.PORT,
                    "chunks_db": self.config.DB_CHUNKS,
                    "summaries_db": self.config.DB_SUMMARIES,
                    "similarity_threshold": settings.SIMILARITY_THRESHOLD,
                    "parallel_searches": True,
                    "thread_pool_workers": self.thread_pool._max_workers
                },
                "chunks_database": {},
                "summaries_database": {},
                "collections": {}
            }
            
            # Get chunks database info
            try:
                chunks_collections = utility.list_collections(using=self.chunks_connection)
                stats["chunks_database"]["collections"] = chunks_collections
                
                for name in chunks_collections:
                    try:
                        collection = Collection(name=name, using=self.chunks_connection)
                        collection.load()
                        stats["collections"][f"chunks:{name}"] = {
                            "num_entities": collection.num_entities,
                            "database": "chunks",
                            "type": self._get_summary_type(name)
                        }
                        collection.release()
                    except Exception as e:
                        stats["collections"][f"chunks:{name}"] = {"error": str(e)}
                        
            except Exception as e:
                stats["chunks_database"]["error"] = str(e)
            
            # Get summaries database info
            try:
                summaries_collections = utility.list_collections(using=self.summaries_connection)
                stats["summaries_database"]["collections"] = summaries_collections
                
                for name in summaries_collections:
                    try:
                        collection = Collection(name=name, using=self.summaries_connection)
                        collection.load()
                        stats["collections"][f"summaries:{name}"] = {
                            "num_entities": collection.num_entities,
                            "database": "summaries",
                            "type": self._get_summary_type(name)
                        }
                        collection.release()
                    except Exception as e:
                        stats["collections"][f"summaries:{name}"] = {"error": str(e)}
                        
            except Exception as e:
                stats["summaries_database"]["error"] = str(e)
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get Milvus stats: {e}")
            return {"connected": False, "error": str(e)}
    
    async def close(self):
        """Close all Milvus connections."""
        try:
            if self.is_connected:
                connections.disconnect(self.chunks_connection)
                connections.disconnect(self.summaries_connection)
                self.is_connected = False
                logger.info("All Milvus connections closed")
            
            # Shutdown thread pool
            self.thread_pool.shutdown(wait=False)
            
        except Exception as e:
            logger.error(f"Error closing Milvus connections: {e}")


# Global Milvus client instance
milvus_client = MilvusClient()


def get_milvus_client() -> MilvusClient:
    """Get Milvus client instance."""
    return milvus_client