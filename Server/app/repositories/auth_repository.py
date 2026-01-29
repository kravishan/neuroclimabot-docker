"""
Repository for authentication token operations.

DEPRECATED: Auth tokens are now stored in Redis with TTL-based expiration.
This module is kept for backward compatibility only.
Use app.services.auth.auth_service for all token operations.
"""

import warnings
from typing import Optional, Dict

from app.models.auth import AuthToken


class AuthTokenRepository:
    """
    DEPRECATED: Auth tokens are now stored in Redis.

    This class is kept for backward compatibility only.
    Use AuthService from app.services.auth.auth_service instead.
    """

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "AuthTokenRepository is deprecated. "
            "Auth tokens are now stored in Redis. "
            "Use AuthService from app.services.auth.auth_service instead.",
            DeprecationWarning,
            stacklevel=2
        )

    def find_by_token(self, token: str) -> Optional[AuthToken]:
        """DEPRECATED: Use AuthService.validate_token() instead."""
        raise NotImplementedError(
            "AuthTokenRepository is deprecated. Use AuthService.validate_token() instead."
        )

    def find_valid_token(self, token: str) -> Optional[AuthToken]:
        """DEPRECATED: Use AuthService.validate_token() instead."""
        raise NotImplementedError(
            "AuthTokenRepository is deprecated. Use AuthService.validate_token() instead."
        )

    def delete_expired_tokens(self) -> int:
        """DEPRECATED: Redis handles expiration automatically via TTL."""
        raise NotImplementedError(
            "AuthTokenRepository is deprecated. Redis handles expiration automatically."
        )

    def get_active_tokens_count(self) -> int:
        """DEPRECATED: Use AuthService.get_token_stats() instead."""
        raise NotImplementedError(
            "AuthTokenRepository is deprecated. Use AuthService.get_token_stats() instead."
        )

    def get_expired_tokens_count(self) -> int:
        """DEPRECATED: Redis auto-removes expired tokens."""
        raise NotImplementedError(
            "AuthTokenRepository is deprecated. Redis auto-removes expired tokens."
        )

    def get_token_stats(self) -> Dict:
        """DEPRECATED: Use AuthService.get_token_stats() instead."""
        raise NotImplementedError(
            "AuthTokenRepository is deprecated. Use AuthService.get_token_stats() instead."
        )

    def token_exists(self, token: str) -> bool:
        """DEPRECATED: Use AuthService.validate_token() instead."""
        raise NotImplementedError(
            "AuthTokenRepository is deprecated. Use AuthService.validate_token() instead."
        )
