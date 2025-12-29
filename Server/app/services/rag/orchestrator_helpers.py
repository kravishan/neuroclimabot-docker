"""
Helper functions for RAG orchestrator to reduce function complexity.
Extracted from orchestrator.py to improve code organization and readability.
"""

from typing import Dict, Any, List, Optional, Tuple
import time

from app.services.tracing import get_langfuse_client, is_langfuse_enabled
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def apply_query_processing(
    original_query: str,
    language: str,
    was_processed: bool,
    is_start_conversation: bool = True
) -> Tuple[str, bool]:
    """
    Apply query processing/fixes based on conversation type.

    Args:
        original_query: The original user query
        language: Detected language
        was_processed: Whether query was already processed
        is_start_conversation: True for start, False for continue

    Returns:
        Tuple of (processed_query, was_processed_flag)
    """
    if was_processed:
        return original_query, True

    from app.services.rag.llm_query_processor import get_llm_query_preprocessor
    preprocessor = await get_llm_query_preprocessor()

    if is_langfuse_enabled():
        langfuse_client = get_langfuse_client()
        processing_type = "basic_fixes" if is_start_conversation else "advanced_processing"

        with langfuse_client.start_as_current_span(
            name=processing_type,
            input=original_query,
            metadata={
                "component": "query_processor",
                "step": "1_query_processing",
                "type": "start" if is_start_conversation else "continue"
            }
        ) as span:
            if is_start_conversation:
                processed = await preprocessor.apply_basic_fixes_for_start(original_query, language)
            else:
                processed = await preprocessor.apply_basic_fixes_for_start(original_query, language)

            was_changed = (processed != original_query)

            span.update(
                output=f"Processed: {processed}" if was_changed else "No changes needed",
                metadata={"was_processed": was_changed, "changes_applied": was_changed}
            )

            return processed, was_changed
    else:
        if is_start_conversation:
            processed = await preprocessor.apply_basic_fixes_for_start(original_query, language)
        else:
            processed = await preprocessor.apply_basic_fixes_for_start(original_query, language)

        return processed, (processed != original_query)


async def perform_retrieval(
    retriever,
    search_query: str,
    use_cache: bool = True,
    bucket: Optional[str] = None
):
    """
    Perform retrieval from all sources with optional tracing.

    Args:
        retriever: The retriever instance
        search_query: Query to search for
        use_cache: Whether to use caching
        bucket: Optional bucket filter

    Returns:
        RetrievalResult or None if failed
    """
    if not retriever:
        return None

    if is_langfuse_enabled():
        langfuse_client = get_langfuse_client()
        with langfuse_client.start_as_current_span(
            name="retrieval",
            input=search_query,
            metadata={
                "component": "multi_source_retriever",
                "step": "2_retrieval",
                "bucket": bucket or "all"
            }
        ) as span:
            try:
                result = await retriever.retrieve_all_sources(
                    query=search_query,
                    use_cache=use_cache,
                    bucket=bucket
                )

                span.update(
                    output=f"Retrieved {result.total_results} results",
                    metadata={
                        "chunks": len(result.chunks),
                        "summaries": len(result.summaries),
                        "graph": len(result.graph_data),
                        "retrieval_time": result.retrieval_time
                    }
                )

                return result

            except Exception as e:
                span.update(output=f"Retrieval failed: {e}", level="ERROR")
                logger.error(f"Retrieval failed: {e}")
                return None
    else:
        try:
            return await retriever.retrieve_all_sources(
                query=search_query,
                use_cache=use_cache,
                bucket=bucket
            )
        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            return None


