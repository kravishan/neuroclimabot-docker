"""OpenAI LLM implementation."""

from typing import Any, Dict, List, Optional

from langchain_community.llms import OpenAI
from langchain.callbacks.manager import CallbackManagerForLLMRun
from pydantic import Field

from app.core.exceptions import LLMError
from app.utils.logger import get_logger

logger = get_logger(__name__)


class OpenAILLM(OpenAI):
    """OpenAI LLM implementation with custom configuration."""
    
    api_key: str = Field(...)
    model: str = Field(default="gpt-4o-2024-08-06")
    temperature: float = Field(default=0.2)
    max_tokens: int = Field(default=2000)
    
    def __init__(self, **kwargs):
        """Initialize OpenAI LLM."""
        # Extract api_key for pydantic validation
        api_key = kwargs.get("api_key")
        if not api_key:
            raise ValueError("api_key is required")
            
        # Set the api_key field for pydantic
        super().__init__(
            openai_api_key=api_key,
            model_name=kwargs.get("model", "gpt-4o-2024-08-06"),
            temperature=kwargs.get("temperature", 0.2),
            max_tokens=kwargs.get("max_tokens", 2000),
        )
        
        # Set instance attributes
        self.api_key = api_key
        self.model = kwargs.get("model", "gpt-4o-2024-08-06")
        self.temperature = kwargs.get("temperature", 0.2)
        self.max_tokens = kwargs.get("max_tokens", 2000)
    
    async def test_connection(self) -> bool:
        """Test connection to OpenAI API."""
        try:
            # Test with a simple prompt
            result = await self._acall("Test connection", stop=None, run_manager=None)
            return bool(result)
        except Exception as e:
            logger.error(f"Failed to connect to OpenAI: {e}")
            return False