"""
TruLens Evaluation Service with Asynchronous Processing

Provides interpretable, expandable RAG evaluation with:
- Async evaluation (zero latency impact on response time)
- Custom climate-specific feedback functions
- Integration with Langfuse for unified observability
- GDPR-compliant consent checking
"""

import asyncio
import logging
import random
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
from contextvars import ContextVar
from enum import Enum

logger = logging.getLogger(__name__)

# Context variable for evaluation consent
_evaluation_consent: ContextVar[bool] = ContextVar('evaluation_consent', default=True)

# Global TruLens instances
_trulens_session = None
_trulens_enabled = False
_evaluation_queue: deque = deque(maxlen=1000)
_background_worker_task = None


class EvaluationStatus(Enum):
    """Status of an evaluation record."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class EvaluationRecord:
    """Record for async evaluation."""
    id: str
    query: str
    response: str
    context_chunks: List[Dict[str, Any]]
    context_summaries: List[Dict[str, Any]]
    context_graph: List[Dict[str, Any]]
    social_tipping_point: str
    session_id: str
    conversation_type: str
    timestamp: datetime
    status: EvaluationStatus = EvaluationStatus.PENDING
    scores: Dict[str, float] = field(default_factory=dict)
    explanations: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    langfuse_trace_id: Optional[str] = None
    processing_time: float = 0.0
    error_message: Optional[str] = None


@dataclass
class EvaluationResult:
    """Result of TruLens evaluation with interpretability."""
    record_id: str
    scores: Dict[str, float]
    explanations: Dict[str, str]
    overall_score: float
    passed_thresholds: bool
    alerts: List[str]
    processing_time: float
    timestamp: datetime


class TruLensService:
    """
    Async TruLens evaluation service with interpretability and expandability.

    Features:
    - Zero latency impact (async evaluation after response)
    - Chain-of-thought explanations for each score
    - Custom climate domain feedback functions
    - Langfuse integration for unified dashboard
    - Configurable sampling rate
    """

    def __init__(self):
        self.session = None
        self.is_enabled = False
        self.is_initialized = False
        self.provider = None
        self.feedbacks = {}
        self.evaluation_queue = deque(maxlen=1000)
        self.worker_task = None
        self.stats = {
            "total_evaluations": 0,
            "completed_evaluations": 0,
            "failed_evaluations": 0,
            "skipped_evaluations": 0,
            "avg_groundedness": 0.0,
            "avg_relevance": 0.0,
            "avg_context_relevance": 0.0,
            "avg_climate_accuracy": 0.0,
            "alerts_triggered": 0,
            "queue_size": 0
        }

    async def initialize(self):
        """Initialize TruLens service with configured provider."""
        try:
            from app.config import get_settings
            settings = get_settings()

            if not settings.TRULENS_ENABLED:
                logger.info("TruLens evaluation service disabled")
                self.is_enabled = False
                return

            if not settings.trulens_is_configured:
                logger.warning("TruLens not properly configured - evaluation disabled")
                self.is_enabled = False
                return

            # Initialize TruLens session
            await self._initialize_session(settings)

            # Initialize evaluation provider
            await self._initialize_provider(settings)

            # Initialize feedback functions
            await self._initialize_feedbacks(settings)

            # Start background worker if async mode is enabled
            if settings.TRULENS_ASYNC_MODE:
                self.worker_task = asyncio.create_task(
                    self._background_evaluation_worker(settings)
                )
                logger.info("TruLens async background worker started")

            self.is_enabled = True
            self.is_initialized = True
            logger.info(f"TruLens evaluation service initialized (provider: {settings.TRULENS_PROVIDER})")

        except ImportError as e:
            logger.warning(f"TruLens not installed: {e}. Install with: pip install trulens-eval")
            self.is_enabled = False
        except Exception as e:
            logger.error(f"Failed to initialize TruLens service: {e}")
            self.is_enabled = False

    async def _initialize_session(self, settings):
        """Initialize TruLens session with database."""
        try:
            from trulens.core import TruSession

            self.session = TruSession(
                database_url=settings.trulens_database_path
            )
            logger.info(f"TruLens session initialized with database: {settings.trulens_database_path}")

        except ImportError:
            # Fallback for older TruLens versions
            try:
                from trulens_eval import Tru
                self.session = Tru(database_url=settings.trulens_database_path)
                logger.info("TruLens session initialized (legacy API)")
            except ImportError as e:
                raise ImportError(f"TruLens not available: {e}")

    async def _initialize_provider(self, settings):
        """Initialize the LLM provider for evaluations."""
        provider_type = settings.TRULENS_PROVIDER.lower()

        try:
            if provider_type == "ollama":
                from trulens.providers.litellm import LiteLLM
                self.provider = LiteLLM(
                    model_engine=f"ollama/{settings.TRULENS_EVAL_MODEL}"
                )
                logger.info(f"TruLens using Ollama provider: {settings.TRULENS_EVAL_MODEL}")

            elif provider_type == "openai":
                from trulens.providers.openai import OpenAI
                self.provider = OpenAI(
                    model_engine=settings.TRULENS_EVAL_MODEL or "gpt-4o-mini",
                    api_key=settings.TRULENS_OPENAI_API_KEY
                )
                logger.info(f"TruLens using OpenAI provider: {settings.TRULENS_EVAL_MODEL}")

            elif provider_type == "litellm":
                from trulens.providers.litellm import LiteLLM
                self.provider = LiteLLM(
                    model_engine=settings.TRULENS_EVAL_MODEL
                )
                logger.info(f"TruLens using LiteLLM provider: {settings.TRULENS_EVAL_MODEL}")

            else:
                raise ValueError(f"Unknown TruLens provider: {provider_type}")

        except ImportError as e:
            logger.warning(f"Provider import failed: {e}. Using fallback.")
            # Fallback to basic provider
            try:
                from trulens_eval.feedback.provider import OpenAI as LegacyOpenAI
                self.provider = LegacyOpenAI()
            except:
                self.provider = None

    async def _initialize_feedbacks(self, settings):
        """Initialize feedback functions based on configuration."""
        if not self.provider:
            logger.warning("No provider available - feedback functions disabled")
            return

        try:
            from trulens.core import Feedback
            from trulens.feedback import Groundedness

            # Standard RAG metrics
            if settings.TRULENS_EVAL_GROUNDEDNESS:
                self.feedbacks["groundedness"] = self._create_groundedness_feedback()

            if settings.TRULENS_EVAL_RELEVANCE:
                self.feedbacks["answer_relevance"] = self._create_relevance_feedback()

            if settings.TRULENS_EVAL_CONTEXT_RELEVANCE:
                self.feedbacks["context_relevance"] = self._create_context_relevance_feedback()

            if settings.TRULENS_EVAL_COHERENCE:
                self.feedbacks["coherence"] = self._create_coherence_feedback()

            # Custom climate-specific metrics
            if settings.TRULENS_EVAL_CLIMATE_ACCURACY:
                self.feedbacks["climate_accuracy"] = self._create_climate_accuracy_feedback()

            if settings.TRULENS_EVAL_STP_RELEVANCE:
                self.feedbacks["stp_relevance"] = self._create_stp_relevance_feedback()

            logger.info(f"Initialized {len(self.feedbacks)} feedback functions: {list(self.feedbacks.keys())}")

        except ImportError as e:
            logger.warning(f"Could not initialize feedback functions: {e}")

    def _create_groundedness_feedback(self) -> Callable:
        """
        Create groundedness feedback function.

        Evaluates: Is the response supported by the retrieved context?
        Interpretability: Shows which statements are/aren't grounded.
        """
        async def evaluate_groundedness(query: str, response: str, context: str) -> Dict[str, Any]:
            try:
                prompt = f"""Evaluate if the response is grounded in the provided context.

