"""
Updated auth API endpoints with enhanced Maileroo testing.
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, EmailStr
from typing import Optional

from app.services.auth.auth_service import get_auth_service
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


class TokenRequestModel(BaseModel):
    """Token request model."""
    email: EmailStr = Field(..., description="Email address to send token to")


class TokenValidationModel(BaseModel):
    """Token validation model."""
    token: str = Field(..., min_length=6, max_length=6, description="6-digit access code")


class TokenResponseModel(BaseModel):
    """Token response model."""
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None


class ValidationResponseModel(BaseModel):
    """Token validation response model."""
    success: bool
    valid: bool
    expires_in: Optional[int] = None
    message: Optional[str] = None
    error: Optional[str] = None


class EmailTestModel(BaseModel):
    """Email test request model."""
    email: EmailStr = Field(..., description="Email address for testing")
    provider: Optional[str] = Field(default=None, description="Force specific provider: 'maileroo' or 'smtp'")


class EmailTestResponseModel(BaseModel):
    """Email test response model."""
    success: bool
    provider_used: str
    message: str
    test_token: Optional[str] = None
    details: Optional[dict] = None
    error: Optional[str] = None


@router.post("/request-token", response_model=TokenResponseModel)
async def request_access_token(request: TokenRequestModel) -> TokenResponseModel:
    """
    Request a new 6-digit access code via email.
    
    The code will be sent to the provided email address and will be valid for 7 days.
    """
    try:
        auth_service = get_auth_service()
        result = await auth_service.request_token(request.email)
        
        if result["success"]:
            return TokenResponseModel(
                success=True,
                message=result["message"]
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in request_access_token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process token request"
        )


@router.post("/validate-token", response_model=ValidationResponseModel)
async def validate_access_token(request: TokenValidationModel) -> ValidationResponseModel:
    """
    Validate a 6-digit access code.
    
    Returns whether the code is valid and when it expires.
    """
    try:
        auth_service = get_auth_service()
        result = await auth_service.validate_token(request.token)
        
        return ValidationResponseModel(
            success=result["success"],
            valid=result["valid"],
            expires_in=result.get("expires_in"),
            message=result.get("message"),
            error=result.get("error")
        )
        
    except Exception as e:
        logger.error(f"Error in validate_access_token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate token"
        )


@router.post("/logout", response_model=TokenResponseModel)
async def logout() -> TokenResponseModel:
    """
    Logout endpoint (placeholder for client-side token cleanup).
    
    Currently just returns success - actual logout is handled client-side.
    """
    return TokenResponseModel(
        success=True,
        message="Logged out successfully"
    )


@router.get("/token-stats")
async def get_token_statistics():
    """
    Get token statistics (for admin/debugging purposes).
    
    Returns counts of total, active, and expired tokens.
    """
    try:
        auth_service = get_auth_service()
        stats = await auth_service.get_token_stats()
        
        return {
            "success": True,
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"Error getting token stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get token statistics"
        )


@router.post("/cleanup-expired")
async def cleanup_expired_tokens():
    """
    Manually trigger cleanup of expired tokens.
    
    This is also done automatically by a background task.
    """
    try:
        auth_service = get_auth_service()
        deleted_count = await auth_service.cleanup_expired_tokens()
        
        return {
            "success": True,
            "message": f"Cleaned up {deleted_count} expired tokens"
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up tokens: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cleanup expired tokens"
        )
    

@router.post("/test-email", response_model=EmailTestResponseModel)
async def test_email_sending(request: EmailTestModel):
    """
    Enhanced test endpoint to send a test email via Maileroo or SMTP.
    
    Only works in development mode for security.
    Tests both Maileroo and SMTP fallback functionality.
    """
    try:
        from app.config import get_settings
        settings = get_settings()
        
        if not settings.is_development:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Test endpoint only available in development mode"
            )
        
        auth_service = get_auth_service()
        
        # Generate a test code
        test_token = "123456"
        
        # Determine which provider to test
        provider_to_test = request.provider or settings.EMAIL_PROVIDER
        
        # Test email configuration status
        email_config_details = {
            "maileroo_configured": settings.maileroo_is_configured,
            "smtp_configured": settings.smtp_auth_enabled,
            "primary_provider": settings.EMAIL_PROVIDER,
            "test_provider": provider_to_test
        }
        
        if provider_to_test == "maileroo":
            if not settings.maileroo_is_configured:
                return EmailTestResponseModel(
                    success=False,
                    provider_used="none",
                    message="Maileroo is not configured",
                    error="Missing MAILEROO_API_KEY or MAILEROO_FROM_EMAIL",
                    details=email_config_details
                )
            
            try:
                # Test Maileroo specifically
                await auth_service._send_via_maileroo(request.email, test_token)
                
                return EmailTestResponseModel(
                    success=True,
                    provider_used="maileroo",
                    message=f"Test email sent successfully to {request.email} via Maileroo",
                    test_token=test_token,
                    details=email_config_details
                )
                
            except Exception as e:
                logger.error(f"Maileroo test failed: {e}")
                return EmailTestResponseModel(
                    success=False,
                    provider_used="maileroo",
                    message=f"Maileroo test failed: {str(e)}",
                    error=str(e),
                    details=email_config_details
                )
                
        elif provider_to_test == "smtp":
            if not settings.smtp_auth_enabled:
                return EmailTestResponseModel(
                    success=False,
                    provider_used="none",
                    message="SMTP is not configured",
                    error="Missing SMTP credentials",
                    details=email_config_details
                )
            
            try:
                # Test SMTP specifically
                await auth_service._send_via_smtp(request.email, test_token)
                
                return EmailTestResponseModel(
                    success=True,
                    provider_used="smtp",
                    message=f"Test email sent successfully to {request.email} via SMTP",
                    test_token=test_token,
                    details=email_config_details
                )
                
            except Exception as e:
                logger.error(f"SMTP test failed: {e}")
                return EmailTestResponseModel(
                    success=False,
                    provider_used="smtp",
                    message=f"SMTP test failed: {str(e)}",
                    error=str(e),
                    details=email_config_details
                )
        
        else:
            # Test the full email sending process with retry/fallback logic
            try:
                await auth_service._send_token_email(request.email, test_token)
                
                return EmailTestResponseModel(
                    success=True,
                    provider_used=settings.EMAIL_PROVIDER,
                    message=f"Test email sent successfully to {request.email}",
                    test_token=test_token,
                    details=email_config_details
                )
                
            except Exception as e:
                logger.error(f"Email test failed: {e}")
                return EmailTestResponseModel(
                    success=False,
                    provider_used=settings.EMAIL_PROVIDER,
                    message=f"Email test failed: {str(e)}",
                    error=str(e),
                    details=email_config_details
                )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in test email endpoint: {e}")
        return EmailTestResponseModel(
            success=False,
            provider_used="unknown",
            message="Test email failed with unexpected error",
            error=str(e)
        )


@router.get("/email-config")
async def get_email_configuration():
    """
    Get current email configuration status (for debugging/development).
    
    Only works in development mode for security.
    """
    try:
        from app.config import get_settings
        settings = get_settings()
        
        if not settings.is_development:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Configuration endpoint only available in development mode"
            )
        
        return {
            "success": True,
            "configuration": {
                "primary_provider": settings.EMAIL_PROVIDER,
                "maileroo": {
                    "configured": settings.maileroo_is_configured,
                    "api_key_set": bool(settings.MAILEROO_API_KEY),
                    "from_email": settings.MAILEROO_FROM_EMAIL,
                    "from_name": settings.MAILEROO_FROM_NAME,
                    "api_url": settings.MAILEROO_API_URL
                },
                "smtp": {
                    "configured": settings.smtp_auth_enabled,
                    "server": settings.SMTP_SERVER,
                    "port": settings.SMTP_PORT,
                    "username_set": bool(settings.SMTP_USERNAME),
                    "password_set": bool(settings.SMTP_PASSWORD),
                    "from_email": settings.FROM_EMAIL
                },
                "general": {
                    "timeout_seconds": settings.EMAIL_TIMEOUT_SECONDS,
                    "retry_attempts": settings.EMAIL_RETRY_ATTEMPTS,
                    "retry_delay_seconds": settings.EMAIL_RETRY_DELAY_SECONDS,
                    "token_expiry_days": settings.AUTH_TOKEN_EXPIRY_DAYS
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting email configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get email configuration"
        )