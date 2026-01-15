"""
Updated dependencies.py with proper session validation and semaphore management
"""

import asyncio
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer

from app.config import Settings, get_settings
from app.services.memory.session import SessionManager, get_session_manager
from app.utils.logger import get_logger

security = HTTPBearer(auto_error=False)
logger = get_logger(__name__)


class SemaphoreManager:
    """
    Centralized management of async semaphores for concurrency control.

    Semaphores limit concurrent execution of resource-intensive operations:
    - Chat requests: Prevent overwhelming the entire pipeline
    - LLM calls: Control API rate limits and costs
    - Milvus queries: Prevent database overload
    - External APIs: Respect service rate limits

    Benefits:
    - Resource protection (memory, CPU, API limits)
    - Predictable performance under load
    - Cost control for paid APIs
    - Better error handling

    Usage:
        async with semaphore_manager.chat_semaphore:
            # Process chat request
            result = await process_chat()
    """

    _instance: Optional["SemaphoreManager"] = None
    _initialized: bool = False

    def __init__(self, settings: Settings):
        """Initialize semaphores based on configuration."""
        if SemaphoreManager._initialized:
            return

        self.settings = settings

        # Chat processing semaphore
        self.chat_semaphore = asyncio.Semaphore(
            settings.MAX_CONCURRENT_CHAT_REQUESTS
        )
        logger.info(
            f"Chat semaphore initialized with limit: "
            f"{settings.MAX_CONCURRENT_CHAT_REQUESTS}"
        )

        # LLM API call semaphore
        self.llm_semaphore = asyncio.Semaphore(
            settings.MAX_CONCURRENT_LLM_CALLS
        )
        logger.info(
            f"LLM semaphore initialized with limit: "
            f"{settings.MAX_CONCURRENT_LLM_CALLS}"
        )

        # Milvus vector database semaphore
        self.milvus_semaphore = asyncio.Semaphore(
            settings.MAX_CONCURRENT_MILVUS_QUERIES
        )
        logger.info(
            f"Milvus semaphore initialized with limit: "
            f"{settings.MAX_CONCURRENT_MILVUS_QUERIES}"
        )

        # External API semaphores
        self.translation_semaphore = asyncio.Semaphore(
            settings.MAX_CONCURRENT_TRANSLATION_CALLS
        )
        logger.info(
            f"Translation semaphore initialized with limit: "
            f"{settings.MAX_CONCURRENT_TRANSLATION_CALLS}"
        )

        self.graphrag_semaphore = asyncio.Semaphore(
            settings.MAX_CONCURRENT_GRAPHRAG_CALLS
        )
        logger.info(
            f"GraphRAG semaphore initialized with limit: "
            f"{settings.MAX_CONCURRENT_GRAPHRAG_CALLS}"
        )

        self.stp_semaphore = asyncio.Semaphore(
            settings.MAX_CONCURRENT_STP_CALLS
        )
        logger.info(
            f"STP semaphore initialized with limit: "
            f"{settings.MAX_CONCURRENT_STP_CALLS}"
        )

        # Timeout for semaphore acquisition
        self.acquisition_timeout = settings.SEMAPHORE_ACQUISITION_TIMEOUT

        SemaphoreManager._initialized = True
        logger.info("SemaphoreManager initialization complete")

    @classmethod
    def get_instance(cls, settings: Settings = None) -> "SemaphoreManager":
        """Get or create singleton instance."""
        if cls._instance is None:
            if settings is None:
                settings = get_settings()
            cls._instance = cls(settings)
        return cls._instance

    async def acquire_with_timeout(
        self,
        semaphore: asyncio.Semaphore,
        semaphore_name: str,
        timeout: Optional[float] = None
    ):
        """
        Acquire semaphore with timeout to prevent indefinite waiting.

        Args:
            semaphore: The semaphore to acquire
            semaphore_name: Name for logging purposes
            timeout: Maximum wait time (uses default if None)

        Raises:
            TimeoutError: If semaphore cannot be acquired within timeout
        """
        timeout = timeout or self.acquisition_timeout

        try:
            async with asyncio.timeout(timeout):
                logger.debug(f"Waiting to acquire {semaphore_name} semaphore...")
                await semaphore.acquire()
                logger.debug(f"{semaphore_name} semaphore acquired")
                return semaphore
        except asyncio.TimeoutError:
            logger.warning(
                f"Timeout waiting for {semaphore_name} semaphore after {timeout}s"
            )
            raise TimeoutError(
                f"System is currently overloaded. "
                f"Could not acquire {semaphore_name} within {timeout} seconds."
            )


# Global semaphore manager instance
_semaphore_manager: Optional[SemaphoreManager] = None


def get_semaphore_manager() -> SemaphoreManager:
    """Get or create the global semaphore manager instance."""
    global _semaphore_manager
    if _semaphore_manager is None:
        settings = get_settings()
        _semaphore_manager = SemaphoreManager.get_instance(settings)
    return _semaphore_manager


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