CONTEXT:
{context[:4000]}

RESPONSE:
{response}

For each claim in the response, determine if it is:
1. SUPPORTED - directly stated or strongly implied by context
2. PARTIALLY_SUPPORTED - related info exists but claim extends beyond it
3. NOT_SUPPORTED - no evidence in context (potential hallucination)

Provide your evaluation as:
- Overall score (0.0-1.0)
- List each major claim with its support status
- Explanation of reasoning

Format:
SCORE: [0.0-1.0]
CLAIMS:
- "[claim]": [SUPPORTED/PARTIALLY_SUPPORTED/NOT_SUPPORTED] - [reason]
EXPLANATION: [overall reasoning]"""

                result = await self._call_provider(prompt)
                score, explanation = self._parse_evaluation_result(result, "groundedness")

                return {
                    "score": score,
                    "explanation": explanation,
                    "raw_response": result[:500]
                }

            except Exception as e:
                logger.error(f"Groundedness evaluation failed: {e}")
                return {"score": 0.5, "explanation": f"Evaluation failed: {str(e)}", "error": True}

        return evaluate_groundedness

    def _create_relevance_feedback(self) -> Callable:
        """
        Create answer relevance feedback function.

        Evaluates: Does the response actually answer the question?
        Interpretability: Shows alignment between question intent and response.
        """
        async def evaluate_relevance(query: str, response: str, context: str = None) -> Dict[str, Any]:
            try:
                prompt = f"""Evaluate if the response directly answers the user's question.

