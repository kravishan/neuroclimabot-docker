"""Mixtral LLM implementation via hosted endpoint."""

import asyncio
import json
from typing import Any, Dict, List, Optional

import aiohttp
from langchain.callbacks.manager import CallbackManagerForLLMRun
from langchain.llms.base import LLM
from pydantic import Field

from app.core.exceptions import LLMError
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
        """Call the Mixtral model asynchronously."""
        
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
                    return result.get("response", "").strip()
                    
        except aiohttp.ClientError as e:
            raise LLMError(f"Mixtral connection error: {str(e)}")
        except asyncio.TimeoutError:
            raise LLMError("Mixtral request timed out")
        except Exception as e:
            raise LLMError(f"Mixtral error: {str(e)}")
    
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