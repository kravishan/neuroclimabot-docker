"""
Authentication middleware for token validation with detailed expiration messages.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer

from app.services.auth.auth_service import get_auth_service
from app.config.security import SecurityConfig
from app.utils.logger import get_logger

logger = get_logger(__name__)
security = HTTPBearer(auto_error=False)

def get_security_config() -> SecurityConfig:
    """Get security configuration."""
    return SecurityConfig()


async def get_auth_service_dep():
    """Get auth service dependency."""
    return get_auth_service()


async def validate_auth_token(
    authorization: Optional[str] = Header(None),
    auth_service = Depends(get_auth_service_dep),
    security_config: SecurityConfig = Depends(get_security_config)
) -> Optional[str]:
    """
    Validate authentication token from Authorization header with detailed error messages.

    If AUTH_ENABLED=False, authentication is bypassed and returns None.
    If AUTH_ENABLED=True, validates token normally.

    Expected format: "Bearer <token>"
    Returns the token if valid, raises HTTPException with specific error details if invalid.
    """
    # Skip authentication if disabled
    if not security_config.AUTH_ENABLED:
        logger.debug("Authentication disabled (AUTH_ENABLED=False), skipping token validation")
        return None

    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "missing_token",
                "message": "Authorization header required",
                "ui_message": "Please provide an access token to continue"
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # Parse "Bearer <token>"
        scheme, token = authorization.split(" ", 1)
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "invalid_scheme",
                    "message": "Invalid authentication scheme. Expected 'Bearer'",
                    "ui_message": "Invalid authentication format"
                },
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Validate token
        result = await auth_service.validate_token(token)
        
        if not result["success"]:
            # Handle specific validation errors
            error_message = result.get("error", "Token validation failed")
            
            if "expired" in error_message.lower():
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={
                        "error": "token_expired",
                        "message": error_message,
                        "ui_message": "Your access token has expired. Please request a new one.",
                        "action_required": "request_new_token"
                    },
                    headers={"WWW-Authenticate": "Bearer"},
                )
            elif "invalid" in error_message.lower():
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={
                        "error": "invalid_token",
                        "message": error_message,
                        "ui_message": "Invalid access token. Please check your token and try again.",
                        "action_required": "request_new_token"
                    },
                    headers={"WWW-Authenticate": "Bearer"},
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={
                        "error": "validation_failed",
                        "message": error_message,
                        "ui_message": "Authentication failed. Please request a new access token.",
                        "action_required": "request_new_token"
                    },
                    headers={"WWW-Authenticate": "Bearer"},
                )
        
        if not result["valid"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "token_invalid",
                    "message": "Token is not valid",
                    "ui_message": "Your access token is no longer valid. Please request a new one.",
                    "action_required": "request_new_token"
                },
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return token
        
    except ValueError:
        # Split failed - invalid format
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "invalid_format",
                "message": "Invalid authorization header format. Expected 'Bearer <token>'",
                "ui_message": "Invalid authentication format. Please try again.",
                "action_required": "request_new_token"
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating auth token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "validation_error",
                "message": "Authentication validation failed",
                "ui_message": "Authentication service error. Please try again.",
                "action_required": "retry_or_request_new_token"
            }
        )


async def optional_auth_token(
    authorization: Optional[str] = Header(None),
    auth_service = Depends(get_auth_service_dep),
    security_config: SecurityConfig = Depends(get_security_config)
) -> Optional[str]:
    """
    Optional authentication token validation.

    If AUTH_ENABLED=False, always returns None without validation.
    If AUTH_ENABLED=True, returns token if valid, None if no token provided or invalid.
    Does not raise exceptions for missing/invalid tokens.
    """
    # Skip authentication if disabled
    if not security_config.AUTH_ENABLED:
        return None

    if not authorization:
        return None
    
    try:
        # Parse "Bearer <token>"
        scheme, token = authorization.split(" ", 1)
        if scheme.lower() != "bearer":
            return None
        
        # Validate token
        result = await auth_service.validate_token(token)
        
        if result["success"] and result["valid"]:
            return token
        else:
            return None
            
    except Exception as e:
        logger.debug(f"Optional auth validation failed: {e}")
        return None


# Convenience function for protected endpoints
async def require_auth(token: str = Depends(validate_auth_token)) -> str:
    """
    Require valid authentication token.
    
    Use this dependency on endpoints that require authentication.
    """
    return token


# Convenience function for optional auth
async def optional_require_auth(token: Optional[str] = Depends(optional_auth_token)) -> Optional[str]:
    """
    Optional authentication token.
    
    Use this dependency on endpoints where auth is optional.
    """
    return token