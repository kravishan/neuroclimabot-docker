"""
Authentication service for token-based email authentication with detailed error messages.
"""

import secrets
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path
from sqlalchemy.orm import Session
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.models.auth import AuthToken, get_auth_engine, get_auth_session_factory, create_auth_tables
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


class AuthService:
    """Authentication service for token management with detailed validation messages."""
    
    def __init__(self):
        self.engine = get_auth_engine()
        self.SessionLocal = get_auth_session_factory(self.engine)
        create_auth_tables(self.engine)
    
    def _get_db(self) -> Session:
        """Get database session."""
        return self.SessionLocal()
    
    def generate_token(self) -> str:
        """
        Generate a cryptographically secure 6-digit code.

        SECURITY: Uses secrets module instead of random for cryptographic security.
        Range: 100000-999999 (6-digit codes)
        """
        # Use secrets.randbelow() for cryptographically secure random number generation
        # secrets.randbelow(n) returns random int in range [0, n)
        range_size = AUTH_TOKEN_MAX - AUTH_TOKEN_MIN + 1
        random_offset = secrets.randbelow(range_size)
        token_value = AUTH_TOKEN_MIN + random_offset
        return f"{token_value}"
    
    async def request_token(self, email: str) -> Dict[str, Any]:
        """Request a new access token and send via email."""
        try:
            # Generate new token
            token = self.generate_token()
            
            # Save to database
            db = self._get_db()
            try:
                auth_token = AuthToken(token=token, expires_in_days=settings.AUTH_TOKEN_EXPIRY_DAYS)
                db.add(auth_token)
                db.commit()
                logger.info(f"Token generated and saved to database")
            except Exception as e:
                db.rollback()
                raise Exception(f"Database error: {str(e)}")
            finally:
                db.close()
            
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
            # Basic token format validation
            if not token or len(token) != 6 or not token.isdigit():
                return {
                    "success": False,
                    "valid": False,
                    "error": "Invalid access token format. Expected 6-digit code.",
                    "error_type": "format_error"
                }
            
            db = self._get_db()
            try:
                # Find token in database
                auth_token = db.query(AuthToken).filter(AuthToken.token == token).first()
                
                if not auth_token:
                    return {
                        "success": False,
                        "valid": False,
                        "error": "Access token not found. Please request a new token.",
                        "error_type": "token_not_found"
                    }
                
                # Check if expired with detailed information
                now = datetime.utcnow()
                if auth_token.is_expired:
                    # Calculate how long ago it expired
                    time_expired = now - auth_token.expires_at
                    days_expired = time_expired.days
                    hours_expired = time_expired.seconds // 3600
                    
                    # Remove expired token
                    db.delete(auth_token)
                    db.commit()
                    
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
                        "expired_at": auth_token.expires_at.isoformat(),
                        "days_expired": days_expired,
                        "hours_expired": hours_expired if days_expired == 0 else None
                    }
                
                # Token is valid - return remaining time
                time_remaining = auth_token.expires_at - now
                days_remaining = time_remaining.days
                hours_remaining = time_remaining.seconds // 3600
                
                return {
                    "success": True,
                    "valid": True,
                    "expires_in": auth_token.expires_in_seconds,
                    "message": "Access token is valid",
                    "expires_at": auth_token.expires_at.isoformat(),
                    "days_remaining": days_remaining,
                    "hours_remaining": hours_remaining if days_remaining == 0 else None
                }
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error validating token: {e}")
            return {
                "success": False,
                "valid": False,
                "error": "Token validation service error. Please try again.",
                "error_type": "service_error"
            }
    
    async def cleanup_expired_tokens(self) -> int:
        """Remove expired tokens from database."""
        try:
            db = self._get_db()
            try:
                # Delete expired tokens
                deleted_count = db.query(AuthToken).filter(
                    AuthToken.expires_at < datetime.utcnow()
                ).delete()
                
                db.commit()
                logger.info(f"Cleaned up {deleted_count} expired tokens")
                return deleted_count
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error cleaning up tokens: {e}")
            return 0
    
    async def get_token_stats(self) -> Dict[str, int]:
        """Get token statistics."""
        try:
            db = self._get_db()
            try:
                now = datetime.utcnow()
                
                total_tokens = db.query(AuthToken).count()
                expired_tokens = db.query(AuthToken).filter(
                    AuthToken.expires_at < now
                ).count()
                active_tokens = total_tokens - expired_tokens
                
                # Additional stats for better monitoring
                recently_expired = db.query(AuthToken).filter(
                    AuthToken.expires_at < now,
                    AuthToken.expires_at > now - timedelta(days=1)
                ).count()
                
                expiring_soon = db.query(AuthToken).filter(
                    AuthToken.expires_at > now,
                    AuthToken.expires_at < now + timedelta(days=1)
                ).count()
                
                return {
                    "total": total_tokens,
                    "active": active_tokens,
                    "expired": expired_tokens,
                    "recently_expired": recently_expired,
                    "expiring_soon": expiring_soon
                }
                
            finally:
                db.close()
                
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
            
            subject = "Your NeuroClima Access Code"
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
            
            subject = "Your NeuroClima Access Code"
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
_auth_service = None

def get_auth_service() -> AuthService:
    """Get the global auth service instance."""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service