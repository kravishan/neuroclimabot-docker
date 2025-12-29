"""
LLM (Large Language Model) configuration.
Settings for OpenAI, Ollama, and other LLM providers.
"""

from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class LLMConfig(BaseSettings):
    """LLM provider configurations."""

    # Ollama Configuration (from .env)
    OLLAMA_BASE_URL: str  # From .env
    OLLAMA_MODEL: str  # From .env
    OLLAMA_TEMPERATURE: float  # From .env
    OLLAMA_MAX_TOKENS: int  # From .env
    OLLAMA_TIMEOUT: int  # From .env
    OLLAMA_CONNECTION_POOL_SIZE: int = 5  # Default, not in .env

    # OpenAI Configuration (from .env)
    OPENAI_API_KEY: Optional[str] = None  # Optional from .env
    OPENAI_MODEL: str = "gpt-4o"  # Default if not in .env
    OPENAI_TEMPERATURE: float = 0.2  # Default if not in .env
    OPENAI_MAX_TOKENS: int = 1500  # Default if not in .env
    OPENAI_TIMEOUT: int = 15  # Default if not in .env

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"