async def perform_reranking(
    reranker,
    combined_results: List[Dict[str, Any]],
    search_query: str,
    top_k: int
) -> Tuple[List[Dict[str, Any]], float]:
    """
    Perform reranking with optional tracing.

    Args:
        reranker: The reranker instance
        combined_results: Combined retrieval results
        search_query: Original search query
        top_k: Number of top results to keep

    Returns:
        Tuple of (reranked_results, reranking_time)
    """
    start_time = time.perf_counter()

    if not reranker or len(combined_results) <= 5:
        return combined_results[:top_k], time.perf_counter() - start_time

    if is_langfuse_enabled():
        langfuse_client = get_langfuse_client()
        with langfuse_client.start_as_current_span(
            name="reranking",
            input=f"Reranking {len(combined_results)} results",
            metadata={
                "component": "reranker",
                "step": "3_reranking",
                "input_count": len(combined_results),
                "top_k": top_k
            }
        ) as span:
            try:
                reranked = await reranker.rerank(
                    query=search_query,
                    documents=combined_results,
                    top_k=top_k
                )

                reranking_time = time.perf_counter() - start_time

                span.update(
                    output=f"Reranked to {len(reranked)} results",
                    metadata={
                        "output_count": len(reranked),
                        "reranking_time": reranking_time
                    }
                )

                return reranked, reranking_time

            except Exception as e:
                span.update(output=f"Reranking failed: {e}", level="WARNING")
                logger.warning(f"Reranking failed, using original order: {e}")
                return combined_results[:top_k], time.perf_counter() - start_time
    else:
        try:
            reranked = await reranker.rerank(
                query=search_query,
                documents=combined_results,
                top_k=top_k
            )
            return reranked, time.perf_counter() - start_time

        except Exception as e:
            logger.warning(f"Reranking failed, using original order: {e}")
            return combined_results[:top_k], time.perf_counter() - start_time


async def generate_response(
    generator,
    search_query: str,
    reranked_results: List[Dict[str, Any]],
    language: str,
    difficulty_level: str,
    conversation_type: str = "start"
) -> Optional[str]:
    """
    Generate LLM response with optional tracing.

    Args:
        generator: The response generator instance
        search_query: The search query
        reranked_results: Reranked context results
        language: Response language
        difficulty_level: Difficulty level for response
        conversation_type: "start" or "continue"

    Returns:
        Generated response or None if failed
    """
    if not generator:
        return None

    if is_langfuse_enabled():
        langfuse_client = get_langfuse_client()
        with langfuse_client.start_as_current_span(
            name="response_generation",
            input=search_query,
            metadata={
                "component": "response_generator",
                "step": "4_generation",
                "language": language,
                "difficulty": difficulty_level,
                "conversation_type": conversation_type,
                "context_items": len(reranked_results)
            }
        ) as span:
            try:
                response = await generator.generate_response(
                    query=search_query,
                    reranked_results=reranked_results,
                    language=language,
                    difficulty_level=difficulty_level,
                    conversation_type=conversation_type
                )

                span.update(
                    output=response[:200] if response else "No response generated",
                    metadata={
                        "success": bool(response),
                        "response_length": len(response) if response else 0
                    }
                )

                return response

            except Exception as e:
                span.update(output=f"Generation failed: {e}", level="ERROR")
                logger.error(f"Response generation failed: {e}")
                return None
    else:
        try:
            return await generator.generate_response(
                query=search_query,
                reranked_results=reranked_results,
                language=language,
                difficulty_level=difficulty_level,
                conversation_type=conversation_type
            )
        except Exception as e:
            logger.error(f"Response generation failed: {e}")
            return None


def combine_results_for_reranking(
    chunks: List[Dict[str, Any]],
    summaries: List[Dict[str, Any]],
    graph_data: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Combine results from multiple sources for reranking.

    Args:
        chunks: Chunk results from Milvus
        summaries: Summary results from Milvus
        graph_data: Graph data from GraphRAG

    Returns:
        Combined list of results
    """
    combined = []

    # Add chunks
    for chunk in (chunks or []):
        if "source" not in chunk:
            chunk["source"] = "chunk"
        combined.append(chunk)

    # Add summaries
    for summary in (summaries or []):
        if "source" not in summary:
            summary["source"] = "summary"
        combined.append(summary)

    # Add graph data
    for graph in (graph_data or []):
        if "source" not in graph:
            graph["source"] = "graph"
        combined.append(graph)

    return combined
