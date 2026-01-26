"""LLM factory for creating different LLM instances."""

import logging
from typing import Optional

from langchain.llms.base import BaseLLM

from app.config import get_settings
from app.core.exceptions import LLMError
from app.services.llm.mixtral import MixtralLLM
from app.services.llm.openai import OpenAILLM
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


async def get_llm(provider: Optional[str] = None) -> BaseLLM:
    """Get LLM instance based on configuration or provider preference."""
    
    # Try OpenAI first if API key is available
    if provider == "openai" or (not provider and settings.OPENAI_API_KEY):
        try:
            return await get_openai_llm()
        except Exception as e:
            logger.warning(f"Failed to initialize OpenAI LLM: {e}")
            if provider == "openai":
                # If explicitly requested OpenAI, don't fallback
                raise LLMError(f"OpenAI LLM requested but failed: {str(e)}")
            # Otherwise fallback to Mixtral
            logger.info("Falling back to Mixtral LLM")
    
    # Try Mixtral/Bedrock
    try:
        return await get_mixtral_llm()
    except Exception as e:
        logger.error(f"Failed to initialize Bedrock LLM: {e}")
        if provider == "mixtral" or provider == "bedrock":
            raise LLMError(f"Bedrock LLM initialization failed: {str(e)}")
        
        # If we haven't tried OpenAI yet and we have a key, try it as last resort
        if not provider and settings.OPENAI_API_KEY:
            try:
                logger.info("Trying OpenAI as last resort")
                return await get_openai_llm()
            except Exception as openai_e:
                logger.error(f"OpenAI fallback also failed: {openai_e}")
        
        raise LLMError(f"No LLM could be initialized. Mixtral error: {str(e)}")


async def get_mixtral_llm() -> BaseLLM:
    """Get Mixtral LLM instance via Bedrock (OpenAI-compatible) endpoint."""
    try:
        llm = MixtralLLM(
            base_url=settings.BEDROCK_API_URL,
            api_key=settings.BEDROCK_API_KEY,
            model=settings.BEDROCK_MODEL,
            temperature=settings.BEDROCK_TEMPERATURE,
            max_tokens=settings.BEDROCK_MAX_TOKENS,
            timeout=settings.BEDROCK_TIMEOUT,
        )

        # Test connection
        connection_ok = await llm.test_connection()
        if not connection_ok:
            raise LLMError(f"Could not connect to Bedrock at {settings.BEDROCK_API_URL}")

        logger.info(f"✅ Bedrock LLM initialized via {settings.BEDROCK_API_URL}")
        return llm

    except Exception as e:
        logger.error(f"Failed to initialize Bedrock LLM: {e}")
        raise LLMError(f"Bedrock LLM initialization failed: {str(e)}")


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
            
        logger.info("✅ OpenAI LLM initialized")
        return llm
        
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI LLM: {e}")
        raise LLMError(f"OpenAI LLM initialization failed: {str(e)}")