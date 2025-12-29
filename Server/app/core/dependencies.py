"""
Updated dependencies.py with proper session validation
"""

from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer

from app.config import Settings, get_settings
from app.services.memory.session import SessionManager, get_session_manager

security = HTTPBearer(auto_error=False)


async def get_current_settings() -> Settings:
    """Get current application settings."""
    return get_settings()


async def get_session_manager_dep() -> SessionManager:
    """Get session manager dependency."""
    return get_session_manager()


async def validate_session(
    session_id: UUID,
    session_manager: SessionManager = Depends(get_session_manager_dep)
) -> UUID:
    """
    Validate that a session exists.
    Used for /continue/{session_id} endpoint.
    """
    try:
        session = await session_manager.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found or expired"
            )
        return session_id
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Session validation failed: {str(e)}"
        )


async def validate_session_exists(
    session_id: str,
    session_manager: SessionManager = Depends(get_session_manager_dep)
) -> UUID:
    """
    Validate session ID string and convert to UUID.
    Used when session_id comes from headers or query params.
    """
    try:
        # Convert string to UUID
        session_uuid = UUID(session_id)
        
        # Check if session exists
        session = await session_manager.get_session(session_uuid)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found or expired"
            )
        
        return session_uuid
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid session ID format: {session_id}"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Session validation failed: {str(e)}"
        )


# Optional: Authentication dependency (if needed)
async def get_current_user(token: Optional[str] = Depends(security)):
    """Get current authenticated user (placeholder for future auth)."""
    # For now, we'll allow anonymous access
    # In the future, implement JWT token validation here
    return {"user_id": "anonymous", "authenticated": False}