"""
LLM (Large Language Model) configuration.
Settings for AWS Bedrock, OpenAI, Ollama, and other LLM providers.
"""

from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class LLMConfig(BaseSettings):
    """LLM provider configurations."""

    # Default LLM Provider (from .env)
    DEFAULT_LLM_PROVIDER: str = "bedrock"  # Options: "bedrock", "ollama", "openai"

    # Embedding Model Configuration (from .env)
    EMBEDDING_API_URL: str = "https://lex.itml.space/v1/embeddings"
    EMBEDDING_API_TOKEN: Optional[str] = None
    EMBEDDING_MODEL: str = "nomic-embed-text"
    EMBEDDING_DIMENSION: int = 768
    EMBEDDING_TIMEOUT: int = 30

    # AWS Bedrock Configuration (from .env)
    BEDROCK_REGION: str = "us-east-1"
    BEDROCK_MODEL_ID: str = "anthropic.claude-3-sonnet-20240229-v1:0"
    BEDROCK_ACCESS_KEY_ID: Optional[str] = None
    BEDROCK_SECRET_ACCESS_KEY: Optional[str] = None
    BEDROCK_ENDPOINT_URL: Optional[str] = None  # Optional custom endpoint
    BEDROCK_TEMPERATURE: float = 0.2
    BEDROCK_MAX_TOKENS: int = 1500
    BEDROCK_TIMEOUT: int = 60

    # Ollama Configuration (from .env)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "mistral:7b"
    OLLAMA_TEMPERATURE: float = 0.2
    OLLAMA_MAX_TOKENS: int = 1500
    OLLAMA_TIMEOUT: int = 30
    OLLAMA_CONNECTION_POOL_SIZE: int = 5

    # OpenAI Configuration (from .env)
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_TEMPERATURE: float = 0.2
    OPENAI_MAX_TOKENS: int = 1500
    OPENAI_TIMEOUT: int = 15

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"
