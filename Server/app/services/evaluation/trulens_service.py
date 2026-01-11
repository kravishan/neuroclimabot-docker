"""
TruLens Evaluation Service for RAG Application
Provides real-time evaluation using the RAG Triad:
1. Context Relevance - Are retrieved chunks relevant to the query?
2. Groundedness - Is the answer supported by the retrieved context?
3. Answer Relevance - Does the answer address the question?
"""

import os
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
import asyncio

from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


@dataclass
class EvaluationScores:
    """TruLens evaluation scores for a RAG response."""
    context_relevance: float  # 0-1: How relevant are retrieved contexts to query
    groundedness: float  # 0-1: How well is answer supported by context (hallucination check)
    answer_relevance: float  # 0-1: How well does answer address the query
    overall_score: float  # Average of the three scores

    # Per-source breakdown
    milvus_context_relevance: Optional[float] = None
    graphrag_context_relevance: Optional[float] = None

    # Metadata
    evaluation_time: float = 0.0
    model_used: str = "gpt-4"


class TruLensService:
    """
    TruLens evaluation service for NeuroClimaBot RAG system.

    Features:
    - Real-time evaluation of RAG responses
    - Multi-source context relevance tracking (Milvus vs GraphRAG)
    - Hallucination detection via groundedness scoring
    - Dashboard for monitoring evaluation trends
    - Integration with existing Langfuse tracing
    """

    def __init__(self):
        self.tru = None
        self.feedback_provider = None
        self.is_initialized = False
        self.db_path = settings.TRULENS_DB_PATH
        self.groundedness_threshold = settings.TRULENS_GROUNDEDNESS_THRESHOLD

        # Performance tracking
        self.stats = {
            "total_evaluations": 0,
            "avg_context_relevance": 0.0,
            "avg_groundedness": 0.0,
            "avg_answer_relevance": 0.0,
            "low_groundedness_count": 0,  # Potential hallucinations
        }

    async def initialize(self):
        """Initialize TruLens with feedback providers."""
        try:
            from trulens_eval import Tru, Feedback, TruCustomApp
            from trulens_eval.feedback.provider import OpenAI as TruLensOpenAI

            # Initialize TruLens database
            self.tru = Tru(database_url=f"sqlite:///{self.db_path}")

            # Initialize feedback provider (uses OpenAI by default)
            # Falls back to your Mixtral/Ollama if needed
            openai_api_key = settings.OPENAI_API_KEY if hasattr(settings, 'OPENAI_API_KEY') else None

            if openai_api_key:
                self.feedback_provider = TruLensOpenAI(api_key=openai_api_key)
                logger.info("TruLens initialized with OpenAI feedback provider")
            else:
                # Use a custom feedback provider with your local Mixtral/Ollama
                from app.services.evaluation.trulens_custom_provider import OllamaFeedbackProvider
                self.feedback_provider = OllamaFeedbackProvider()
                logger.info("TruLens initialized with Ollama/Mixtral feedback provider")

            self.is_initialized = True
            logger.info(f"✅ TruLens service initialized (DB: {self.db_path})")

        except ImportError as e:
            logger.error(f"TruLens not installed: {e}")
            logger.info("Install with: pip install trulens-eval")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize TruLens: {e}")
            raise

    async def evaluate_rag_response(
        self,
        query: str,
        retrieved_contexts: List[str],
        generated_answer: str,
        milvus_contexts: Optional[List[str]] = None,
        graphrag_contexts: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> EvaluationScores:
        """
        Evaluate a RAG response using the TruLens RAG Triad.

        Args:
            query: Original user query
            retrieved_contexts: All retrieved context chunks (combined)
            generated_answer: Final generated response
            milvus_contexts: Contexts from Milvus (for per-source analysis)
            graphrag_contexts: Contexts from GraphRAG (for per-source analysis)
            metadata: Additional metadata for tracking

        Returns:
            EvaluationScores with all three RAG Triad metrics
        """
        if not self.is_initialized:
            await self.initialize()

        import time
        start_time = time.perf_counter()

        try:
            from trulens_eval import Feedback

            # Create feedback functions
            f_context_relevance = Feedback(
                self.feedback_provider.context_relevance,
                name="Context Relevance"
            ).on_input_output()

            f_groundedness = Feedback(
                self.feedback_provider.groundedness_measure_with_cot_reasons,
                name="Groundedness"
            ).on_input_output()

            f_answer_relevance = Feedback(
                self.feedback_provider.relevance,
                name="Answer Relevance"
            ).on_input_output()

            # Run evaluations in parallel for speed
            tasks = [
                self._evaluate_context_relevance(query, retrieved_contexts),
                self._evaluate_groundedness(retrieved_contexts, generated_answer),
                self._evaluate_answer_relevance(query, generated_answer)
            ]

            context_rel, groundedness, answer_rel = await asyncio.gather(*tasks)

            # Per-source context relevance
            milvus_rel = None
            graphrag_rel = None
            if milvus_contexts:
                milvus_rel = await self._evaluate_context_relevance(query, milvus_contexts)
            if graphrag_contexts:
                graphrag_rel = await self._evaluate_context_relevance(query, graphrag_contexts)

            # Calculate overall score
            overall = (context_rel + groundedness + answer_rel) / 3.0

            # Update stats
            self.stats["total_evaluations"] += 1
            self.stats["avg_context_relevance"] = (
                (self.stats["avg_context_relevance"] * (self.stats["total_evaluations"] - 1) + context_rel)
                / self.stats["total_evaluations"]
            )
            self.stats["avg_groundedness"] = (
                (self.stats["avg_groundedness"] * (self.stats["total_evaluations"] - 1) + groundedness)
                / self.stats["total_evaluations"]
            )
            self.stats["avg_answer_relevance"] = (
                (self.stats["avg_answer_relevance"] * (self.stats["total_evaluations"] - 1) + answer_rel)
                / self.stats["total_evaluations"]
            )

            # Track potential hallucinations (low groundedness)
            if groundedness < self.groundedness_threshold:
                self.stats["low_groundedness_count"] += 1
                logger.warning(
                    f"⚠️ Low groundedness detected: {groundedness:.2f} "
                    f"(threshold: {self.groundedness_threshold}, potential hallucination)"
                )

            eval_time = time.perf_counter() - start_time

            scores = EvaluationScores(
                context_relevance=context_rel,
                groundedness=groundedness,
                answer_relevance=answer_rel,
                overall_score=overall,
                milvus_context_relevance=milvus_rel,
                graphrag_context_relevance=graphrag_rel,
                evaluation_time=eval_time,
                model_used=self._get_model_name()
            )

            logger.info(
                f"📊 TruLens Scores: "
                f"Context={context_rel:.2f}, "
                f"Groundedness={groundedness:.2f}, "
                f"Answer={answer_rel:.2f}, "
                f"Overall={overall:.2f}"
            )

            return scores

        except Exception as e:
            logger.error(f"TruLens evaluation failed: {e}")
            # Return default scores on failure
            return EvaluationScores(
                context_relevance=0.0,
                groundedness=0.0,
                answer_relevance=0.0,
                overall_score=0.0,
                evaluation_time=time.perf_counter() - start_time,
                model_used="error"
            )

    async def _evaluate_context_relevance(self, query: str, contexts: List[str]) -> float:
        """Evaluate how relevant retrieved contexts are to the query."""
        try:
            # TruLens context relevance scoring
            combined_context = "\n\n".join(contexts[:10])  # Limit to top 10 for speed
            score = await asyncio.to_thread(
                self.feedback_provider.context_relevance,
                query,
                combined_context
            )
            return float(score) if score is not None else 0.0
        except Exception as e:
            logger.error(f"Context relevance evaluation failed: {e}")
            return 0.0

    async def _evaluate_groundedness(self, contexts: List[str], answer: str) -> float:
        """
        Evaluate if the answer is grounded in the retrieved contexts.
        This is the hallucination detection metric.
        """
        try:
            combined_context = "\n\n".join(contexts)
            score = await asyncio.to_thread(
                self.feedback_provider.groundedness_measure_with_cot_reasons,
                combined_context,
                answer
            )
            return float(score) if score is not None else 0.0
        except Exception as e:
            logger.error(f"Groundedness evaluation failed: {e}")
            return 0.0

    async def _evaluate_answer_relevance(self, query: str, answer: str) -> float:
        """Evaluate if the answer addresses the query."""
        try:
            score = await asyncio.to_thread(
                self.feedback_provider.relevance,
                query,
                answer
            )
            return float(score) if score is not None else 0.0
        except Exception as e:
            logger.error(f"Answer relevance evaluation failed: {e}")
            return 0.0

    def _get_model_name(self) -> str:
        """Get the model name used for evaluation."""
        try:
            return self.feedback_provider.model_engine if hasattr(self.feedback_provider, 'model_engine') else "gpt-4"
        except:
            return "unknown"

    def get_statistics(self) -> Dict[str, Any]:
        """Get evaluation statistics."""
        return {
            **self.stats,
            "hallucination_rate": (
                self.stats["low_groundedness_count"] / self.stats["total_evaluations"]
                if self.stats["total_evaluations"] > 0 else 0.0
            )
        }

    async def create_rag_app_recorder(self, app_name: str = "NeuroClimaBot RAG"):
        """
        Create a TruLens app recorder to wrap your RAG application.
        This enables automatic tracking and dashboard visualization.

        Usage:
            recorder = await trulens_service.create_rag_app_recorder()
            with recorder as recording:
                result = await rag_service.query(question)
        """
        if not self.is_initialized:
            await self.initialize()

        try:
            from trulens_eval import TruCustomApp, Feedback, Select

            # Define feedback functions for automatic evaluation
            f_context_relevance = (
                Feedback(self.feedback_provider.context_relevance)
                .on_input()
                .on(Select.RecordCalls.retrieve.rets[:].collect())
                .aggregate(lambda x: sum(x) / len(x) if x else 0)
            )

            f_groundedness = (
                Feedback(self.feedback_provider.groundedness_measure_with_cot_reasons)
                .on(Select.RecordCalls.retrieve.rets.collect())
                .on_output()
            )

            f_answer_relevance = (
                Feedback(self.feedback_provider.relevance)
                .on_input()
                .on_output()
            )

            # Create app recorder
            # Note: You'll need to wrap your actual RAG app here
            # This is a placeholder structure
            feedbacks = [f_context_relevance, f_groundedness, f_answer_relevance]

            logger.info(f"✅ TruLens app recorder created: {app_name}")
            return {
                "feedbacks": feedbacks,
                "app_name": app_name,
                "tru": self.tru
            }

        except Exception as e:
            logger.error(f"Failed to create app recorder: {e}")
            raise

    def launch_dashboard(self, port: int = 8501):
        """
        Launch the TruLens dashboard for visualization.

        Run this in a separate process or terminal:
            from app.services.evaluation.trulens_service import get_trulens_service
            service = get_trulens_service()
            service.launch_dashboard()
        """
        try:
            logger.info(f"🚀 Launching TruLens dashboard on port {port}")
            logger.info(f"Dashboard URL: http://localhost:{port}")
            self.tru.run_dashboard(port=port)
        except Exception as e:
            logger.error(f"Failed to launch dashboard: {e}")
            raise


# Singleton instance
_trulens_service = None

async def get_trulens_service() -> TruLensService:
    """Get or create the TruLens service singleton."""
    global _trulens_service
    if _trulens_service is None:
        _trulens_service = TruLensService()
        await _trulens_service.initialize()
    return _trulens_service


def get_trulens_service_sync() -> TruLensService:
    """Get TruLens service synchronously (for non-async contexts)."""
    global _trulens_service
    if _trulens_service is None:
        _trulens_service = TruLensService()
    return _trulens_service
