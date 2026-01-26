"""
Configuration package for the application.

This package provides a modular configuration system with settings organized
by domain (base, security, LLM, RAG, integrations, features).

Usage:
    from app.config import get_settings, Settings

    settings = get_settings()
    print(settings.APP_NAME)
    print(settings.GRAPHRAG_LOCAL_SEARCH_MAX_RESULTS)
"""

from pydantic_settings import BaseSettings

# Import all modular configs
from app.config.base import BaseConfig
from app.config.security import SecurityConfig
from app.config.llm import LLMConfig
from app.config.rag import RAGConfig
from app.config.integrations import IntegrationsConfig
from app.config.features import FeaturesConfig
from app.config.database import (
    DatabaseConfig,
    MilvusConfig,
    RedisConfig,
    MinIOConfig,
    AnalyticsConfig,
    get_database_config,
    get_milvus_config,
    get_redis_config,
    get_minio_config,
)


class Settings(
    BaseConfig,
    SecurityConfig,
    LLMConfig,
    RAGConfig,
    IntegrationsConfig,
    FeaturesConfig,
    BaseSettings
):
    """
    Unified application settings composed from modular configurations.

    This class inherits from all modular config classes, providing a single
    point of access to all application settings while keeping the configuration
    organized in separate modules:

    - BaseConfig: Core application settings (APP_NAME, HOST, PORT, etc.)
    - SecurityConfig: Security, authentication, CORS, rate limiting
    - LLMConfig: LLM provider settings (Bedrock, OpenAI)
    - RAGConfig: RAG pipeline configuration (retrieval, reranking, responses)
    - IntegrationsConfig: External services (Langfuse, GraphRAG, MinIO, STP)
    - FeaturesConfig: Feature flags, performance, monitoring

    Database configuration (Milvus, Redis, MinIO) is handled separately via
    app.config.database module using a factory pattern.
    """

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


# Global settings instance
_settings = None


def get_settings() -> Settings:
    """
    Get the global settings instance (singleton pattern).

    Returns:
        Settings: The global settings instance
    """
    global _settings

    if _settings is None:
        _settings = Settings()

    return _settings


# Convenience alias for backward compatibility
settings = get_settings()


# Define what gets exported when someone does "from app.config import *"
__all__ = [
    # Unified settings (most commonly used)
    "Settings",
    "get_settings",
    "settings",

    # Modular config classes
    "BaseConfig",
    "SecurityConfig",
    "LLMConfig",
    "RAGConfig",
    "IntegrationsConfig",
    "FeaturesConfig",

    # Database configs
    "DatabaseConfig",
    "MilvusConfig",
    "RedisConfig",
    "MinIOConfig",
    "AnalyticsConfig",
    "get_database_config",
    "get_milvus_config",
    "get_redis_config",
    "get_minio_config",
]
