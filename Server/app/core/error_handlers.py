"""
Centralized error handling decorators and utilities.
Provides consistent error handling across all API endpoints.
"""

from functools import wraps
from typing import Callable, Any
from fastapi import HTTPException, status

from app.utils.logger import get_logger

logger = get_logger(__name__)


def api_error_handler(operation_name: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR):
    """
    Decorator for consistent error handling in API endpoints.

    Automatically catches exceptions, logs them with full stack trace,
    and returns appropriate HTTP errors.

    Args:
        operation_name: Human-readable name of the operation (e.g., "start conversation")
        status_code: HTTP status code to return on error (default: 500)

    Usage:
        @router.post("/endpoint")
        @api_error_handler("create user")
        async def create_user(...):
            # Your code here
            # No need for try-catch!
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                # Re-raise HTTP exceptions without modification
                raise
            except Exception as e:
                # Log the full exception with stack trace
                logger.error(
                    f"{operation_name} failed: {str(e)}",
                    exc_info=True,
                    extra={
                        "operation": operation_name,
                        "error_type": type(e).__name__,
                        "error_message": str(e)
                    }
                )

                # Return generic error to client (don't leak implementation details)
                raise HTTPException(
                    status_code=status_code,
                    detail=f"{operation_name.capitalize()} failed"
                )

        return wrapper
    return decorator


def service_error_handler(service_name: str, operation_name: str):
    """
    Decorator for error handling in service layer.

    Similar to api_error_handler but for service methods.
    Logs errors but doesn't raise HTTPException (services shouldn't know about HTTP).

    Args:
        service_name: Name of the service (e.g., "AuthService")
        operation_name: Name of the operation (e.g., "create_token")

    Usage:
        class AuthService:
            @service_error_handler("AuthService", "create token")
            async def create_token(self, email: str):
                # Your code here
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(
                    f"{service_name}.{operation_name} failed: {str(e)}",
                    exc_info=True,
                    extra={
                        "service": service_name,
                        "operation": operation_name,
                        "error_type": type(e).__name__,
                        "error_message": str(e)
                    }
                )
                # Re-raise for caller to handle
                raise

        return wrapper
    return decorator


def repository_error_handler(repository_name: str, operation_name: str):
    """
    Decorator for error handling in repository layer.

    Similar to service_error_handler but specifically for database operations.

    Args:
        repository_name: Name of the repository (e.g., "AuthTokenRepository")
        operation_name: Name of the operation (e.g., "create")

    Usage:
        class AuthTokenRepository:
            @repository_error_handler("AuthTokenRepository", "create")
            async def create(self, token: AuthToken):
                # Your code here
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(
                    f"{repository_name}.{operation_name} failed: {str(e)}",
                    exc_info=True,
                    extra={
                        "repository": repository_name,
                        "operation": operation_name,
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "layer": "repository"
                    }
                )
                # Re-raise for service layer to handle
                raise

        return wrapper
    return decorator