QUESTION:
{query}

RESPONSE:
{response}

Evaluate:
1. Does the response address the main question?
2. Is the response focused or does it go off-topic?
3. Are all parts of the question answered?

Format:
SCORE: [0.0-1.0]
QUESTION_ADDRESSED: [YES/PARTIALLY/NO]
FOCUS_LEVEL: [HIGH/MEDIUM/LOW]
MISSING_ASPECTS: [list any unanswered parts]
EXPLANATION: [reasoning]"""

                result = await self._call_provider(prompt)
                score, explanation = self._parse_evaluation_result(result, "relevance")

                return {
                    "score": score,
                    "explanation": explanation,
                    "raw_response": result[:500]
                }

            except Exception as e:
                logger.error(f"Relevance evaluation failed: {e}")
                return {"score": 0.5, "explanation": f"Evaluation failed: {str(e)}", "error": True}

        return evaluate_relevance

    def _create_context_relevance_feedback(self) -> Callable:
        """
        Create context relevance feedback function.

        Evaluates: Are the retrieved documents actually useful for the query?
        Interpretability: Shows relevance of each context chunk.
        """
        async def evaluate_context_relevance(query: str, response: str, context: str) -> Dict[str, Any]:
            try:
                prompt = f"""Evaluate if the retrieved context is relevant to the user's question.

QUESTION:
{query}

RETRIEVED CONTEXT:
{context[:3000]}

For each chunk of context, evaluate:
1. Is it relevant to the question?
2. Does it contain useful information?
3. Is it used in the response?

Format:
SCORE: [0.0-1.0]
RELEVANT_CHUNKS: [count of relevant chunks]
TOTAL_CHUNKS: [total chunks]
UNUSED_BUT_RELEVANT: [count]
IRRELEVANT: [count]
EXPLANATION: [reasoning about retrieval quality]"""

                result = await self._call_provider(prompt)
                score, explanation = self._parse_evaluation_result(result, "context_relevance")

                return {
                    "score": score,
                    "explanation": explanation,
                    "raw_response": result[:500]
                }

            except Exception as e:
                logger.error(f"Context relevance evaluation failed: {e}")
                return {"score": 0.5, "explanation": f"Evaluation failed: {str(e)}", "error": True}

        return evaluate_context_relevance

    def _create_coherence_feedback(self) -> Callable:
        """Create response coherence feedback function."""
        async def evaluate_coherence(query: str, response: str, context: str = None) -> Dict[str, Any]:
            try:
                prompt = f"""Evaluate the coherence and structure of this response.

RESPONSE:
{response}

Evaluate:
1. Is the response well-organized?
2. Does it flow logically?
3. Is the language clear and professional?

Format:
SCORE: [0.0-1.0]
ORGANIZATION: [GOOD/FAIR/POOR]
LOGICAL_FLOW: [GOOD/FAIR/POOR]
CLARITY: [GOOD/FAIR/POOR]
EXPLANATION: [reasoning]"""

                result = await self._call_provider(prompt)
                score, explanation = self._parse_evaluation_result(result, "coherence")

                return {
                    "score": score,
                    "explanation": explanation,
                    "raw_response": result[:500]
                }

            except Exception as e:
                logger.error(f"Coherence evaluation failed: {e}")
                return {"score": 0.5, "explanation": f"Evaluation failed: {str(e)}", "error": True}

        return evaluate_coherence

    def _create_climate_accuracy_feedback(self) -> Callable:
        """
        Create climate-specific accuracy feedback function.

        CUSTOM for NeuroClima: Evaluates climate science accuracy.
        Expandable: Add more domain-specific checks here.
        """
        async def evaluate_climate_accuracy(query: str, response: str, context: str) -> Dict[str, Any]:
            try:
                prompt = f"""As a climate science expert, evaluate the accuracy of this climate-related response.

