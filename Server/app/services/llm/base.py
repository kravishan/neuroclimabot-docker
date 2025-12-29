"""Base LLM interface and utilities."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from langchain.llms.base import BaseLLM


class CustomBaseLLM(BaseLLM, ABC):
    """Custom base LLM with additional methods."""
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """Test connection to the LLM service."""
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information."""
        pass
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        try:
            connection_ok = await self.test_connection()
            return {
                "status": "healthy" if connection_ok else "unhealthy",
                "model_info": self.get_model_info(),
                "connection": connection_ok,
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "connection": False,
            }