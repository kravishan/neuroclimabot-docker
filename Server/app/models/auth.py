"""
Authentication token model for SQLite database.
"""

from datetime import datetime, timedelta
from sqlalchemy import Column, String, DateTime, create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base


class AuthToken(Base):
    """Simple token storage model for 6-digit codes."""
    __tablename__ = "auth_tokens"
    
    token = Column(String(6), primary_key=True)  # 6-digit code
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    
    def __init__(self, token: str, expires_in_days: int = 7):
        self.token = token
        self.created_at = datetime.utcnow()
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


# Database setup
def get_auth_engine(database_url: str = "sqlite:///./auth_tokens.db"):
    """Get SQLAlchemy engine for auth database."""
    return create_engine(database_url, echo=False)


def get_auth_session_factory(engine):
    """Get session factory for auth database."""
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_auth_tables(engine):
    """Create auth tables."""
    Base.metadata.create_all(bind=engine)