QUESTION:
{query}

RESPONSE:
{response}

CONTEXT (from knowledge base):
{context[:3000]}

Evaluate for climate-specific accuracy:
1. Are scientific claims accurate and up-to-date?
2. Are statistics and figures correctly cited?
3. Are climate policies correctly described?
4. Are EU climate regulations accurately referenced?
5. Are any common climate misconceptions present?

Format:
SCORE: [0.0-1.0]
SCIENTIFIC_ACCURACY: [HIGH/MEDIUM/LOW]
POLICY_ACCURACY: [HIGH/MEDIUM/LOW/NA]
POTENTIAL_ERRORS:
- [list any inaccuracies or concerns]
STRENGTHS:
- [list accurate/well-explained points]
EXPLANATION: [detailed reasoning about climate accuracy]"""

                result = await self._call_provider(prompt)
                score, explanation = self._parse_evaluation_result(result, "climate_accuracy")

                return {
                    "score": score,
                    "explanation": explanation,
                    "raw_response": result[:500]
                }

            except Exception as e:
                logger.error(f"Climate accuracy evaluation failed: {e}")
                return {"score": 0.5, "explanation": f"Evaluation failed: {str(e)}", "error": True}

        return evaluate_climate_accuracy

    def _create_stp_relevance_feedback(self) -> Callable:
        """
        Create Social Tipping Point relevance feedback function.

        CUSTOM for NeuroClima: Evaluates if STP is relevant to response.
        Expandable: Add more STP-specific evaluation criteria.
        """
        async def evaluate_stp_relevance(
            query: str, response: str, context: str, stp: str
        ) -> Dict[str, Any]:
            try:
                if not stp or stp == "No specific social tipping point available for this query.":
                    return {
                        "score": 1.0,  # N/A is acceptable
                        "explanation": "No STP was provided, which is appropriate when no relevant STP exists.",
                        "raw_response": "N/A - No STP to evaluate"
                    }

                prompt = f"""Evaluate if the Social Tipping Point (STP) is relevant to the response and question.

QUESTION:
{query}

RESPONSE:
{response}

SOCIAL TIPPING POINT PROVIDED:
{stp}

Evaluate:
1. Is the STP thematically related to the question/response?
2. Does the STP add value to understanding climate action?
3. Is the STP accurately described?
4. Would a different STP be more appropriate?

