"""
Clean RAG orchestrator without web search functionality
Fixed: Proper title handling for both start and continue conversations
"""

import asyncio
import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from app.services.rag.data_sources import get_multi_source_retriever
from app.services.rag.reranker import get_reranker_service
from app.services.rag.response_generator import get_response_generator_service
from app.services.tracing import get_langfuse_client, is_langfuse_enabled
from app.core.exceptions import RAGException
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


@dataclass
class RAGResponse:
    """RAG response with essential metadata."""
    title: str
    content: str
    social_tipping_point: str
    sources_used: Dict[str, int]
    total_processing_time: float
    retrieval_time: float
    reranking_time: float
    generation_time: float
    has_relevant_data: bool
    query_preprocessed: bool = False
    original_query: Optional[str] = None
    processed_query: Optional[str] = None
    reference_data: Optional[Dict[str, List[Dict[str, Any]]]] = None


class RAGOrchestrator:
    """Clean RAG orchestrator without web search functionality."""
    
    def __init__(self):
        self.retriever = None
        self.reranker = None
        self.response_generator = None
        self.is_initialized = False
    
    async def initialize(self):
        """Initialize all components."""
        try:
            logger.info("Initializing RAG orchestrator...")
            
            init_tasks = [
                get_multi_source_retriever(),
                get_reranker_service(),
                get_response_generator_service()
            ]
            
            self.retriever, self.reranker, self.response_generator = await asyncio.gather(
                *init_tasks, return_exceptions=True
            )
            
            if isinstance(self.retriever, Exception):
                logger.error(f"Retriever initialization failed: {self.retriever}")
                self.retriever = None
            
            if isinstance(self.reranker, Exception):
                logger.warning(f"Reranker initialization failed: {self.reranker}")
                self.reranker = None
            
            if isinstance(self.response_generator, Exception):
                logger.error(f"Response generator initialization failed: {self.response_generator}")
                raise RAGException("Critical component initialization failed")
            
            self.is_initialized = True
            logger.info("✅ RAG orchestrator initialized without web search")
            
        except Exception as e:
            logger.error(f"Failed to initialize RAG orchestrator: {e}")
            raise RAGException(f"Orchestrator initialization failed: {str(e)}")
    
    async def process_start_conversation(
        self,
        original_query: str,
        processed_query: Optional[str] = None,
        language: str = "en",
        difficulty_level: str = "low",
        was_processed: bool = False
    ) -> RAGResponse:
        """Process start conversation with basic query fixes only"""
        if not self.is_initialized:
            await self.initialize()
        
        total_start_time = time.perf_counter()
        
        try:
            return await asyncio.wait_for(
                self._process_start_conversation_internal(
                    original_query, processed_query, language, difficulty_level, 
                    was_processed, total_start_time
                ),
                timeout=settings.MAX_RESPONSE_TIME_SECONDS
            )
        
        except asyncio.TimeoutError:
            logger.error(f"Start conversation timed out after {settings.MAX_RESPONSE_TIME_SECONDS}s")
            return self._create_timeout_response(original_query, settings.MAX_RESPONSE_TIME_SECONDS)
        
        except Exception as e:
            logger.error(f"Error in start conversation: {e}")
            return self._create_error_response(
                original_query, str(e), time.perf_counter() - total_start_time
            )
    
    async def _process_start_conversation_internal(
        self,
        original_query: str,
        processed_query: Optional[str],
        language: str,
        difficulty_level: str,
        was_processed: bool,
        total_start_time: float
    ) -> RAGResponse:
        """Internal start conversation processing with basic fixes only"""
        
        # For start conversations, use basic fixes only
        search_query = processed_query if processed_query else original_query
        
        # Apply basic fixes if not already processed
        if not was_processed:
            from app.services.rag.llm_query_processor import get_llm_query_preprocessor
            preprocessor = await get_llm_query_preprocessor()
            
            if is_langfuse_enabled():
                langfuse_client = get_langfuse_client()
                with langfuse_client.start_as_current_span(
                    name="basic_query_fixes",
                    input=original_query,
                    metadata={"component": "query_processor", "step": "1_basic_fixes", "type": "start"}
                ) as span:
                    search_query = await preprocessor.apply_basic_fixes_for_start(original_query, language)
                    was_processed = (search_query != original_query)
                    
                    span.update(
                        output=f"Fixed: {search_query}" if was_processed else "No fixes needed",
                        metadata={"was_processed": was_processed, "fixes_applied": was_processed}
                    )
            else:
                search_query = await preprocessor.apply_basic_fixes_for_start(original_query, language)
                was_processed = (search_query != original_query)
        
        # Step 2: Retrieval (child span)
        retrieval_result = None
        if self.retriever:
            if is_langfuse_enabled():
                langfuse_client = get_langfuse_client()
                with langfuse_client.start_as_current_span(
                    name="retrieval",
                    input=search_query,
                    metadata={"component": "multi_source_retriever", "step": "2_retrieval"}
                ) as span:
                    try:
                        retrieval_result = await self.retriever.retrieve_all_sources(
                            query=search_query,
                            use_cache=settings.ENABLE_RESULT_CACHING
                        )
                        
                        span.update(
                            output=f"Retrieved {retrieval_result.total_results} results",
                            metadata={
                                "chunks": len(retrieval_result.chunks),
                                "summaries": len(retrieval_result.summaries),
                                "graph": len(retrieval_result.graph_data),
                                "retrieval_time": retrieval_result.retrieval_time
                            }
                        )
                    except Exception as e:
                        span.update(output=f"Retrieval failed: {e}", level="ERROR")
                        retrieval_result = None
            else:
                try:
                    retrieval_result = await self.retriever.retrieve_all_sources(
                        query=search_query,
                        use_cache=settings.ENABLE_RESULT_CACHING
                    )
                except Exception as e:
                    logger.error(f"Retrieval failed: {e}")
                    retrieval_result = None
        
        if not retrieval_result or retrieval_result.total_results == 0:
            return await self._create_fallback_response(
                original_query, search_query if was_processed else None, language, difficulty_level,
                was_processed, time.perf_counter() - total_start_time
            )
        
        # Step 3: Reranking (child span)
        reranking_start_time = time.perf_counter()
        reranked_results = []
        
        if self.reranker and retrieval_result.total_results > 5:
            if is_langfuse_enabled():
                langfuse_client = get_langfuse_client()
                with langfuse_client.start_as_current_span(
                    name="reranking",
                    input=f"Reranking {retrieval_result.total_results} results",
                    metadata={"component": "cross_encoder_reranker", "step": "3_reranking"}
                ) as span:
                    try:
                        combined_results = self._combine_results_for_reranking(
                            retrieval_result.chunks or [],
                            retrieval_result.summaries or [],
                            retrieval_result.graph_data or []
                        )
                        
                        reranked_results = await self.reranker.rerank_results(
                            query=search_query,
                            results=combined_results,
                            top_k=settings.TOP_K_RERANK
                        )
                        
                        span.update(
                            output=f"Reranked to {len(reranked_results)} results",
                            metadata={
                                "input_count": len(combined_results),
                                "output_count": len(reranked_results),
                                "reranking_time": time.perf_counter() - reranking_start_time
                            }
                        )
                    except Exception as e:
                        span.update(output=f"Reranking failed: {e}", level="ERROR")
                        reranked_results = []
            else:
                try:
                    combined_results = self._combine_results_for_reranking(
                        retrieval_result.chunks or [],
                        retrieval_result.summaries or [],
                        retrieval_result.graph_data or []
                    )
                    
                    reranked_results = await self.reranker.rerank_results(
                        query=search_query,
                        results=combined_results,
                        top_k=settings.TOP_K_RERANK
                    )
                except Exception as e:
                    logger.error(f"Reranking failed: {e}")
                    reranked_results = []
        else:
            combined_results = self._combine_results_simple(
                retrieval_result.chunks or [],
                retrieval_result.summaries or [],
                retrieval_result.graph_data or []
            )
            reranked_results = combined_results[:settings.TOP_K_RERANK]
        
        reranking_time = time.perf_counter() - reranking_start_time
        
        if not reranked_results:
            return await self._create_fallback_response(
                original_query, search_query if was_processed else None, language, difficulty_level,
                was_processed, time.perf_counter() - total_start_time
            )
        
        # Step 4: Response generation (child span)
        generation_start_time = time.perf_counter()
        
        if is_langfuse_enabled():
            langfuse_client = get_langfuse_client()
            with langfuse_client.start_as_current_span(
                name="llm_generation",
                input="[Context + Query]",
                metadata={"component": "response_generator", "step": "4_generation"}
            ) as span:
                try:
                    chunks, summaries, graph_data = self._split_reranked_results(reranked_results)
                    
                    generation_result = await self.response_generator.generate_start_conversation_response(
                        original_query=original_query,
                        processed_query=search_query if was_processed else None,
                        chunks=chunks[:settings.MAX_CONTEXT_CHUNKS],
                        summaries=summaries[:settings.MAX_CONTEXT_SUMMARIES],
                        graph_data=graph_data[:settings.MAX_CONTEXT_GRAPH_ITEMS],
                        language=language,
                        difficulty_level=difficulty_level,
                        was_processed=was_processed
                    )
                    
                    generation_time = time.perf_counter() - generation_start_time
                    
                    span.update(
                        output=generation_result.content[:500],
                        metadata={
                            "conversation_type": "start",
                            "language": language,
                            "generation_time": generation_time,
                            "processing_type": "basic_fixes_only",
                            "title_generated": bool(generation_result.title)
                        }
                    )

                    span.score(name="Response Generation LLM", value=generation_time)
                    
                except Exception as e:
                    span.update(output=f"Generation failed: {e}", level="ERROR")
                    return await self._create_fallback_response(
                        original_query, search_query if was_processed else None, language, difficulty_level,
                        was_processed, time.perf_counter() - total_start_time
                    )
        else:
            try:
                chunks, summaries, graph_data = self._split_reranked_results(reranked_results)
                
                generation_result = await self.response_generator.generate_start_conversation_response(
                    original_query=original_query,
                    processed_query=search_query if was_processed else None,
                    chunks=chunks[:settings.MAX_CONTEXT_CHUNKS],
                    summaries=summaries[:settings.MAX_CONTEXT_SUMMARIES],
                    graph_data=graph_data[:settings.MAX_CONTEXT_GRAPH_ITEMS],
                    language=language,
                    difficulty_level=difficulty_level,
                    was_processed=was_processed
                )
                
                generation_time = time.perf_counter() - generation_start_time
                
            except Exception as e:
                logger.error(f"Response generation failed: {e}")
                return await self._create_fallback_response(
                    original_query, search_query if was_processed else None, language, difficulty_level,
                    was_processed, time.perf_counter() - total_start_time
                )
        
        # Create response
        total_time = time.perf_counter() - total_start_time
        response = self._create_response(
            generation_result=generation_result,
            retrieval_result=retrieval_result,
            reranked_results=reranked_results,
            total_time=total_time,
            reranking_time=reranking_time,
            original_query=original_query,
            processed_query=search_query if was_processed else None,
            was_processed=was_processed,
            conversation_type="start"
        )
        
        logger.info(f"Start conversation completed in {total_time:.3f}s (basic fixes only) - Title: '{response.title}'")
        return response
    
    async def process_continue_conversation(
        self,
        original_query: str,
        conversation_memory: str,
        processed_query: Optional[str] = None,
        language: str = "en",
        difficulty_level: str = "low",
        was_processed: bool = False,
        message_count: int = 1
    ) -> RAGResponse:
        """Process continue conversation with full pronoun resolution"""
        if not self.is_initialized:
            await self.initialize()
        
        total_start_time = time.perf_counter()
        
        try:
            return await asyncio.wait_for(
                self._process_continue_conversation_internal(
                    original_query, conversation_memory, processed_query, 
                    language, difficulty_level, was_processed, message_count, 
                    total_start_time
                ),
                timeout=settings.MAX_RESPONSE_TIME_SECONDS
            )
        
        except asyncio.TimeoutError:
            logger.error(f"Continue conversation timed out after {settings.MAX_RESPONSE_TIME_SECONDS}s")
            return self._create_timeout_response(original_query, settings.MAX_RESPONSE_TIME_SECONDS)
        
        except Exception as e:
            logger.error(f"Error in continue conversation: {e}")
            return self._create_error_response(
                original_query, str(e), time.perf_counter() - total_start_time
            )
    
    async def _process_continue_conversation_internal(
        self,
        original_query: str,
        conversation_memory: str,
        processed_query: Optional[str],
        language: str,
        difficulty_level: str,
        was_processed: bool,
        message_count: int,
        total_start_time: float
    ) -> RAGResponse:
        """Internal continue conversation processing with full pronoun resolution"""
        
        # For continue conversations, apply full processing including pronoun resolution
        search_query = processed_query if processed_query else original_query
        
        # Apply full processing if not already processed
        if not was_processed:
            from app.services.rag.llm_query_processor import get_llm_query_preprocessor
            preprocessor = await get_llm_query_preprocessor()
            
            if is_langfuse_enabled():
                langfuse_client = get_langfuse_client()
                with langfuse_client.start_as_current_span(
                    name="full_query_processing",
                    input=original_query,
                    metadata={"component": "query_processor", "step": "1_full_processing", "type": "continue", "message_count": message_count}
                ) as span:
                    search_query = await preprocessor.apply_full_processing_for_continue(
                        original_query, language, conversation_memory
                    )
                    was_processed = (search_query != original_query)
                    
                    span.update(
                        output=f"Processed: {search_query}" if was_processed else "No processing needed",
                        metadata={"was_processed": was_processed, "has_memory": bool(conversation_memory), "pronoun_resolution": was_processed}
                    )
            else:
                search_query = await preprocessor.apply_full_processing_for_continue(
                    original_query, language, conversation_memory
                )
                was_processed = (search_query != original_query)
        
        # Step 2: Retrieval (child span)
        if self.retriever:
            if is_langfuse_enabled():
                langfuse_client = get_langfuse_client()
                with langfuse_client.start_as_current_span(
                    name="retrieval",
                    input=search_query,
                    metadata={"component": "multi_source_retriever", "step": "2_retrieval"}
                ) as span:
                    try:
                        retrieval_result = await self.retriever.retrieve_all_sources(
                            query=search_query,
                            use_cache=settings.ENABLE_RESULT_CACHING
                        )
                        
                        span.update(
                            output=f"Retrieved {retrieval_result.total_results} results",
                            metadata={
                                "chunks": len(retrieval_result.chunks),
                                "summaries": len(retrieval_result.summaries),
                                "graph": len(retrieval_result.graph_data),
                                "retrieval_time": retrieval_result.retrieval_time
                            }
                        )
                    except Exception as e:
                        span.update(output=f"Retrieval failed: {e}", level="ERROR")
                        retrieval_result = None
            else:
                try:
                    retrieval_result = await self.retriever.retrieve_all_sources(
                        query=search_query,
                        use_cache=settings.ENABLE_RESULT_CACHING
                    )
                except Exception as e:
                    logger.error(f"Retrieval failed: {e}")
                    retrieval_result = None
        else:
            retrieval_result = None
        
        if not retrieval_result or retrieval_result.total_results == 0:
            return await self._create_continue_fallback_response(
                original_query, conversation_memory, search_query if was_processed else None, 
                language, difficulty_level, was_processed, message_count,
                time.perf_counter() - total_start_time
            )
        
        # Step 3: Reranking (child span)
        reranking_start_time = time.perf_counter()
        
        if self.reranker and retrieval_result.total_results > 6:
            if is_langfuse_enabled():
                langfuse_client = get_langfuse_client()
                with langfuse_client.start_as_current_span(
                    name="reranking",
                    input=f"Reranking {retrieval_result.total_results} results",
                    metadata={"component": "cross_encoder_reranker", "step": "3_reranking"}
                ) as span:
                    try:
                        combined_results = self._combine_results_for_reranking(
                            retrieval_result.chunks,
                            retrieval_result.summaries,
                            retrieval_result.graph_data
                        )
                        
                        reranked_results = await self.reranker.rerank_results(
                            query=search_query,
                            results=combined_results,
                            top_k=settings.TOP_K_RERANK + 2
                        )
                        
                        span.update(
                            output=f"Reranked to {len(reranked_results)} results",
                            metadata={
                                "input_count": len(combined_results),
                                "output_count": len(reranked_results),
                                "reranking_time": time.perf_counter() - reranking_start_time
                            }
                        )
                    except Exception as e:
                        span.update(output=f"Reranking failed: {e}", level="ERROR")
                        reranked_results = []
            else:
                try:
                    combined_results = self._combine_results_for_reranking(
                        retrieval_result.chunks,
                        retrieval_result.summaries,
                        retrieval_result.graph_data
                    )
                    
                    reranked_results = await self.reranker.rerank_results(
                        query=search_query,
                        results=combined_results,
                        top_k=settings.TOP_K_RERANK + 2
                    )
                except Exception as e:
                    logger.error(f"Reranking failed: {e}")
                    reranked_results = []
        else:
            combined_results = self._combine_results_simple(
                retrieval_result.chunks,
                retrieval_result.summaries,
                retrieval_result.graph_data
            )
            reranked_results = combined_results[:settings.TOP_K_RERANK + 2]
        
        reranking_time = time.perf_counter() - reranking_start_time
        
        # Step 4: Generate response (child span)
        generation_start_time = time.perf_counter()
        
        if is_langfuse_enabled():
            langfuse_client = get_langfuse_client()
            with langfuse_client.start_as_current_span(
                name="llm_generation",
                input="[Context + Query + Memory]",
                metadata={"component": "response_generator", "step": "4_generation"}
            ) as span:
                try:
                    chunks, summaries, graph_data = self._split_reranked_results(reranked_results)
                    
                    generation_result = await self.response_generator.generate_continue_conversation_response(
                        original_query=original_query,
                        processed_query=search_query if was_processed else None,
                        chunks=chunks[:settings.MAX_CONTEXT_CHUNKS + 1],
                        summaries=summaries[:settings.MAX_CONTEXT_SUMMARIES + 1],
                        graph_data=graph_data[:settings.MAX_CONTEXT_GRAPH_ITEMS],
                        conversation_memory=conversation_memory,
                        language=language,
                        difficulty_level=difficulty_level,
                        was_processed=was_processed,
                        message_count=message_count
                    )
                    
                    generation_time = time.perf_counter() - generation_start_time
                    
                    span.update(
                        output=generation_result.content[:500],
                        metadata={
                            "conversation_type": "continue",
                            "language": language,
                            "generation_time": generation_time,
                            "message_count": message_count,
                            "processing_type": "full_with_pronoun_resolution",
                            "title_generated": bool(generation_result.title)
                        }
                    )
                    span.score(name="Response Generation LLM", value=generation_time) 
                    
                except Exception as e:
                    span.update(output=f"Generation failed: {e}", level="ERROR")
                    return await self._create_continue_fallback_response(
                        original_query, conversation_memory, search_query if was_processed else None, 
                        language, difficulty_level, was_processed, message_count,
                        time.perf_counter() - total_start_time
                    )
        else:
            try:
                chunks, summaries, graph_data = self._split_reranked_results(reranked_results)
                
                generation_result = await self.response_generator.generate_continue_conversation_response(
                    original_query=original_query,
                    processed_query=search_query if was_processed else None,
                    chunks=chunks[:settings.MAX_CONTEXT_CHUNKS + 1],
                    summaries=summaries[:settings.MAX_CONTEXT_SUMMARIES + 1],
                    graph_data=graph_data[:settings.MAX_CONTEXT_GRAPH_ITEMS],
                    conversation_memory=conversation_memory,
                    language=language,
                    difficulty_level=difficulty_level,
                    was_processed=was_processed,
                    message_count=message_count
                )
                
                generation_time = time.perf_counter() - generation_start_time
                
            except Exception as e:
                logger.error(f"Response generation failed: {e}")
                return await self._create_continue_fallback_response(
                    original_query, conversation_memory, search_query if was_processed else None, 
                    language, difficulty_level, was_processed, message_count,
                    time.perf_counter() - total_start_time
                )
        
        # Create response
        total_time = time.perf_counter() - total_start_time
        response = self._create_response(
            generation_result=generation_result,
            retrieval_result=retrieval_result,
            reranked_results=reranked_results,
            total_time=total_time,
            reranking_time=reranking_time,
            original_query=original_query,
            processed_query=search_query if was_processed else None,
            was_processed=was_processed,
            conversation_type="continue"
        )
        
        logger.info(f"Continue conversation completed in {total_time:.3f}s (full processing) - Title: None (no title for continue)")
        return response
    
    # Helper methods
    def _combine_results_simple(
        self,
        chunks: List[Dict[str, Any]],
        summaries: List[Dict[str, Any]],
        graph_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Simple result combination without reranking overhead."""
        combined = []
        
        all_results = [
            (chunk, "chunk") for chunk in chunks
        ] + [
            (summary, "summary") for summary in summaries
        ] + [
            (graph_item, "graph") for graph_item in graph_data
        ]
        
        all_results.sort(
            key=lambda x: x[0].get("score", x[0].get("similarity_score", 0.0)),
            reverse=True
        )
        
        for result, source_type in all_results:
            result["source"] = source_type
            combined.append(result)
        
        return combined
    
    def _combine_results_for_reranking(
        self,
        chunks: List[Dict[str, Any]],
        summaries: List[Dict[str, Any]],
        graph_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Combine results for reranking."""
        combined = []
        
        for chunk in chunks:
            combined.append({**chunk, "source": "chunk"})
        
        for summary in summaries:
            combined.append({**summary, "source": "summary"})
        
        for graph_item in graph_data:
            combined.append({**graph_item, "source": "graph"})
        
        return combined
    
    def _split_reranked_results(
        self, 
        reranked_results: List[Dict[str, Any]]
    ) -> tuple:
        """Split reranked results by source type."""
        chunks = []
        summaries = []
        graph_data = []
        
        for result in reranked_results:
            source_type = result.get("source", "unknown")
            
            if source_type == "chunk":
                chunks.append(result)
            elif source_type == "summary":
                summaries.append(result)
            elif source_type == "graph":
                graph_data.append(result)
        
        return chunks, summaries, graph_data
    
    def _create_response(
        self,
        generation_result,
        retrieval_result,
        reranked_results: List[Dict[str, Any]],
        total_time: float,
        reranking_time: float,
        original_query: str,
        processed_query: Optional[str],
        was_processed: bool,
        conversation_type: str = "start"
    ) -> RAGResponse:
        """Create response object with proper title handling - title ONLY for start conversations."""
        
        source_counts = {"chunks": 0, "summaries": 0, "graph_data": 0}
        chunks_for_refs = []
        summaries_for_refs = []
        graph_for_refs = []
        
        for result in reranked_results:
            if result is None:
                continue
                
            source_type = result.get("source", "unknown")
            if source_type == "chunk":
                source_counts["chunks"] += 1
                chunks_for_refs.append(result)
            elif source_type == "summary":
                source_counts["summaries"] += 1
                summaries_for_refs.append(result)
            elif source_type == "graph":
                source_counts["graph_data"] += 1
                graph_for_refs.append(result)
        
        source_counts["total"] = len(reranked_results)
        
        reference_data = {
            "chunks": chunks_for_refs,
            "summaries": summaries_for_refs,
            "graph_data": graph_for_refs,
            "all_reranked": reranked_results
        }
        
        # Handle title properly based on conversation type
        if conversation_type == "start":
            # Start conversations: get title from LLM response
            title = getattr(generation_result, 'title', None) or 'Climate Information'
            logger.debug(f"Start conversation title: '{title}'")
        else:
            # Continue conversations: NO TITLE (empty string)
            title = ""
            logger.debug(f"Continue conversation: no title (empty)")
        
        return RAGResponse(
            title=title,
            content=getattr(generation_result, 'content', 'Processing your climate question...'),
            social_tipping_point=getattr(generation_result, 'social_tipping_point', 'No specific social tipping point available for this query.'),
            sources_used=source_counts,
            total_processing_time=total_time,
            retrieval_time=getattr(retrieval_result, 'retrieval_time', 0.0),
            reranking_time=reranking_time,
            generation_time=getattr(generation_result, 'generation_time', 0.0),
            has_relevant_data=len(reranked_results) > 0,
            query_preprocessed=was_processed,
            original_query=original_query,
            processed_query=processed_query if was_processed else None,
            reference_data=reference_data
        )
    
    async def _create_fallback_response(
        self,
        original_query: str,
        processed_query: Optional[str],
        language: str,
        difficulty_level: str,
        was_processed: bool,
        total_time: float
    ) -> RAGResponse:
        """Create fallback response for start conversation."""
        
        if is_langfuse_enabled():
            langfuse_client = get_langfuse_client()
            with langfuse_client.start_as_current_span(
                name="fallback_response",
                input=f"No retrieval data for: {original_query}",
                metadata={"component": "fallback_handler", "step": "fallback"}
            ) as span:
                span.update(output="Generated fallback response")
        
        return RAGResponse(
            title="Climate Information",
            content=f"Welcome to NeuroClima Bot! I understand you're asking about '{original_query}'. While I don't have specific documents for this exact query right now, I'm here to help with climate-related questions. Please feel free to rephrase your question or ask about other climate topics.",
            social_tipping_point="No specific social tipping point available for this query.",
            sources_used={"chunks": 0, "summaries": 0, "graph_data": 0, "total": 0},
            total_processing_time=total_time,
            retrieval_time=0.0,
            reranking_time=0.0,
            generation_time=0.1,
            has_relevant_data=False,
            query_preprocessed=was_processed,
            original_query=original_query,
            processed_query=processed_query if was_processed else None
        )
    
    async def _create_continue_fallback_response(
        self,
        original_query: str,
        conversation_memory: str,
        processed_query: Optional[str],
        language: str,
        difficulty_level: str,
        was_processed: bool,
        message_count: int,
        total_time: float
    ) -> RAGResponse:
        """Create fallback response for continue conversation with NO title."""
        
        if is_langfuse_enabled():
            langfuse_client = get_langfuse_client()
            with langfuse_client.start_as_current_span(
                name="fallback_response",
                input=f"No retrieval data for continue: {original_query}",
                metadata={"component": "fallback_handler", "step": "fallback"}
            ) as span:
                span.update(output="Generated continue fallback response")
        
        return RAGResponse(
            title="",  # Empty title for continue conversations
            content=f"Thank you for the follow-up question about '{original_query}'. While I don't have specific documents for this particular aspect right now, I'm continuing to assist with your climate inquiry. Based on our conversation, feel free to explore related topics or rephrase your question.",
            social_tipping_point="No specific social tipping point available for this query.",
            sources_used={"chunks": 0, "summaries": 0, "graph_data": 0, "total": 0},
            total_processing_time=total_time,
            retrieval_time=0.0,
            reranking_time=0.0,
            generation_time=0.1,
            has_relevant_data=False,
            query_preprocessed=was_processed,
            original_query=original_query,
            processed_query=processed_query if was_processed else None
        )
    
    def _create_timeout_response(self, original_query: str, timeout_duration: float) -> RAGResponse:
        """Create response for timeout situations - title only if we know it's a start conversation."""
        # Note: We don't know conversation type here, so we'll use a generic title
        # This should rarely happen, so a generic title is acceptable
        
        return RAGResponse(
            title="Climate Assistant - Processing",
            content=f"I'm processing your question about '{original_query}' but it's taking longer than expected. Please try rephrasing your question or ask about a specific climate topic for a faster response.",
            social_tipping_point="No specific social tipping point available for this query.",
            sources_used={"chunks": 0, "summaries": 0, "graph_data": 0, "total": 0},
            total_processing_time=timeout_duration,
            retrieval_time=0.0,
            reranking_time=0.0,
            generation_time=0.1,
            has_relevant_data=False,
            query_preprocessed=False,
            original_query=original_query,
            processed_query=None
        )
    
    def _create_error_response(
        self,
        original_query: str,
        error_message: str,
        total_time: float
    ) -> RAGResponse:
        """Create response for error situations - title only if we know it's a start conversation."""
        # Note: We don't know conversation type here, so we'll use a generic title
        # This should rarely happen, so a generic title is acceptable
        
        return RAGResponse(
            title="Climate Assistant",
            content=f"I encountered a technical issue while processing your question about '{original_query}'. Please try again or rephrase your question. I'm here to help with climate-related topics.",
            social_tipping_point="No specific social tipping point available for this query.",
            sources_used={"chunks": 0, "summaries": 0, "graph_data": 0, "total": 0},
            total_processing_time=total_time,
            retrieval_time=0.0,
            reranking_time=0.0,
            generation_time=0.1,
            has_relevant_data=False,
            query_preprocessed=False,
            original_query=original_query,
            processed_query=None
        )
    
    async def health_check(self) -> Dict[str, bool]:
        """Health check with component monitoring."""
        if not self.is_initialized:
            return {"initialized": False}

        try:
            retriever_health = await self.retriever.health_check() if self.retriever else False
            reranker_health = await self.reranker.health_check() if self.reranker else True
            generator_health = await self.response_generator.health_check() if self.response_generator else False

            return {
                "initialized": True,
                "retriever": retriever_health,
                "reranker": reranker_health,
                "response_generator": generator_health,
                "overall": retriever_health and generator_health,
                "simplified_processing": True
            }

        except Exception as e:
            logger.error(f"Orchestrator health check failed: {e}")
            return {"initialized": False, "error": str(e)}


# Global orchestrator instance
rag_orchestrator = RAGOrchestrator()


async def get_rag_orchestrator() -> RAGOrchestrator:
    """Get the RAG orchestrator instance."""
    if not rag_orchestrator.is_initialized:
        await rag_orchestrator.initialize()
    return rag_orchestrator