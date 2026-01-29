"""
Authentication service for token-based email authentication.
Uses Redis for multi-replica support in Kubernetes.
Replaces SQLite auth_tokens.db.
"""

from typing import Dict, Any

from app.services.auth.redis_auth_service import get_redis_auth_service, RedisAuthService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AuthService:
    """
    Authentication service wrapper that uses Redis backend.
    Provides the same interface as the old SQLite-based service.
    """

    def __init__(self):
        self._redis_auth: RedisAuthService = None
        self._initialized = False

    async def _ensure_initialized(self):
        """Ensure Redis auth service is initialized."""
        if not self._initialized:
            self._redis_auth = await get_redis_auth_service()
            self._initialized = True

    def generate_token(self) -> str:
        """Generate a cryptographically secure 6-digit code."""
        # Create a temporary instance just for token generation (sync operation)
        temp_service = RedisAuthService()
        return temp_service.generate_token()

    async def request_token(self, email: str) -> Dict[str, Any]:
        """Request a new access token and send via email."""
        await self._ensure_initialized()
        return await self._redis_auth.request_token(email)

    async def validate_token(self, token: str) -> Dict[str, Any]:
        """Validate an access token with detailed error information."""
        await self._ensure_initialized()
        return await self._redis_auth.validate_token(token)

    async def cleanup_expired_tokens(self) -> int:
        """Remove expired tokens (handled automatically by Redis TTL)."""
        await self._ensure_initialized()
        return await self._redis_auth.cleanup_expired_tokens()

    async def get_token_stats(self) -> Dict[str, int]:
        """Get token statistics."""
        await self._ensure_initialized()
        return await self._redis_auth.get_token_stats()


# Global auth service instance
_auth_service = None


def get_auth_service() -> AuthService:
    """Get the global auth service instance."""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service
