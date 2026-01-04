"""
Unified LLM Client supporting both Ollama and OpenAI

Automatically switches between providers based on MODEL_PROVIDER environment variable.
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


class OllamaLLMClient(BaseLLMClient):
    """LLM client using Ollama (Free, Local)."""

    def __init__(self):
        self.api_url = os.getenv("OLLAMA_API_URL", "http://localhost:11434")
        self.model = os.getenv("OLLAMA_MODEL", "mistral:7b")
        self.embedding_model = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
        # Timeout is in MINUTES in .env, convert to seconds
        timeout_minutes = int(os.getenv("OLLAMA_TIMEOUT", "2"))
        self.timeout = timeout_minutes * 60

        logger.info(f"🆓 Initialized Ollama LLM Client - Model: {self.model}")

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """Generate text using Ollama."""
        import httpx

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }

        if system_prompt:
            payload["system"] = system_prompt

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.api_url}/api/generate",
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using Ollama."""
        import httpx

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.api_url}/api/embeddings",
                json={
                    "model": self.embedding_model,
                    "prompt": text
                }
            )
            response.raise_for_status()
            result = response.json()
            return result.get("embedding", [])

    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        import asyncio
        tasks = [self.generate_embedding(text) for text in texts]
        return await asyncio.gather(*tasks)


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
        BaseLLMClient: Ollama client (free) or OpenAI client (paid)

    """
    provider = os.getenv("MODEL_PROVIDER", "free").lower()

    if provider == "paid":
        logger.info("💳 Using PAID model provider (OpenAI)")
        return OpenAILLMClient()
    else:
        logger.info("🆓 Using FREE model provider (Ollama)")
        return OllamaLLMClient()


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
