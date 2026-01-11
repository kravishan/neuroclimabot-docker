"""
RAG Evaluator - Integrates TruLens with NeuroClimaBot RAG Pipeline
Provides seamless evaluation of RAG responses with minimal code changes.
"""

from typing import Any, Dict, List, Optional
import time
from dataclasses import asdict

from app.services.evaluation.trulens_service import get_trulens_service, EvaluationScores
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RAGEvaluator:
    """
    Wrapper for evaluating RAG responses using TruLens.

    Usage:
        evaluator = RAGEvaluator()
        await evaluator.initialize()

        # Evaluate a RAG response
        scores = await evaluator.evaluate_response(
            query=user_question,
            chunks=retrieved_chunks,
            summaries=retrieved_summaries,
            graph_data=retrieved_graph_data,
            generated_response=final_response
        )
    """

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.trulens_service = None
        self.is_initialized = False

    async def initialize(self):
        """Initialize the TruLens service."""
        if not self.enabled:
            logger.info("RAG evaluation disabled")
            return

        try:
            self.trulens_service = await get_trulens_service()
            self.is_initialized = True
            logger.info("✅ RAG evaluator initialized with TruLens")
        except Exception as e:
            logger.warning(f"Failed to initialize RAG evaluator: {e}")
            logger.info("Continuing without evaluation...")
            self.enabled = False

    async def evaluate_response(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        summaries: List[Dict[str, Any]],
        graph_data: List[Dict[str, Any]],
        generated_response: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[EvaluationScores]:
        """
        Evaluate a RAG response using TruLens RAG Triad.

        Args:
            query: User's original question
            chunks: Retrieved chunks from Milvus
            summaries: Retrieved summaries from Milvus
            graph_data: Retrieved data from GraphRAG
            generated_response: Final generated answer
            metadata: Additional metadata (session_id, language, etc.)

        Returns:
            EvaluationScores or None if evaluation is disabled/failed
        """
        if not self.enabled or not self.is_initialized:
            return None

        try:
            # Extract context texts from chunks
            chunk_contexts = [
                chunk.get("content", "") or chunk.get("text", "")
                for chunk in chunks
            ]

            # Extract context texts from summaries
            summary_contexts = [
                summary.get("content", "") or summary.get("text", "")
                for summary in summaries
            ]

            # Extract context texts from graph data
            graph_contexts = [
                item.get("content", "") or item.get("text", "") or str(item)
                for item in graph_data
            ]

            # Combine all contexts
            all_contexts = chunk_contexts + summary_contexts + graph_contexts

            # Evaluate using TruLens
            scores = await self.trulens_service.evaluate_rag_response(
                query=query,
                retrieved_contexts=all_contexts,
                generated_answer=generated_response,
                milvus_contexts=chunk_contexts + summary_contexts,
                graphrag_contexts=graph_contexts,
                metadata=metadata
            )

            return scores

        except Exception as e:
            logger.error(f"RAG evaluation failed: {e}")
            return None

    async def evaluate_from_rag_response(
        self,
        query: str,
        rag_response: Dict[str, Any]
    ) -> Optional[EvaluationScores]:
        """
        Evaluate a RAG response from your RAGOrchestrator result.

        Args:
            query: User query
            rag_response: Response dict from RAGOrchestrator

        Returns:
            EvaluationScores or None
        """
        if not self.enabled or not self.is_initialized:
            return None

        try:
            # Extract reference data
            reference_data = rag_response.get("reference_data", {})
            chunks = reference_data.get("chunks", [])
            summaries = reference_data.get("summaries", [])
            graph_data = reference_data.get("graph", [])

            # Extract generated content
            content = rag_response.get("content", "")

            return await self.evaluate_response(
                query=query,
                chunks=chunks,
                summaries=summaries,
                graph_data=graph_data,
                generated_response=content,
                metadata={
                    "has_relevant_data": rag_response.get("has_relevant_data", False),
                    "total_processing_time": rag_response.get("total_processing_time", 0),
                }
            )

        except Exception as e:
            logger.error(f"Evaluation from RAG response failed: {e}")
            return None

    def get_statistics(self) -> Dict[str, Any]:
        """Get evaluation statistics from TruLens."""
        if not self.is_initialized or not self.trulens_service:
            return {}

        return self.trulens_service.get_statistics()

    def add_scores_to_response(
        self,
        response: Dict[str, Any],
        scores: Optional[EvaluationScores]
    ) -> Dict[str, Any]:
        """
        Add evaluation scores to a RAG response dict.

        Args:
            response: RAG response dictionary
            scores: TruLens evaluation scores

        Returns:
            Response dict with added 'evaluation' field
        """
        if scores is None:
            return response

        response["evaluation"] = {
            "context_relevance": scores.context_relevance,
            "groundedness": scores.groundedness,
            "answer_relevance": scores.answer_relevance,
            "overall_score": scores.overall_score,
            "milvus_context_relevance": scores.milvus_context_relevance,
            "graphrag_context_relevance": scores.graphrag_context_relevance,
            "evaluation_time_ms": scores.evaluation_time * 1000,
            "model_used": scores.model_used
        }

        # Add quality flags
        response["quality_flags"] = self._generate_quality_flags(scores)

        return response

    def _generate_quality_flags(self, scores: EvaluationScores) -> Dict[str, bool]:
        """Generate quality flags based on scores."""
        return {
            "high_quality": scores.overall_score >= 0.8,
            "potential_hallucination": scores.groundedness < 0.7,
            "irrelevant_context": scores.context_relevance < 0.6,
            "off_topic_answer": scores.answer_relevance < 0.6,
            "excellent_response": (
                scores.context_relevance >= 0.8 and
                scores.groundedness >= 0.8 and
                scores.answer_relevance >= 0.8
            )
        }


# Singleton instance
_rag_evaluator = None


async def get_rag_evaluator(enabled: bool = True) -> RAGEvaluator:
    """Get or create the RAG evaluator singleton."""
    global _rag_evaluator
    if _rag_evaluator is None:
        _rag_evaluator = RAGEvaluator(enabled=enabled)
        await _rag_evaluator.initialize()
    return _rag_evaluator
