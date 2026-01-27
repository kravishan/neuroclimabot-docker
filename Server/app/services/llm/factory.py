"""LLM factory for creating different LLM instances."""

import logging
from typing import Optional

from langchain.llms.base import BaseLLM

from app.config import get_settings
from app.core.exceptions import LLMError
from app.services.llm.openai_compatible import OpenAICompatibleLLM
from app.services.llm.mixtral import MixtralLLM
from app.services.llm.openai import OpenAILLM
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


async def get_llm(provider: Optional[str] = None) -> BaseLLM:
    """Get LLM instance based on configuration or provider preference.

    Priority order (when provider is not specified):
    1. Use DEFAULT_LLM_PROVIDER from settings (default: "openai_compatible")
    2. Fallback to other providers if the default fails
    """

    # Determine the provider to use
    target_provider = provider or settings.DEFAULT_LLM_PROVIDER

    # Try the target provider first
    if target_provider == "openai_compatible":
        try:
            return await get_openai_compatible_llm()
        except Exception as e:
            logger.warning(f"Failed to initialize OpenAI-compatible LLM: {e}")
            if provider == "openai_compatible":
                raise LLMError(f"OpenAI-compatible LLM requested but failed: {str(e)}")
            logger.info("Falling back to Ollama/Mixtral LLM")

    elif target_provider == "openai":
        try:
            return await get_openai_llm()
        except Exception as e:
            logger.warning(f"Failed to initialize OpenAI LLM: {e}")
            if provider == "openai":
                raise LLMError(f"OpenAI LLM requested but failed: {str(e)}")
            logger.info("Falling back to OpenAI-compatible LLM")
            try:
                return await get_openai_compatible_llm()
            except Exception as compat_e:
                logger.warning(f"OpenAI-compatible fallback failed: {compat_e}")

    elif target_provider == "ollama" or target_provider == "mixtral":
        try:
            return await get_mixtral_llm()
        except Exception as e:
            logger.warning(f"Failed to initialize Mixtral LLM: {e}")
            if provider in ("ollama", "mixtral"):
                raise LLMError(f"Mixtral LLM requested but failed: {str(e)}")
            logger.info("Falling back to OpenAI-compatible LLM")
            try:
                return await get_openai_compatible_llm()
            except Exception as compat_e:
                logger.warning(f"OpenAI-compatible fallback failed: {compat_e}")

    # Try remaining providers as fallbacks
    fallback_order = ["openai_compatible", "ollama", "openai"]
    errors = []

    for fallback_provider in fallback_order:
        if fallback_provider == target_provider:
            continue  # Skip the provider we already tried

        try:
            if fallback_provider == "openai_compatible":
                return await get_openai_compatible_llm()
            elif fallback_provider == "ollama":
                return await get_mixtral_llm()
            elif fallback_provider == "openai" and settings.OPENAI_API_KEY:
                return await get_openai_llm()
        except Exception as e:
            errors.append(f"{fallback_provider}: {str(e)}")
            logger.warning(f"{fallback_provider} fallback failed: {e}")

    raise LLMError(f"No LLM could be initialized. Errors: {'; '.join(errors)}")


async def get_openai_compatible_llm() -> BaseLLM:
    """Get OpenAI-compatible LLM instance."""
    if not settings.LLM_API_TOKEN:
        raise LLMError("LLM API token not configured (LLM_API_TOKEN)")

    try:
        llm = OpenAICompatibleLLM(
            api_url=settings.LLM_API_URL,
            api_token=settings.LLM_API_TOKEN,
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            timeout=settings.LLM_TIMEOUT,
        )

        # Test connection
        connection_ok = await llm.test_connection()
        if not connection_ok:
            raise LLMError(f"Could not connect to LLM API at {settings.LLM_API_URL}")

        logger.info(f"OpenAI-compatible LLM initialized (model: {settings.LLM_MODEL})")
        return llm

    except Exception as e:
        logger.error(f"Failed to initialize OpenAI-compatible LLM: {e}")
        raise LLMError(f"OpenAI-compatible LLM initialization failed: {str(e)}")


async def get_mixtral_llm() -> BaseLLM:
    """Get Mixtral LLM instance via configured endpoint."""
    try:
        llm = MixtralLLM(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL,
            temperature=settings.OLLAMA_TEMPERATURE,
            max_tokens=settings.OLLAMA_MAX_TOKENS,
            timeout=settings.OLLAMA_TIMEOUT,
        )

        # Test connection
        connection_ok = await llm.test_connection()
        if not connection_ok:
            raise LLMError(f"Could not connect to Mixtral at {settings.OLLAMA_BASE_URL}")

        logger.info(f"Mixtral LLM initialized via {settings.OLLAMA_BASE_URL}")
        return llm

    except Exception as e:
        logger.error(f"Failed to initialize Mixtral LLM: {e}")
        raise LLMError(f"Mixtral LLM initialization failed: {str(e)}")


async def get_openai_llm() -> BaseLLM:
    """Get OpenAI LLM instance."""
    if not settings.OPENAI_API_KEY:
        raise LLMError("OpenAI API key not configured")

    try:
        llm = OpenAILLM(
            api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_MODEL,
            temperature=settings.OPENAI_TEMPERATURE,
            max_tokens=settings.OPENAI_MAX_TOKENS,
        )

        # Test connection
        connection_ok = await llm.test_connection()
        if not connection_ok:
            raise LLMError("Could not connect to OpenAI API")

        logger.info("OpenAI LLM initialized")
        return llm

    except Exception as e:
        logger.error(f"Failed to initialize OpenAI LLM: {e}")
        raise LLMError(f"OpenAI LLM initialization failed: {str(e)}")
