"""
Authentication service for token-based email authentication using Redis with auto-expiration.

Tokens are stored in Redis with TTL (Time To Live) for automatic expiration.
No cleanup tasks needed - Redis handles expiration automatically.
"""

import secrets
import asyncio
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
import redis.asyncio as redis

from app.config import get_settings
from app.config.database import get_redis_config
from app.constants import AUTH_TOKEN_MIN, AUTH_TOKEN_MAX
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()
redis_config = get_redis_config()

# Set up Jinja2 environment for email templates
TEMPLATE_DIR = Path(__file__).parent.parent.parent / "templates" / "emails"
jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(['html', 'xml'])
)


class AuthService:
    """Authentication service for token management using Redis with TTL expiration."""

    def __init__(self):
        self._redis_client: Optional[redis.Redis] = None
        self._initialized = False
        self._key_prefix = redis_config.AUTH_TOKEN_PREFIX

    async def _ensure_initialized(self):
        """Ensure Redis client is initialized."""
        if not self._initialized:
            await self.initialize()

    async def initialize(self):
        """Initialize Redis connection for auth tokens."""
        try:
            if self._redis_client is None:
                self._redis_client = redis.from_url(
                    redis_config.URL,
                    db=redis_config.AUTH_DB,
                    password=redis_config.PASSWORD,
                    decode_responses=True,
                    socket_timeout=redis_config.SOCKET_TIMEOUT,
                    socket_connect_timeout=redis_config.CONNECTION_TIMEOUT
                )
                # Test connection
                await self._redis_client.ping()
                logger.info("✅ Auth service Redis connection initialized")
            self._initialized = True
        except Exception as e:
            logger.error(f"❌ Failed to initialize Redis for auth service: {e}")
            raise

    async def close(self):
        """Close Redis connection."""
        if self._redis_client:
            await self._redis_client.close()
            self._redis_client = None
            self._initialized = False
            logger.info("Auth service Redis connection closed")

    def _get_token_key(self, token: str) -> str:
        """Get Redis key for a token."""
        return f"{self._key_prefix}{token}"

    def generate_token(self) -> str:
        """
        Generate a cryptographically secure 6-digit code.

        SECURITY: Uses secrets module instead of random for cryptographic security.
        Range: 100000-999999 (6-digit codes)
        """
        range_size = AUTH_TOKEN_MAX - AUTH_TOKEN_MIN + 1
        random_offset = secrets.randbelow(range_size)
        token_value = AUTH_TOKEN_MIN + random_offset
        return f"{token_value}"

    async def request_token(self, email: str) -> Dict[str, Any]:
        """Request a new access token and send via email."""
        try:
            await self._ensure_initialized()

            # Generate new token
            token = self.generate_token()

            # Calculate expiration in seconds
            expiry_days = settings.AUTH_TOKEN_EXPIRY_DAYS
            expiry_seconds = expiry_days * 24 * 60 * 60

            # Store token in Redis with TTL
            # Store token metadata as JSON for potential future use
            token_data = {
                "created_at": datetime.utcnow().isoformat(),
                "email_hash": hash(email) % 10000  # Store partial hash for debugging (not the actual email)
            }

            key = self._get_token_key(token)
            await self._redis_client.setex(
                key,
                expiry_seconds,
                json.dumps(token_data)
            )

            logger.info(f"Token generated and saved to Redis with {expiry_days} day TTL")

            # Send email
            if settings.is_development and not settings.email_is_configured:
                logger.warning(f"Development mode: Token generated but email not configured. Token: {token}")
                return {
                    "success": True,
                    "message": f"Development mode: Your access token is {token}"
                }
            else:
                await self._send_token_email(email, token)

            return {
                "success": True,
                "message": "Access token has been sent to your email"
            }

        except Exception as e:
            logger.error(f"Error requesting token: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def validate_token(self, token: str) -> Dict[str, Any]:
        """Validate an access token with detailed error information."""
        try:
            await self._ensure_initialized()

            # Basic token format validation
            if not token or len(token) != 6 or not token.isdigit():
                return {
                    "success": False,
                    "valid": False,
                    "error": "Invalid access token format. Expected 6-digit code.",
                    "error_type": "format_error"
                }

            key = self._get_token_key(token)

            # Check if token exists in Redis
            token_data_str = await self._redis_client.get(key)

            if not token_data_str:
                # Token doesn't exist - either never existed or expired (auto-removed by Redis)
                return {
                    "success": False,
                    "valid": False,
                    "error": "Access token not found or expired. Please request a new token.",
                    "error_type": "token_not_found"
                }

            # Token exists - get remaining TTL
            ttl_seconds = await self._redis_client.ttl(key)

            if ttl_seconds <= 0:
                # Token is expiring/expired (shouldn't happen normally due to Redis auto-cleanup)
                return {
                    "success": False,
                    "valid": False,
                    "error": "Access token has expired. Please request a new token.",
                    "error_type": "token_expired"
                }

            # Parse token data
            try:
                token_data = json.loads(token_data_str)
                created_at = datetime.fromisoformat(token_data.get("created_at", datetime.utcnow().isoformat()))
            except (json.JSONDecodeError, ValueError):
                created_at = datetime.utcnow()

            # Calculate time remaining
            days_remaining = ttl_seconds // (24 * 60 * 60)
            hours_remaining = (ttl_seconds % (24 * 60 * 60)) // 3600

            # Calculate expiry time
            expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)

            return {
                "success": True,
                "valid": True,
                "expires_in": ttl_seconds,
                "message": "Access token is valid",
                "expires_at": expires_at.isoformat(),
                "days_remaining": days_remaining,
                "hours_remaining": hours_remaining if days_remaining == 0 else None
            }

        except Exception as e:
            logger.error(f"Error validating token: {e}")
            return {
                "success": False,
                "valid": False,
                "error": "Token validation service error. Please try again.",
                "error_type": "service_error"
            }

    async def cleanup_expired_tokens(self) -> int:
        """
        Manual cleanup - not needed with Redis TTL, but kept for API compatibility.

        Redis automatically removes expired keys, so this just returns 0.
        This method is kept for backward compatibility with the API.
        """
        logger.info("Cleanup called - Redis handles expiration automatically via TTL")
        return 0

    async def get_token_stats(self) -> Dict[str, int]:
        """Get token statistics."""
        try:
            await self._ensure_initialized()

            # Count active tokens using SCAN with pattern matching
            pattern = f"{self._key_prefix}*"
            active_count = 0

            async for key in self._redis_client.scan_iter(match=pattern):
                active_count += 1

            return {
                "total": active_count,
                "active": active_count,
                "expired": 0,  # Redis auto-removes expired keys
                "recently_expired": 0,  # Not trackable with TTL-based expiration
                "expiring_soon": 0  # Could be implemented by checking TTL < 1 day
            }

        except Exception as e:
            logger.error(f"Error getting token stats: {e}")
            return {"total": 0, "active": 0, "expired": 0, "recently_expired": 0, "expiring_soon": 0}

    async def delete_token(self, token: str) -> bool:
        """Delete a specific token (for logout or revocation)."""
        try:
            await self._ensure_initialized()
            key = self._get_token_key(token)
            result = await self._redis_client.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Error deleting token: {e}")
            return False

    async def health_check(self) -> bool:
        """Check if Redis connection is healthy."""
        try:
            await self._ensure_initialized()
            await self._redis_client.ping()
            return True
        except Exception as e:
            logger.error(f"Auth service health check failed: {e}")
            return False

    async def _send_token_email(self, email: str, token: str):
        """Send token via configured email provider with retry logic."""
        for attempt in range(settings.EMAIL_RETRY_ATTEMPTS):
            try:
                if settings.EMAIL_PROVIDER == "maileroo":
                    await self._send_via_maileroo(email, token)
                else:
                    await self._send_via_smtp(email, token)

                logger.info(f"✅ Email sent successfully to {email} via {settings.EMAIL_PROVIDER}")
                return

            except Exception as e:
                logger.warning(f"Email attempt {attempt + 1} failed: {e}")

                if attempt < settings.EMAIL_RETRY_ATTEMPTS - 1:
                    await asyncio.sleep(settings.EMAIL_RETRY_DELAY_SECONDS * (attempt + 1))
                    continue
                else:
                    # Last attempt failed, try fallback if available
                    if settings.EMAIL_PROVIDER == "maileroo" and settings.smtp_auth_enabled:
                        logger.info("Trying SMTP fallback after Maileroo failure")
                        try:
                            await self._send_via_smtp(email, token)
                            logger.info(f"✅ Email sent successfully to {email} via SMTP fallback")
                            return
                        except Exception as smtp_error:
                            logger.error(f"SMTP fallback also failed: {smtp_error}")

                    raise Exception(f"Failed to send email after {settings.EMAIL_RETRY_ATTEMPTS} attempts: {str(e)}")

    async def _send_via_maileroo(self, email: str, token: str):
        """Send token email via Maileroo API."""
        try:
            import httpx

            if not settings.maileroo_is_configured:
                raise Exception("Maileroo is not properly configured")

            logger.info(f"Sending email via Maileroo to: {email}")

            subject = "Your NeuroClima Bot Access Code"
            html_content = self._generate_html_email(token)
            text_content = self._generate_text_email(token)

            payload = {
                "from": {
                    "address": settings.MAILEROO_FROM_EMAIL,
                    "display_name": settings.MAILEROO_FROM_NAME
                },
                "to": [{"address": email}],
                "subject": subject,
                "html": html_content,
                "plain": text_content
            }

            headers = {
                "X-API-Key": settings.MAILEROO_API_KEY,
                "Content-Type": "application/json",
                "User-Agent": f"NeuroClima/{settings.APP_VERSION}",
            }

            async with httpx.AsyncClient(timeout=settings.EMAIL_TIMEOUT_SECONDS) as client:
                response = await client.post(settings.MAILEROO_API_URL, json=payload, headers=headers)

                if response.status_code == 200:
                    logger.info(f"✅ Email sent successfully via Maileroo!")
                elif response.status_code == 401:
                    raise Exception("Maileroo API authentication failed. Please check your API key.")
                elif response.status_code == 403:
                    raise Exception("Maileroo API forbidden. Add recipient to authorized recipients list.")
                else:
                    raise Exception(f"Maileroo API error: {response.status_code} - {response.text}")

        except Exception as e:
            logger.error(f"❌ Failed to send email via Maileroo: {e}")
            raise

    async def _send_via_smtp(self, email: str, token: str):
        """Send token email via SMTP server."""
        try:
            import smtplib
            import ssl
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            logger.info(f"Sending email via SMTP to: {email}")

            subject = "Your NeuroClima Bot Access Code"
            html_content = self._generate_html_email(token)
            text_content = self._generate_text_email(token)

            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = settings.FROM_EMAIL
            message["To"] = email

            text_part = MIMEText(text_content, "plain")
            html_part = MIMEText(html_content, "html")

            message.attach(text_part)
            message.attach(html_part)

            context = ssl.create_default_context()

            if settings.SMTP_PORT == 587:
                with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
                    server.starttls(context=context)
                    if settings.smtp_auth_enabled:
                        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                    server.sendmail(settings.FROM_EMAIL, email, message.as_string())
            elif settings.SMTP_PORT == 465:
                with smtplib.SMTP_SSL(settings.SMTP_SERVER, settings.SMTP_PORT, context=context) as server:
                    if settings.smtp_auth_enabled:
                        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                    server.sendmail(settings.FROM_EMAIL, email, message.as_string())
            else:
                with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
                    if settings.smtp_auth_enabled:
                        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                    server.sendmail(settings.FROM_EMAIL, email, message.as_string())

            logger.info(f"✅ Email sent successfully via SMTP to {email}")

        except Exception as e:
            logger.error(f"❌ Failed to send email via SMTP: {e}")
            raise Exception(f"SMTP error: {str(e)}")

    def _generate_html_email(self, token: str) -> str:
        """
        Generate HTML email content using Jinja2 template.

        Template file: app/templates/emails/auth_token.html
        """
        template = jinja_env.get_template('auth_token.html')
        return template.render(
            token=token,
            token_expiry_days=settings.AUTH_TOKEN_EXPIRY_DAYS
        )

    def _generate_text_email(self, token: str) -> str:
        """
        Generate plain text email content using Jinja2 template.

        Template file: app/templates/emails/auth_token.txt
        """
        template = jinja_env.get_template('auth_token.txt')
        return template.render(
            token=token,
            token_expiry_days=settings.AUTH_TOKEN_EXPIRY_DAYS
        )


# Global auth service instance
_auth_service: Optional[AuthService] = None


def get_auth_service() -> AuthService:
    """Get the global auth service instance."""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service


async def initialize_auth_service() -> AuthService:
    """Initialize and return the global auth service instance."""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    await _auth_service.initialize()
    return _auth_service
