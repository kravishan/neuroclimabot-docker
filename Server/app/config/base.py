"""
Base application configuration.
Core settings like host, port, debug mode, environment.
"""

from typing import List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class BaseConfig(BaseSettings):
    """Core application settings."""

    # Application Info
    APP_NAME: str = "NeuroClima Bot RAG"
    APP_VERSION: str = "0.1.2"
    ENVIRONMENT: str  # From .env

    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 1
    RELOAD: bool = False

    # Debugging & Logging
    DEBUG: bool  # From .env
    LOG_LEVEL: str  # From .env
    LOG_FORMAT: str  # From .env

    # Validators
    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of {valid_levels}")
        return v.upper()

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        valid_envs = ["development", "staging", "production", "testing"]
        if v.lower() not in valid_envs:
            raise ValueError(f"ENVIRONMENT must be one of {valid_envs}")
        return v.lower()

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"
