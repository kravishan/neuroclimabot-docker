"""
Security configuration.
Authentication, CORS, rate limiting, and security settings.
"""

import secrets
from typing import List, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class SecurityConfig(BaseSettings):
    """Security and authentication settings."""

    # Security Keys
    SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALGORITHM: str = "HS256"

    # CORS Settings
    ALLOWED_ORIGINS: Union[str, List[str]] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
        "https://128-214-253-121.nip.io",
        "*"
    ]
    ALLOW_CREDENTIALS: bool = True
    ALLOWED_METHODS: Union[str, List[str]] = ["*"]
    ALLOWED_HEADERS: Union[str, List[str]] = ["*"]

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60
    CHAT_RATE_LIMIT: int = 20
    UPLOAD_RATE_LIMIT: int = 5
    ADMIN_RATE_LIMIT: int = 50

    # Authentication (from .env)
    # Note: Auth tokens are now stored in Redis with TTL-based auto-expiration
    AUTH_ENABLED: bool = Field(
        default=True,
        description="Enable/disable authentication. If False, app works without auth."
    )
    AUTH_TOKEN_EXPIRY_DAYS: int  # From .env

    # Admin Dashboard Authentication
    ADMIN_USERNAME: str = Field(
        ...,
        description="Admin dashboard username"
    )
    ADMIN_PASSWORD: str = Field(
        ...,
        description="Admin dashboard password"
    )

    # Validators
    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        # Handle None or empty string
        if v is None or v == "":
            return ["*"]
        # Handle string values
        if isinstance(v, str):
            # Don't try to parse JSON, just split by comma
            return [i.strip() for i in v.split(",") if i.strip()]
        # Handle list values
        elif isinstance(v, list):
            return v
        raise ValueError(f"Invalid ALLOWED_ORIGINS value: {v}")

    @field_validator("ALLOWED_METHODS", mode="before")
    @classmethod
    def assemble_cors_methods(cls, v: Union[str, List[str]]) -> List[str]:
        # Handle None or empty string
        if v is None or v == "":
            return ["*"]
        # Handle string values
        if isinstance(v, str):
            return [i.strip() for i in v.split(",") if i.strip()]
        # Handle list values
        elif isinstance(v, list):
            return v
        raise ValueError(f"Invalid ALLOWED_METHODS value: {v}")

    @field_validator("ALLOWED_HEADERS", mode="before")
    @classmethod
    def assemble_cors_headers(cls, v: Union[str, List[str]]) -> List[str]:
        # Handle None or empty string
        if v is None or v == "":
            return ["*"]
        # Handle string values
        if isinstance(v, str):
            return [i.strip() for i in v.split(",") if i.strip()]
        # Handle list values
        elif isinstance(v, list):
            return v
        raise ValueError(f"Invalid ALLOWED_HEADERS value: {v}")

    @field_validator("AUTH_TOKEN_EXPIRY_DAYS")
    @classmethod
    def validate_auth_token_expiry(cls, v: int) -> int:
        if not 1 <= v <= 30:
            raise ValueError("AUTH_TOKEN_EXPIRY_DAYS must be between 1 and 30 days")
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"
