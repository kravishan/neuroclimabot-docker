"""
Authentication token model.

Note: Tokens are now stored in Redis with TTL-based expiration.
This module is kept for backward compatibility and type hints.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional


@dataclass
class AuthToken:
    """
    Simple token data class for auth tokens.

    Note: Actual token storage is handled by Redis in auth_service.py.
    This class is kept for type hints and backward compatibility.
    """
    token: str
    created_at: datetime
    expires_at: datetime

    def __init__(self, token: str, expires_in_days: int = 7, created_at: Optional[datetime] = None):
        self.token = token
        self.created_at = created_at or datetime.utcnow()
        self.expires_at = self.created_at + timedelta(days=expires_in_days)

    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        return datetime.utcnow() > self.expires_at

    @property
    def expires_in_seconds(self) -> int:
        """Get seconds until expiry."""
        if self.is_expired:
            return 0
        return int((self.expires_at - datetime.utcnow()).total_seconds())
