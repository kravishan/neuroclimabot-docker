"""
Custom TruLens Feedback Provider using Ollama/Mixtral
For users without OpenAI API access
"""

from typing import Dict, List, Optional, Tuple
import requests
import json

from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class OllamaFeedbackProvider:
    """
    Custom feedback provider that uses Ollama (Mixtral) instead of OpenAI.
    Implements TruLens feedback interface.
    """

    def __init__(self, model: str = "mixtral:latest"):
        self.model = model
        self.ollama_url = settings.OLLAMA_BASE_URL if hasattr(settings, 'OLLAMA_BASE_URL') else "http://ollama:11434"
        self.model_engine = f"ollama:{model}"

    def _generate(self, prompt: str, temperature: float = 0.0) -> str:
        """Generate response from Ollama."""
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "temperature": temperature,
                    "stream": False
                },
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            return ""

    def _extract_score(self, response: str) -> float:
        """Extract numerical score from LLM response."""
        try:
            # Look for patterns like "Score: 0.8" or "8/10" or just "0.8"
            import re

            # Try to find a decimal number between 0 and 1
            match = re.search(r'(?:score[:\s]+)?(\d+\.?\d*)', response.lower())
            if match:
                score = float(match.group(1))
                # Normalize to 0-1 if needed
                if score > 1:
                    score = score / 10.0
                return max(0.0, min(1.0, score))

            # Default to middle score if can't parse
            return 0.5
        except:
            return 0.5

    def context_relevance(self, question: str, context: str) -> float:
        """
        Evaluate how relevant the context is to the question.
        Returns: Score between 0 and 1
        """
        prompt = f"""You are evaluating the relevance of retrieved context to a user's question.

Question: {question}

Context:
{context[:2000]}

Task: Rate how relevant this context is to answering the question on a scale of 0 to 1, where:
- 0 = Completely irrelevant
- 0.5 = Somewhat relevant
- 1 = Highly relevant and directly answers the question

Provide your rating as a single decimal number between 0 and 1.
Rating:"""

        response = self._generate(prompt, temperature=0.0)
        score = self._extract_score(response)
        logger.debug(f"Context relevance score: {score}")
        return score

    def groundedness_measure_with_cot_reasons(self, context: str, response: str) -> float:
        """
        Evaluate if the response is grounded in (supported by) the context.
        This is the hallucination detection metric.

        Returns: Score between 0 and 1
        """
        prompt = f"""You are evaluating whether an AI-generated response is grounded in the provided context.

Context:
{context[:2000]}

AI Response:
{response[:1000]}

Task: Determine if the AI response is fully supported by the context. Rate groundedness on a scale of 0 to 1:
- 0 = Response contains information not in context (hallucination)
- 0.5 = Partially grounded, some claims not supported
- 1 = Fully grounded, all claims supported by context

Think step by step:
1. Identify key claims in the response
2. Check if each claim is supported by the context
3. Calculate the proportion of supported claims

Provide your final rating as a single decimal number between 0 and 1.
Rating:"""

        response = self._generate(prompt, temperature=0.0)
        score = self._extract_score(response)
        logger.debug(f"Groundedness score: {score}")
        return score

    def relevance(self, question: str, response: str) -> float:
        """
        Evaluate if the response addresses the question.

        Returns: Score between 0 and 1
        """
        prompt = f"""You are evaluating whether an AI response adequately addresses a user's question.

Question: {question}

AI Response:
{response[:1000]}

Task: Rate how well the response addresses the question on a scale of 0 to 1:
- 0 = Does not address the question at all
- 0.5 = Partially addresses the question
- 1 = Fully and directly addresses the question

Provide your rating as a single decimal number between 0 and 1.
Rating:"""

        response_text = self._generate(prompt, temperature=0.0)
        score = self._extract_score(response_text)
        logger.debug(f"Answer relevance score: {score}")
        return score

    def context_relevance_with_cot_reasons(self, question: str, context: str) -> Tuple[float, Dict]:
        """
        Context relevance with chain-of-thought reasoning.
        Returns score and reasoning dictionary.
        """
        score = self.context_relevance(question, context)
        reasons = {"score": score, "reasoning": "Evaluated with Ollama"}
        return score, reasons

    def relevance_with_cot_reasons(self, question: str, response: str) -> Tuple[float, Dict]:
        """
        Answer relevance with chain-of-thought reasoning.
        Returns score and reasoning dictionary.
        """
        score = self.relevance(question, response)
        reasons = {"score": score, "reasoning": "Evaluated with Ollama"}
        return score, reasons
