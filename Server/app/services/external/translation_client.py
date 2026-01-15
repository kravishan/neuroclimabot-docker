"""
Translation service client for the local translation server at http://127.0.0.1:1151
Handles automatic language detection and batch translation with XML markers.
Includes async semaphore control to limit concurrent translation requests.
"""

import asyncio
import aiohttp
import re
from typing import Optional, Dict

from app.config import get_settings
from app.config.integrations import IntegrationsConfig
from app.services.tracing import get_langfuse_client, is_langfuse_enabled
from app.core.dependencies import get_semaphore_manager
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()
integrations_config = IntegrationsConfig()


class TranslationClient:
    """Client for local translation service with automatic language detection and batch translation."""

    def __init__(self):
        # Load configuration from integrations config (SECURITY: Never hardcode URLs!)
        self.base_url = integrations_config.TRANSLATION_SERVICE_URL
        self.translate_in_endpoint = "/translate/in"
        self.translate_out_endpoint = "/translate/out"
        self.health_endpoint = "/health"
        self.timeout = integrations_config.TRANSLATION_SERVICE_TIMEOUT
        self.is_initialized = True

        # Supported languages from config
        self.supported_languages = integrations_config.TRANSLATION_SUPPORTED_LANGUAGES
    
    async def translate_to_english(self, content: str) -> tuple[str, str]:
        """
        Translate content to English from auto-detected source language with tracing.
        
        Returns:
            tuple: (translated_text, detected_language)
        """
        if not content or not content.strip():
            return content, "en"
        
        if is_langfuse_enabled():
            langfuse_client = get_langfuse_client()
            with langfuse_client.start_as_current_span(
                name="translation_to_english",
                input=content[:200],
                metadata={
                    "component": "translation_service",
                    "step": "input_translation",
                    "direction": "auto→en",
                    "service": "local_translation_server"
                }
            ) as span:
                try:
                    translated_text, detected_lang = await self._translate_in_request(content)
                    
                    span.update(
                        output=translated_text[:200],
                        metadata={
                            "translation_success": True,
                            "detected_language": detected_lang,
                            "is_english": detected_lang == "en",
                            "original_length": len(content),
                            "translated_length": len(translated_text),
                            "was_translated": detected_lang != "en",
                            "service_endpoint": self.translate_in_endpoint
                        }
                    )
                    
                    return translated_text, detected_lang
                    
                except Exception as e:
                    span.update(
                        output=f"Translation failed: {str(e)}",
                        level="ERROR",
                        metadata={
                            "translation_success": False,
                            "error": str(e),
                            "fallback_to_original": True
                        }
                    )
                    logger.error(f"Error translating to English: {e}")
                    return content, "en"
        else:
            # No tracing version
            try:
                return await self._translate_in_request(content)
            except Exception as e:
                logger.error(f"Error translating to English: {e}")
                return content, "en"
    
    async def translate_batch_from_english(
        self, 
        title: str,
        response: str,
        target_language: str,
        social_tipping_point: Optional[Dict] = None
    ) -> Dict[str, any]:
        """
        Translate title, response, and social tipping point from English to target language.
        Uses the /translate/out endpoint which handles the full response structure.
        
        Args:
            title: Title text in English
            response: Response text in English
            target_language: Target language code (e.g., 'it', 'pt', 'el')
            social_tipping_point: Optional STP dict with 'text' and 'qualifying_factors'
        
        Returns:
            Dict with translated 'title', 'response', and 'social_tipping_point'
        """
        if target_language == "en" or target_language not in self.supported_languages:
            return {
                "title": title,
                "response": response,
                "social_tipping_point": social_tipping_point
            }
        
        if is_langfuse_enabled():
            langfuse_client = get_langfuse_client()
            with langfuse_client.start_as_current_span(
                name="batch_translation_from_english",
                input=f"Title + Response + STP (combined)",
                metadata={
                    "component": "translation_service",
                    "step": "batch_output_translation",
                    "direction": f"en→{target_language}",
                    "target_language": target_language,
                    "title_length": len(title),
                    "response_length": len(response),
                    "has_stp": bool(social_tipping_point),
                    "service": "local_translation_server"
                }
            ) as span:
                try:
                    # Call translation server
                    translated_result = await self._translate_out_request(
                        title=title,
                        response=response,
                        target_language=target_language,
                        social_tipping_point=social_tipping_point
                    )
                    
                    span.update(
                        output=f"Translated title, response, and STP successfully",
                        metadata={
                            "translation_success": True,
                            "target_language": target_language,
                            "translated_title_length": len(translated_result["title"]),
                            "translated_response_length": len(translated_result["response"]),
                            "stp_translated": "social_tipping_point" in translated_result,
                            "service_endpoint": self.translate_out_endpoint
                        }
                    )
                    
                    return translated_result
                    
                except Exception as e:
                    span.update(
                        output=f"Batch translation failed: {str(e)}",
                        level="ERROR",
                        metadata={
                            "translation_success": False,
                            "error": str(e),
                            "fallback_to_original": True,
                            "target_language": target_language
                        }
                    )
                    logger.error(f"Error in batch translation to {target_language}: {e}")
                    # Fallback: return original texts
                    return {
                        "title": title,
                        "response": response,
                        "social_tipping_point": social_tipping_point
                    }
        else:
            # No tracing version
            try:
                return await self._translate_out_request(
                    title=title,
                    response=response,
                    target_language=target_language,
                    social_tipping_point=social_tipping_point
                )
            except Exception as e:
                logger.error(f"Error in batch translation to {target_language}: {e}")
                return {
                    "title": title,
                    "response": response,
                    "social_tipping_point": social_tipping_point
                }
    
    async def _translate_in_request(self, content: str) -> tuple[str, str]:
        """
        Make translation IN request to local server (auto-detect → English).
        Uses semaphore to limit concurrent translation API calls.

        Returns:
            tuple: (translated_text, detected_language)
        """
        semaphore_manager = get_semaphore_manager()

        logger.debug("🔒 Waiting for translation semaphore (IN)...")
        async with semaphore_manager.translation_semaphore:
            logger.debug("✅ Translation semaphore acquired (IN)")

            payload = {
                "text": content
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}{self.translate_in_endpoint}",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        translated_text = result.get("translated_text", content)
                        detected_language = result.get("detected_language", "en")
                        is_english = result.get("is_english", False)

                        if is_english:
                            logger.info("Text is already in English - no translation needed")
                        else:
                            logger.info(f"Translated from {detected_language} to English")

                        logger.debug("🔓 Translation semaphore released (IN)")
                        return translated_text.strip() if translated_text else content, detected_language
                    else:
                        error_text = await response.text()
                        logger.warning(f"Translation IN failed with status {response.status}: {error_text}")
                        return content, "en"
    
    async def _translate_out_request(
        self,
        title: str,
        response: str,
        target_language: str,
        social_tipping_point: Optional[Dict] = None
    ) -> Dict[str, any]:
        """
        Make translation OUT request to local server (English → target language).
        Uses semaphore to limit concurrent translation API calls.

        Returns:
            Dict with translated 'title', 'response', and 'social_tipping_point'
        """
        semaphore_manager = get_semaphore_manager()

        logger.debug("🔒 Waiting for translation semaphore (OUT)...")
        async with semaphore_manager.translation_semaphore:
            logger.debug("✅ Translation semaphore acquired (OUT)")

            payload = {
                "target_lang": target_language,
                "title": title,
                "response": response
            }

            # Add social tipping point if provided
            if social_tipping_point:
                payload["social_tipping_point"] = social_tipping_point

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}{self.translate_out_endpoint}",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"Successfully translated to {target_language}")
                        logger.debug("🔓 Translation semaphore released (OUT)")
                        return result
                    else:
                        error_text = await response.text()
                        logger.warning(f"Translation OUT failed with status {response.status}: {error_text}")
                        # Return originals on failure
                        return {
                            "title": title,
                            "response": response,
                            "social_tipping_point": social_tipping_point
                        }
    
    async def health_check(self) -> bool:
        """Check if translation service is healthy."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}{self.health_endpoint}",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"✅ Translation service healthy: {result.get('status')}")
                        return True
                    return False
                    
        except Exception as e:
            logger.error(f"Translation service health check failed: {e}")
            return False
    
    def get_supported_languages(self) -> list:
        """Get list of supported languages."""
        return self.supported_languages.copy()


# Global instance
_translation_client = None


def get_translation_client() -> TranslationClient:
    """Get translation client instance."""
    global _translation_client
    if _translation_client is None:
        _translation_client = TranslationClient()
    return _translation_client