"""
Repository for authentication token database operations.
Separates database logic from business logic.
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session

from app.models.auth import AuthToken
from app.repositories.base import BaseRepository


class AuthTokenRepository(BaseRepository[AuthToken]):
    """Repository for authentication token operations."""

    def __init__(self, session: Session):
        super().__init__(AuthToken, session)

    def find_by_token(self, token: str) -> Optional[AuthToken]:
        """
        Find token by token string.

        Args:
            token: The 6-digit token string

        Returns:
            AuthToken if found, None otherwise
        """
        return self.session.query(AuthToken).filter_by(token=token).first()

    def find_valid_token(self, token: str) -> Optional[AuthToken]:
        """
        Find valid (non-expired) token.

        Args:
            token: The 6-digit token string

        Returns:
            AuthToken if found and not expired, None otherwise
        """
        auth_token = self.find_by_token(token)
        if auth_token and not auth_token.is_expired:
            return auth_token
        return None

    def delete_expired_tokens(self) -> int:
        """
        Delete all expired tokens.

        Returns:
            Number of tokens deleted
        """
        now = datetime.utcnow()
        deleted_count = (
            self.session.query(AuthToken)
            .filter(AuthToken.expires_at < now)
            .delete()
        )
        self.session.commit()
        return deleted_count

    def get_active_tokens_count(self) -> int:
        """
        Get count of active (non-expired) tokens.

        Returns:
            Number of active tokens
        """
        now = datetime.utcnow()
        return (
            self.session.query(AuthToken)
            .filter(AuthToken.expires_at > now)
            .count()
        )

    def get_expired_tokens_count(self) -> int:
        """
        Get count of expired tokens.

        Returns:
            Number of expired tokens
        """
        now = datetime.utcnow()
        return (
            self.session.query(AuthToken)
            .filter(AuthToken.expires_at < now)
            .count()
        )

    def get_token_stats(self) -> dict:
        """
        Get comprehensive token statistics.

        Returns:
            Dictionary with token statistics
        """
        total = self.count()
        active = self.get_active_tokens_count()
        expired = self.get_expired_tokens_count()

        return {
            "total": total,
            "active": active,
            "expired": expired,
        }

    def token_exists(self, token: str) -> bool:
        """
        Check if token exists.

        Args:
            token: The 6-digit token string

        Returns:
            True if exists, False otherwise
        """
        return self.find_by_token(token) is not None
