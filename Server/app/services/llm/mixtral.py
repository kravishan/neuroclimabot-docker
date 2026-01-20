"""Mixtral LLM implementation via hosted endpoint with async semaphore control."""

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
    """Mixtral LLM implementation via hosted endpoint."""
    
    base_url: str = Field(default="http://localhost:11434")  # Will be overridden by settings
    model: str = Field(default="mistral:7b")
    temperature: float = Field(default=0.2)
    max_tokens: int = Field(default=2000)
    timeout: int = Field(default=300)
    
    @property
    def _llm_type(self) -> str:
        return "mixtral"
    
    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """Call the Mixtral model synchronously."""
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
        Call the Mixtral model asynchronously with semaphore control.

        Limits concurrent Mixtral API calls to prevent overload and
        manage resource usage across the application.
        """
        semaphore_manager = get_semaphore_manager()

        logger.debug("🔒 Waiting for LLM semaphore (Mixtral)...")
        async with semaphore_manager.llm_semaphore:
            logger.debug("✅ LLM semaphore acquired (Mixtral)")

            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens,
                    "stop": stop or [],
                }
            }

            try:
                headers = {
                    "Content-Type": "application/json"
                }

                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.base_url}/api/generate",
                        json=payload,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=self.timeout)
                    ) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            raise LLMError(f"Mixtral API error {response.status}: {error_text}")

                        result = await response.json()
                        logger.debug("🔓 LLM semaphore released (Mixtral)")
                        return result.get("response", "").strip()

            except aiohttp.ClientError as e:
                raise LLMError(f"Mixtral connection error: {str(e)}")
            except asyncio.TimeoutError:
                raise LLMError("Mixtral request timed out")
            except Exception as e:
                raise LLMError(f"Mixtral error: {str(e)}")

    async def astream(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ):
        """
        Stream the Mixtral model response asynchronously (token by token).

        This method implements SSE-style streaming following industry standards.
        Yields response chunks as they arrive from Ollama.
        """
        semaphore_manager = get_semaphore_manager()

        logger.debug("🔒 Waiting for LLM semaphore (Mixtral streaming)...")
        async with semaphore_manager.llm_semaphore:
            logger.debug("✅ LLM semaphore acquired (Mixtral streaming)")

            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": True,  # Enable streaming
                "options": {
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens,
                    "stop": stop or [],
                }
            }

            try:
                headers = {
                    "Content-Type": "application/json"
                }

                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.base_url}/api/generate",
                        json=payload,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=self.timeout)
                    ) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            raise LLMError(f"Mixtral API error {response.status}: {error_text}")

                        # Read the response line by line (NDJSON format)
                        async for line in response.content:
                            if line:
                                try:
                                    chunk_data = json.loads(line.decode('utf-8'))

                                    # Extract the response chunk
                                    chunk_text = chunk_data.get("response", "")
                                    is_done = chunk_data.get("done", False)

                                    if chunk_text:
                                        yield chunk_text

                                    if is_done:
                                        logger.debug("🔓 LLM semaphore released (Mixtral streaming complete)")
                                        break

                                except json.JSONDecodeError:
                                    # Skip malformed JSON lines
                                    continue

            except aiohttp.ClientError as e:
                raise LLMError(f"Mixtral streaming connection error: {str(e)}")
            except asyncio.TimeoutError:
                raise LLMError("Mixtral streaming request timed out")
            except Exception as e:
                raise LLMError(f"Mixtral streaming error: {str(e)}")
    
    async def test_connection(self) -> bool:
        """Test connection to hosted Mixtral endpoint."""
        try:
            headers = {
                "Content-Type": "application/json"
            }

            # Simple test payload
            test_payload = {
                "model": self.model,
                "prompt": "Hello",
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 10
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/generate",
                    json=test_payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        # Check if we got a valid response
                        return bool(result.get("response"))
                    return False
        except Exception as e:
            logger.error(f"Failed to connect to hosted Mixtral: {e}")
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