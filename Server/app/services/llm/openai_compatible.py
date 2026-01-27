"""OpenAI-compatible LLM implementation for any OpenAI-compatible API endpoint."""

import asyncio
import aiohttp
import json
from typing import Any, Dict, List, Optional

from langchain.callbacks.manager import CallbackManagerForLLMRun
from langchain.llms.base import LLM
from pydantic import Field

from app.core.exceptions import LLMError
from app.core.dependencies import get_semaphore_manager
from app.utils.logger import get_logger

logger = get_logger(__name__)


class OpenAICompatibleLLM(LLM):
    """OpenAI-compatible LLM implementation using chat completions API."""

    api_url: str = Field(default="https://lex.itml.space/v1/chat/completions")
    api_token: Optional[str] = Field(default=None)
    model: str = Field(default="mistral.mistral-7b-instruct-v0:2")
    temperature: float = Field(default=0.2)
    max_tokens: int = Field(default=1500)
    timeout: int = Field(default=60)
    system_prompt: Optional[str] = Field(default=None)

    @property
    def _llm_type(self) -> str:
        return "openai_compatible"

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """Call the OpenAI-compatible API synchronously."""
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
        Call the OpenAI-compatible API asynchronously with semaphore control.

        Limits concurrent API calls to prevent overload and
        manage resource usage across the application.
        """
        semaphore_manager = get_semaphore_manager()

        logger.debug("Waiting for LLM semaphore (OpenAI-compatible)...")
        async with semaphore_manager.llm_semaphore:
            logger.debug("LLM semaphore acquired (OpenAI-compatible)")

            try:
                headers = {
                    "Content-Type": "application/json",
                }

                # Add authorization header if token is provided
                if self.api_token:
                    headers["Authorization"] = f"Bearer {self.api_token}"

                # Build messages array
                messages = []

                # Add system prompt if provided
                if self.system_prompt:
                    messages.append({
                        "role": "system",
                        "content": self.system_prompt
                    })

                # Add user message
                messages.append({
                    "role": "user",
                    "content": prompt
                })

                # Build request payload
                payload = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens,
                }

                # Add stop sequences if provided
                if stop:
                    payload["stop"] = stop

                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.api_url,
                        json=payload,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=self.timeout)
                    ) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            raise LLMError(f"API error {response.status}: {error_text}")

                        result = await response.json()

                        # Parse OpenAI-compatible response format
                        # Response: {"choices": [{"message": {"content": "..."}}], ...}
                        choices = result.get("choices", [])

                        if not choices:
                            raise LLMError("No choices returned from API")

                        content = choices[0].get("message", {}).get("content", "")

                        if not content:
                            # Try alternative response format
                            content = choices[0].get("text", "")

                        logger.debug("LLM semaphore released (OpenAI-compatible)")
                        return content.strip()

            except asyncio.TimeoutError:
                logger.error(f"API request timed out after {self.timeout}s")
                raise LLMError("LLM API request timed out")
            except aiohttp.ClientError as e:
                logger.error(f"API connection error: {e}")
                raise LLMError(f"Failed to connect to LLM API: {str(e)}")
            except LLMError:
                raise
            except Exception as e:
                logger.error(f"LLM API error: {e}")
                raise LLMError(f"LLM API call failed: {str(e)}")

    async def test_connection(self) -> bool:
        """Test connection to the OpenAI-compatible API."""
        try:
            # Store original values
            original_max_tokens = self.max_tokens

            # Use minimal tokens for test
            self.max_tokens = 10

            result = await self._acall("Hello", stop=None, run_manager=None)

            # Restore original values
            self.max_tokens = original_max_tokens

            return bool(result)

        except Exception as e:
            logger.error(f"Failed to connect to OpenAI-compatible API: {e}")
            return False

    @property
    def _identifying_params(self) -> Dict[str, Any]:
        """Return identifying parameters."""
        return {
            "api_url": self.api_url,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
