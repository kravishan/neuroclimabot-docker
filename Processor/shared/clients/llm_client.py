"""
Unified LLM Client supporting both Bedrock (AWS) and OpenAI

Automatically switches between providers based on MODEL_PROVIDER environment variable.
Uses OpenAI-compatible API format for Bedrock via lex.itml.space gateway.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseLLMClient(ABC):
    """Base class for LLM clients."""

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """Generate text from prompt."""
        pass

    @abstractmethod
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding vector for text."""
        pass

    @abstractmethod
    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        pass


class BedrockLLMClient(BaseLLMClient):
    """LLM client using AWS Bedrock via OpenAI-compatible API gateway."""

    def __init__(self):
        self.api_url = os.getenv("BEDROCK_API_URL", "https://lex.itml.space")
        self.api_key = os.getenv("BEDROCK_API_KEY", "")
        self.model = os.getenv("BEDROCK_MODEL", "mistral.mistral-7b-instruct-v0:2")
        self.embedding_model = os.getenv("BEDROCK_EMBEDDING_MODEL", "amazon.titan-embed-text-v1")
        # Timeout is in MINUTES in .env, convert to seconds
        timeout_minutes = int(os.getenv("BEDROCK_TIMEOUT", "2"))
        self.timeout = timeout_minutes * 60

        logger.info(f"☁️ Initialized Bedrock LLM Client - Model: {self.model}")

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """Generate text using Bedrock via OpenAI-compatible API."""
        import httpx

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.api_url}/v1/chat/completions",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            result = response.json()
            # OpenAI-compatible response format
            return result.get("choices", [{}])[0].get("message", {}).get("content", "")

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using Bedrock via OpenAI-compatible API."""
        import httpx

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.api_url}/v1/embeddings",
                json={
                    "model": self.embedding_model,
                    "input": text
                },
                headers=headers
            )
            response.raise_for_status()
            result = response.json()
            # OpenAI-compatible response format
            return result.get("data", [{}])[0].get("embedding", [])

    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        import asyncio
        tasks = [self.generate_embedding(text) for text in texts]
        return await asyncio.gather(*tasks)


# Backward compatibility alias
OllamaLLMClient = BedrockLLMClient


class OpenAILLMClient(BaseLLMClient):
    """LLM client using OpenAI (Paid, API-based)."""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is required when MODEL_PROVIDER=paid")

        self.model = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
        self.embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-large")
        self.api_base = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
        self.organization = os.getenv("OPENAI_ORGANIZATION", "")
        # Timeout is in MINUTES in .env, convert to seconds
        timeout_minutes = int(os.getenv("OPENAI_TIMEOUT", "2"))
        self.timeout = timeout_minutes * 60

        logger.info(f"💳 Initialized OpenAI LLM Client - Model: {self.model}")

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """Generate text using OpenAI."""
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.api_base,
            organization=self.organization or None,
            timeout=self.timeout
        )

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )

        return response.choices[0].message.content

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using OpenAI."""
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.api_base,
            organization=self.organization or None,
            timeout=self.timeout
        )

        response = await client.embeddings.create(
            model=self.embedding_model,
            input=text
        )

        return response.data[0].embedding

    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.api_base,
            organization=self.organization or None,
            timeout=self.timeout
        )

        response = await client.embeddings.create(
            model=self.embedding_model,
            input=texts
        )

        return [item.embedding for item in response.data]


def create_llm_client() -> BaseLLMClient:
    """
    Create LLM client based on MODEL_PROVIDER environment variable.

    Returns:
        BaseLLMClient: Bedrock client (default) or OpenAI client (paid)

    """
    provider = os.getenv("MODEL_PROVIDER", "bedrock").lower()

    if provider == "openai" or provider == "paid":
        logger.info("💳 Using OpenAI model provider")
        return OpenAILLMClient()
    else:
        logger.info("☁️ Using Bedrock model provider (AWS)")
        return BedrockLLMClient()


# Global instance (lazy initialization)
_llm_client: Optional[BaseLLMClient] = None


def get_llm_client() -> BaseLLMClient:
    """
    Get or create global LLM client instance.

    Returns:
        BaseLLMClient: Singleton LLM client instance
    """
    global _llm_client

    if _llm_client is None:
        _llm_client = create_llm_client()

    return _llm_client