Format:
SCORE: [0.0-1.0]
THEMATIC_RELEVANCE: [HIGH/MEDIUM/LOW/NONE]
VALUE_ADDED: [YES/PARTIAL/NO]
STP_ACCURACY: [ACCURATE/UNCLEAR/INACCURATE]
EXPLANATION: [reasoning about STP relevance and accuracy]"""

                result = await self._call_provider(prompt)
                score, explanation = self._parse_evaluation_result(result, "stp_relevance")

                return {
                    "score": score,
                    "explanation": explanation,
                    "raw_response": result[:500]
                }

            except Exception as e:
                logger.error(f"STP relevance evaluation failed: {e}")
                return {"score": 0.5, "explanation": f"Evaluation failed: {str(e)}", "error": True}

        return evaluate_stp_relevance

    async def _call_provider(self, prompt: str) -> str:
        """Call the evaluation provider with a prompt."""
        if not self.provider:
            raise ValueError("No evaluation provider configured")

        try:
            # Try new TruLens API
            if hasattr(self.provider, 'generate'):
                return await asyncio.to_thread(self.provider.generate, prompt)
            elif hasattr(self.provider, 'complete'):
                return await asyncio.to_thread(self.provider.complete, prompt)
            elif hasattr(self.provider, '__call__'):
                return await asyncio.to_thread(self.provider, prompt)
            else:
                # Fallback to direct LLM call
                from app.services.llm.factory import get_llm
                llm = await get_llm()
                return await asyncio.to_thread(llm, prompt)

        except Exception as e:
            logger.error(f"Provider call failed: {e}")
            raise

    def _parse_evaluation_result(self, result: str, metric_name: str) -> tuple:
        """Parse evaluation result to extract score and explanation."""
        try:
            lines = result.strip().split('\n')
            score = 0.5
            explanation = result

            for line in lines:
                line_lower = line.lower().strip()
                if line_lower.startswith('score:'):
                    try:
                        score_str = line.split(':')[1].strip()
                        # Handle formats like "0.85" or "0.85/1.0" or "85%"
                        if '/' in score_str:
                            score_str = score_str.split('/')[0]
                        if '%' in score_str:
                            score = float(score_str.replace('%', '')) / 100
                        else:
                            score = float(score_str)
                        score = max(0.0, min(1.0, score))  # Clamp to 0-1
                    except ValueError:
                        pass
                elif line_lower.startswith('explanation:'):
                    explanation = ':'.join(line.split(':')[1:]).strip()

            return score, explanation

        except Exception as e:
            logger.warning(f"Failed to parse {metric_name} result: {e}")
            return 0.5, f"Parse error: {str(e)}"

    async def queue_evaluation(
        self,
        query: str,
        response: str,
        context_chunks: List[Dict[str, Any]],
        context_summaries: List[Dict[str, Any]],
        context_graph: List[Dict[str, Any]],
        social_tipping_point: str,
        session_id: str,
        conversation_type: str = "continue",
        langfuse_trace_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Queue a response for async evaluation.

        Returns immediately with a record ID. Evaluation happens in background.
        This is the main entry point - NO LATENCY IMPACT on response time.
        """
        if not self.is_enabled:
            return None

        # Check consent
        if not get_evaluation_consent():
            logger.debug("Evaluation skipped - user declined consent")
            return None

        # Apply sampling rate
        from app.config import get_settings
        settings = get_settings()

        if random.random() > settings.TRULENS_SAMPLE_RATE:
            self.stats["skipped_evaluations"] += 1
            logger.debug(f"Evaluation skipped due to sampling (rate: {settings.TRULENS_SAMPLE_RATE})")
            return None

        # Create evaluation record
        record_id = f"eval_{session_id}_{int(time.time() * 1000)}"

        record = EvaluationRecord(
            id=record_id,
            query=query,
            response=response,
            context_chunks=context_chunks,
            context_summaries=context_summaries,
            context_graph=context_graph,
            social_tipping_point=social_tipping_point,
            session_id=session_id,
            conversation_type=conversation_type,
            timestamp=datetime.utcnow(),
            langfuse_trace_id=langfuse_trace_id,
            metadata=metadata or {}
        )

        # Add to queue (non-blocking)
        self.evaluation_queue.append(record)
        self.stats["total_evaluations"] += 1
        self.stats["queue_size"] = len(self.evaluation_queue)

        logger.info(f"Queued evaluation {record_id} (queue size: {len(self.evaluation_queue)})")
        return record_id

    async def _background_evaluation_worker(self, settings):
        """
        Background worker that processes evaluation queue.

        Runs continuously, processing pending evaluations without blocking main app.
        """
        logger.info("TruLens background evaluation worker started")

        while True:
            try:
                await asyncio.sleep(settings.TRULENS_WORKER_INTERVAL)

                # Process batch of pending evaluations
                processed = 0
                while self.evaluation_queue and processed < settings.TRULENS_BATCH_SIZE:
                    record = self.evaluation_queue.popleft()

                    try:
                        result = await self._evaluate_record(record, settings)

                        # Push scores to Langfuse if enabled
                        if settings.TRULENS_PUSH_TO_LANGFUSE and record.langfuse_trace_id:
                            await self._push_scores_to_langfuse(record, result)

                        self.stats["completed_evaluations"] += 1
                        processed += 1

                    except Exception as e:
                        logger.error(f"Evaluation failed for {record.id}: {e}")
                        record.status = EvaluationStatus.FAILED
                        record.error_message = str(e)
                        self.stats["failed_evaluations"] += 1

                self.stats["queue_size"] = len(self.evaluation_queue)

                if processed > 0:
                    logger.info(f"Processed {processed} evaluations (remaining: {len(self.evaluation_queue)})")

            except asyncio.CancelledError:
                logger.info("TruLens background worker cancelled")
                break
            except Exception as e:
                logger.error(f"Background worker error: {e}")
                await asyncio.sleep(5)  # Brief pause before retry

    async def _evaluate_record(self, record: EvaluationRecord, settings) -> EvaluationResult:
        """
        Perform full evaluation on a record.

        Returns detailed result with scores, explanations, and alerts.
        """
        start_time = time.perf_counter()
        record.status = EvaluationStatus.IN_PROGRESS

        # Build context string from all sources
        context = self._build_context_string(
            record.context_chunks,
            record.context_summaries,
            record.context_graph
        )

        scores = {}
        explanations = {}
        alerts = []

        # Run all configured evaluations
        for metric_name, feedback_fn in self.feedbacks.items():
            try:
                if metric_name == "stp_relevance":
                    result = await feedback_fn(
                        record.query, record.response, context, record.social_tipping_point
                    )
                else:
                    result = await feedback_fn(record.query, record.response, context)

                scores[metric_name] = result.get("score", 0.5)
                explanations[metric_name] = result.get("explanation", "No explanation")

                # Check thresholds and generate alerts
                if settings.TRULENS_ALERT_ON_LOW_SCORE:
                    if metric_name == "groundedness" and scores[metric_name] < settings.TRULENS_GROUNDEDNESS_THRESHOLD:
                        alerts.append(f"Low groundedness: {scores[metric_name]:.2f} (threshold: {settings.TRULENS_GROUNDEDNESS_THRESHOLD})")
                    elif metric_name == "answer_relevance" and scores[metric_name] < settings.TRULENS_RELEVANCE_THRESHOLD:
                        alerts.append(f"Low relevance: {scores[metric_name]:.2f} (threshold: {settings.TRULENS_RELEVANCE_THRESHOLD})")

            except Exception as e:
                logger.error(f"Evaluation failed for {metric_name}: {e}")
                scores[metric_name] = 0.5
                explanations[metric_name] = f"Evaluation error: {str(e)}"

        # Calculate overall score
        if scores:
            overall_score = sum(scores.values()) / len(scores)
        else:
            overall_score = 0.5

        # Check if all thresholds passed
        passed_thresholds = len(alerts) == 0

        processing_time = time.perf_counter() - start_time

        # Update record
        record.status = EvaluationStatus.COMPLETED
        record.scores = scores
        record.explanations = explanations
        record.processing_time = processing_time

        # Update stats
        self._update_stats(scores)
        if alerts:
            self.stats["alerts_triggered"] += len(alerts)
            for alert in alerts:
                logger.warning(f"TruLens Alert [{record.id}]: {alert}")

        logger.info(
            f"Evaluation {record.id} completed in {processing_time:.2f}s - "
            f"Overall: {overall_score:.2f}, Passed: {passed_thresholds}"
        )

        return EvaluationResult(
            record_id=record.id,
            scores=scores,
            explanations=explanations,
            overall_score=overall_score,
            passed_thresholds=passed_thresholds,
            alerts=alerts,
            processing_time=processing_time,
            timestamp=datetime.utcnow()
        )

    def _build_context_string(
        self,
        chunks: List[Dict],
        summaries: List[Dict],
        graph_data: List[Dict]
    ) -> str:
        """Build a unified context string from all sources."""
        context_parts = []

        for i, chunk in enumerate(chunks[:5]):
            content = chunk.get("content") or chunk.get("text", "")
            doc_name = chunk.get("doc_name", "Unknown")
            context_parts.append(f"[Chunk {i+1} from {doc_name}]:\n{content[:500]}")

        for i, summary in enumerate(summaries[:3]):
            content = summary.get("summary") or summary.get("content", "")
            doc_name = summary.get("doc_name", "Unknown")
            context_parts.append(f"[Summary {i+1} from {doc_name}]:\n{content[:500]}")

        for i, graph_item in enumerate(graph_data[:3]):
            content = graph_item.get("content", "")
            entities = graph_item.get("entities", [])
            context_parts.append(f"[Graph {i+1} - Entities: {entities[:5]}]:\n{content[:500]}")

        return "\n\n".join(context_parts)

    def _update_stats(self, scores: Dict[str, float]):
        """Update running average statistics."""
        n = self.stats["completed_evaluations"]

        for metric, score in scores.items():
            stat_key = f"avg_{metric}"
            if stat_key in self.stats:
                current_avg = self.stats[stat_key]
                self.stats[stat_key] = (current_avg * (n - 1) + score) / n if n > 0 else score

    async def _push_scores_to_langfuse(self, record: EvaluationRecord, result: EvaluationResult):
        """Push TruLens scores to Langfuse trace for unified dashboard."""
        try:
            from app.services.tracing import get_langfuse_client, is_langfuse_enabled

            if not is_langfuse_enabled():
                return

            client = get_langfuse_client()
            if not client:
                return

            # Create scores in Langfuse
            for metric_name, score in result.scores.items():
                try:
                    client.score(
                        trace_id=record.langfuse_trace_id,
                        name=f"trulens_{metric_name}",
                        value=score,
                        comment=result.explanations.get(metric_name, "")[:500]
                    )
                except Exception as e:
                    logger.warning(f"Failed to push {metric_name} to Langfuse: {e}")

            # Push overall score
            client.score(
                trace_id=record.langfuse_trace_id,
                name="trulens_overall",
                value=result.overall_score,
                comment=f"Passed thresholds: {result.passed_thresholds}, Alerts: {len(result.alerts)}"
            )

            client.flush()
            logger.debug(f"Pushed TruLens scores to Langfuse trace {record.langfuse_trace_id}")

        except Exception as e:
            logger.warning(f"Failed to push scores to Langfuse: {e}")

    async def get_evaluation_result(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Get evaluation result by record ID (for API/dashboard)."""
        # In a real implementation, this would query the TruLens database
        # For now, return from session if available
        try:
            if self.session:
                # Query TruLens database
                pass
            return None
        except Exception as e:
            logger.error(f"Failed to get evaluation result: {e}")
            return None

    async def get_stats(self) -> Dict[str, Any]:
        """Get evaluation statistics."""
        return {
            "enabled": self.is_enabled,
            "initialized": self.is_initialized,
            "feedbacks_configured": list(self.feedbacks.keys()),
            **self.stats
        }

    async def health_check(self) -> Dict[str, Any]:
        """Health check for TruLens service."""
        return {
            "status": "healthy" if self.is_enabled and self.is_initialized else "disabled",
            "enabled": self.is_enabled,
            "initialized": self.is_initialized,
            "provider": str(type(self.provider).__name__) if self.provider else None,
            "feedbacks": list(self.feedbacks.keys()),
            "queue_size": len(self.evaluation_queue),
            "worker_running": self.worker_task is not None and not self.worker_task.done()
        }

    async def shutdown(self):
        """Shutdown TruLens service gracefully."""
        logger.info("Shutting down TruLens service...")

        # Cancel background worker
        if self.worker_task and not self.worker_task.done():
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass

        # Process remaining queue items
        remaining = len(self.evaluation_queue)
        if remaining > 0:
            logger.warning(f"TruLens shutdown with {remaining} pending evaluations")

        logger.info("TruLens service shut down")


# Global service instance
trulens_service = TruLensService()


async def get_trulens_service() -> TruLensService:
    """Get the TruLens service instance."""
    if not trulens_service.is_initialized:
        await trulens_service.initialize()
    return trulens_service


def is_trulens_enabled() -> bool:
    """Check if TruLens evaluation is enabled."""
    try:
        from app.config import get_settings
        settings = get_settings()

        if not settings.TRULENS_ENABLED:
            return False

        if not settings.trulens_is_configured:
            return False

        # Check user consent
        if not get_evaluation_consent():
            return False

        return trulens_service.is_enabled

    except Exception:
        return False


def set_evaluation_consent(consent: bool):
    """Set evaluation consent for current request context."""
    _evaluation_consent.set(consent)


def get_evaluation_consent() -> bool:
    """Get evaluation consent from current request context."""
    return _evaluation_consent.get()


# Convenience function for RAG chain integration
async def queue_rag_evaluation(
    query: str,
    response: str,
    context_chunks: List[Dict[str, Any]],
    context_summaries: List[Dict[str, Any]],
    context_graph: List[Dict[str, Any]],
    social_tipping_point: str,
    session_id: str,
    conversation_type: str = "continue",
    langfuse_trace_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Optional[str]:
    """
    Convenience function to queue RAG response for evaluation.

    Call this AFTER returning response to user for zero latency impact.
    Returns record_id for tracking (or None if evaluation is disabled/skipped).
    """
    if not is_trulens_enabled():
        return None

    service = await get_trulens_service()
    return await service.queue_evaluation(
        query=query,
        response=response,
        context_chunks=context_chunks,
        context_summaries=context_summaries,
        context_graph=context_graph,
        social_tipping_point=social_tipping_point,
        session_id=session_id,
        conversation_type=conversation_type,
        langfuse_trace_id=langfuse_trace_id,
        metadata=metadata
    )
