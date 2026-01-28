"""
Redis-based authentication service for token management.
Replaces SQLite auth_tokens.db for multi-replica support in Kubernetes.
"""

import secrets
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path
import redis.asyncio as redis
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.config.database import get_redis_config
from app.config import get_settings
from app.constants import AUTH_TOKEN_MIN, AUTH_TOKEN_MAX
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

# Set up Jinja2 environment for email templates
TEMPLATE_DIR = Path(__file__).parent.parent.parent / "templates" / "emails"
jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(['html', 'xml'])
)

# Redis key prefix for auth tokens
AUTH_TOKEN_PREFIX = "auth:token:"
AUTH_TOKEN_STATS_KEY = "auth:stats"


class RedisAuthService:
    """
    Redis-based authentication service for token management.
    Supports concurrent access from multiple Server replicas.
    """

    def __init__(self):
        self.redis_config = get_redis_config()
        self.redis_client: Optional[redis.Redis] = None
        self._initialized = False

    async def initialize(self):
        """Initialize Redis connection."""
        if self._initialized:
            return

        try:
            self.redis_client = redis.from_url(
                self.redis_config.URL,
                password=self.redis_config.PASSWORD,
                decode_responses=True
            )
            # Test connection
            await self.redis_client.ping()
            self._initialized = True
            logger.info("Redis auth service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Redis auth service: {e}")
            raise

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
            if not self._initialized:
                await self.initialize()

            # Generate new token
            token = self.generate_token()

            # Calculate expiry
            expiry_seconds = settings.AUTH_TOKEN_EXPIRY_DAYS * 24 * 60 * 60
            expires_at = datetime.utcnow() + timedelta(days=settings.AUTH_TOKEN_EXPIRY_DAYS)

            # Save to Redis with TTL
            token_key = f"{AUTH_TOKEN_PREFIX}{token}"
            token_data = {
                "token": token,
                "email": email,
                "created_at": datetime.utcnow().isoformat(),
                "expires_at": expires_at.isoformat()
            }

            # Store token with automatic expiry
            await self.redis_client.hset(token_key, mapping=token_data)
            await self.redis_client.expire(token_key, expiry_seconds)

            logger.info(f"Token generated and saved to Redis")

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
            if not self._initialized:
                await self.initialize()

            # Basic token format validation
            if not token or len(token) != 6 or not token.isdigit():
                return {
                    "success": False,
                    "valid": False,
                    "error": "Invalid access token format. Expected 6-digit code.",
                    "error_type": "format_error"
                }

            token_key = f"{AUTH_TOKEN_PREFIX}{token}"
            token_data = await self.redis_client.hgetall(token_key)

            if not token_data:
                return {
                    "success": False,
                    "valid": False,
                    "error": "Access token not found. Please request a new token.",
                    "error_type": "token_not_found"
                }

            # Check expiry (Redis TTL handles auto-deletion, but check explicitly)
            expires_at_str = token_data.get("expires_at")
            if expires_at_str:
                expires_at = datetime.fromisoformat(expires_at_str)
                now = datetime.utcnow()

                if now > expires_at:
                    # Token expired (should be auto-deleted by Redis, but handle edge case)
                    await self.redis_client.delete(token_key)

                    time_expired = now - expires_at
                    days_expired = time_expired.days
                    hours_expired = time_expired.seconds // 3600

                    if days_expired > 0:
                        expired_message = f"Access token expired {days_expired} day{'s' if days_expired != 1 else ''} ago"
                    elif hours_expired > 0:
                        expired_message = f"Access token expired {hours_expired} hour{'s' if hours_expired != 1 else ''} ago"
                    else:
                        minutes_expired = time_expired.seconds // 60
                        if minutes_expired > 0:
                            expired_message = f"Access token expired {minutes_expired} minute{'s' if minutes_expired != 1 else ''} ago"
                        else:
                            expired_message = "Access token expired recently"

                    return {
                        "success": False,
                        "valid": False,
                        "error": expired_message,
                        "error_type": "token_expired",
                        "expired_at": expires_at.isoformat(),
                        "days_expired": days_expired,
                        "hours_expired": hours_expired if days_expired == 0 else None
                    }

                # Token is valid - return remaining time
                time_remaining = expires_at - now
                days_remaining = time_remaining.days
                hours_remaining = time_remaining.seconds // 3600
                expires_in_seconds = int(time_remaining.total_seconds())

                return {
                    "success": True,
                    "valid": True,
                    "expires_in": expires_in_seconds,
                    "message": "Access token is valid",
                    "expires_at": expires_at.isoformat(),
                    "days_remaining": days_remaining,
                    "hours_remaining": hours_remaining if days_remaining == 0 else None
                }

            return {
                "success": True,
                "valid": True,
                "message": "Access token is valid"
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
        Cleanup is handled automatically by Redis TTL.
        This method is kept for API compatibility.
        """
        # Redis automatically expires tokens via TTL
        # This is a no-op but kept for backward compatibility
        logger.info("Token cleanup is handled automatically by Redis TTL")
        return 0

    async def get_token_stats(self) -> Dict[str, int]:
        """Get token statistics."""
        try:
            if not self._initialized:
                await self.initialize()

            # Count tokens by scanning (use with caution in production)
            total_tokens = 0
            active_tokens = 0
            expiring_soon = 0
            now = datetime.utcnow()
            soon = now + timedelta(days=1)

            async for key in self.redis_client.scan_iter(f"{AUTH_TOKEN_PREFIX}*"):
                total_tokens += 1
                ttl = await self.redis_client.ttl(key)
                if ttl > 0:
                    active_tokens += 1
                    if ttl < 86400:  # Less than 1 day
                        expiring_soon += 1

            return {
                "total": total_tokens,
                "active": active_tokens,
                "expired": 0,  # Redis auto-deletes expired
                "recently_expired": 0,  # Can't track with Redis TTL
                "expiring_soon": expiring_soon
            }

        except Exception as e:
            logger.error(f"Error getting token stats: {e}")
            return {"total": 0, "active": 0, "expired": 0, "recently_expired": 0, "expiring_soon": 0}

    async def _send_token_email(self, email: str, token: str):
        """Send token via configured email provider with retry logic."""
        for attempt in range(settings.EMAIL_RETRY_ATTEMPTS):
            try:
                if settings.EMAIL_PROVIDER == "maileroo":
                    await self._send_via_maileroo(email, token)
                else:
                    await self._send_via_smtp(email, token)

                logger.info(f"Email sent successfully to {email} via {settings.EMAIL_PROVIDER}")
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
                            logger.info(f"Email sent successfully to {email} via SMTP fallback")
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
                    logger.info(f"Email sent successfully via Maileroo!")
                elif response.status_code == 401:
                    raise Exception("Maileroo API authentication failed. Please check your API key.")
                elif response.status_code == 403:
                    raise Exception("Maileroo API forbidden. Add recipient to authorized recipients list.")
                else:
                    raise Exception(f"Maileroo API error: {response.status_code} - {response.text}")

        except Exception as e:
            logger.error(f"Failed to send email via Maileroo: {e}")
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

            logger.info(f"Email sent successfully via SMTP to {email}")

        except Exception as e:
            logger.error(f"Failed to send email via SMTP: {e}")
            raise Exception(f"SMTP error: {str(e)}")

    def _generate_html_email(self, token: str) -> str:
        """Generate HTML email content using Jinja2 template."""
        template = jinja_env.get_template('auth_token.html')
        return template.render(
            token=token,
            token_expiry_days=settings.AUTH_TOKEN_EXPIRY_DAYS
        )

    def _generate_text_email(self, token: str) -> str:
        """Generate plain text email content using Jinja2 template."""
        template = jinja_env.get_template('auth_token.txt')
        return template.render(
            token=token,
            token_expiry_days=settings.AUTH_TOKEN_EXPIRY_DAYS
        )

    async def close(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
            self._initialized = False
            logger.info("Redis auth service connection closed")


# Global auth service instance
_redis_auth_service: Optional[RedisAuthService] = None


async def get_redis_auth_service() -> RedisAuthService:
    """Get the global Redis auth service instance."""
    global _redis_auth_service
    if _redis_auth_service is None:
        _redis_auth_service = RedisAuthService()
        await _redis_auth_service.initialize()
    return _redis_auth_service
