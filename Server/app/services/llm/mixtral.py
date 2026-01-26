"""Bedrock LLM implementation via OpenAI-compatible endpoint with async semaphore control."""

import asyncio
import json
from typing import Any, Dict, List, Optional

import aiohttp
from langchain.callbacks.manager import CallbackManagerForLLMRun
from langchain.llms.base import LLM
from pydantic import Field

from app.core.exceptions import LLMError
from app.core.dependencies import get_semaphore_manager
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MixtralLLM(LLM):
    """Bedrock LLM implementation via OpenAI-compatible endpoint."""

    base_url: str = Field(default="https://lex.itml.space")  # Will be overridden by settings
    api_key: str = Field(default="")  # Bearer token for authentication
    model: str = Field(default="mistral.mistral-7b-instruct-v0:2")
    temperature: float = Field(default=0.2)
    max_tokens: int = Field(default=2000)
    timeout: int = Field(default=300)

    @property
    def _llm_type(self) -> str:
        return "bedrock_mixtral"

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """Call the Bedrock model synchronously."""
        # Run async method in sync context
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self._acall(prompt, stop, run_manager, **kwargs)
        )

    async def _acall(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """
        Call the Bedrock model asynchronously with semaphore control.

        Limits concurrent Bedrock API calls to prevent overload and
        manage resource usage across the application.
        """
        semaphore_manager = get_semaphore_manager()

        logger.debug("🔒 Waiting for LLM semaphore (Bedrock)...")
        async with semaphore_manager.llm_semaphore:
            logger.debug("✅ LLM semaphore acquired (Bedrock)")

            # Build OpenAI-compatible chat completions payload
            messages = [{"role": "user", "content": prompt}]

            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            }

            if stop:
                payload["stop"] = stop

            try:
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }

                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.base_url}/v1/chat/completions",
                        json=payload,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=self.timeout)
                    ) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            raise LLMError(f"Bedrock API error {response.status}: {error_text}")

                        result = await response.json()
                        logger.debug("🔓 LLM semaphore released (Bedrock)")
                        # OpenAI-compatible response format
                        return result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()

            except aiohttp.ClientError as e:
                raise LLMError(f"Bedrock connection error: {str(e)}")
            except asyncio.TimeoutError:
                raise LLMError("Bedrock request timed out")
            except Exception as e:
                raise LLMError(f"Bedrock error: {str(e)}")

    async def test_connection(self) -> bool:
        """Test connection to Bedrock endpoint."""
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }

            # Simple test payload using OpenAI-compatible format
            test_payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": "Hello"}],
                "temperature": 0.1,
                "max_tokens": 10
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/v1/chat/completions",
                    json=test_payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        # Check if we got a valid response
                        choices = result.get("choices", [])
                        return len(choices) > 0 and bool(choices[0].get("message", {}).get("content"))
                    return False
        except Exception as e:
            logger.error(f"Failed to connect to Bedrock: {e}")
            return False

    @property
    def _identifying_params(self) -> Dict[str, Any]:
        """Return identifying parameters."""
        return {
            "model": self.model,
            "base_url": self.base_url,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
