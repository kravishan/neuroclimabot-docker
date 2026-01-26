"""
LLM (Large Language Model) configuration.
Settings for Bedrock (AWS), OpenAI, and other LLM providers.
"""

from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class LLMConfig(BaseSettings):
    """LLM provider configurations."""

    # Bedrock Configuration (from .env) - OpenAI-compatible API via lex.itml.space
    BEDROCK_API_URL: str = "https://lex.itml.space"  # From .env
    BEDROCK_API_KEY: str = ""  # From .env (API token)
    BEDROCK_MODEL: str = "mistral.mistral-7b-instruct-v0:2"  # From .env
    BEDROCK_TEMPERATURE: float = 0.2  # From .env
    BEDROCK_MAX_TOKENS: int = 1500  # From .env
    BEDROCK_TIMEOUT: int = 30  # From .env (seconds)
    BEDROCK_CONNECTION_POOL_SIZE: int = 5  # Default, not in .env

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
