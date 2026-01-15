"""
Translation helper functions to eliminate code duplication.
Centralizes translation logic for all chat endpoints.
Includes GDPR-compliant consent enforcement.
Includes async semaphore for concurrency control.
"""

import asyncio
import time
from datetime import datetime
from typing import Callable, Dict, Any, Optional
from uuid import UUID

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.external.translation_client import get_translation_client
from app.services.analytics.integration import track_chat_analytics
from app.services.memory.session import get_session_manager
from app.services.tracing import set_analytics_consent
from app.core.dependencies import get_semaphore_manager
from app.utils.logger import get_logger
from app.constants import MAX_TRACE_OUTPUT_LENGTH

logger = get_logger(__name__)


async def _process_without_tracing_inner(
    request: ChatRequest,
    orchestration_fn: Callable,
    conversation_type: str,
    start_time: float,
    translation_client,
    session_id: Optional[UUID] = None,
    **orchestrator_kwargs
) -> ChatResponse:
    """
    Inner processing function for when user declines analytics consent.
    This is called from within the semaphore context.
    """
    # Step 1: Input Translation (auto-detect → English)
    english_message, detected_language = await translation_client.translate_to_english(request.message)
    logger.info(f"🌍 Detected language: {detected_language} | Requested: {request.language}")

    # Step 2: Process with English message only (RAG in English)
    if session_id:
        response = await orchestration_fn(
            message=english_message,
            session_id=session_id,
            language="en",
            **orchestrator_kwargs
        )
    else:
        response = await orchestration_fn(
            initial_message=english_message,
            user_id="anonymous",
            language="en",
            **orchestrator_kwargs
        )

    # Reset session timer
    try:
        session_manager = get_session_manager()
        response_session_id = session_id if session_id else response.session_id
        if response_session_id:
            session = await session_manager.get_session(response_session_id)
            if session:
                session.last_activity_time = datetime.now()
                await session_manager.update_session(response_session_id, session, update_activity=True)
    except Exception as e:
        logger.warning(f"Failed to reset session timer: {e}")

    # Step 3: Output Translation
    target_language = detected_language if detected_language != "en" else request.language
    if target_language != "en":
        response = await translate_response_to_language(response, target_language)

    # Step 4: Track Analytics (even without tracing)
    response_time = time.perf_counter() - start_time
    await track_chat_analytics(
        query=english_message,
        response=response.dict(),
        session_id=str(session_id) if session_id else str(response.session_id),
        user_id="anonymous",
        language=target_language,
        difficulty_level=request.difficulty_level or "low",
        response_time=response_time,
        conversation_type=conversation_type
    )

    # Record response time
    try:
        from app.services.database.stats_database import get_stats_database
        stats_db = await get_stats_database()
        await stats_db.record_response_time(response_time)
    except Exception as e:
        logger.warning(f"Failed to record response time in stats database: {e}")

    return response


async def translate_response_to_language(
    response: ChatResponse,
    target_language: str,
) -> ChatResponse:
    """
    Translate response content to target language.

    Args:
        response: The chat response to translate
        target_language: Target language code (e.g., 'it', 'pt', 'el')

    Returns:
        Updated ChatResponse with translated content
    """
    if target_language == "en":
        return response

    translation_client = get_translation_client()

    try:
        # Prepare title for translation (might be empty for continue conversations)
        title_to_translate = response.title if (hasattr(response, 'title') and response.title) else ""

        # Prepare social tipping point dict for translation
        stp_dict = None
        if response.social_tipping_point:
            if hasattr(response.social_tipping_point, 'text'):
                stp_dict = {
                    "text": response.social_tipping_point.text,
                    "qualifying_factors": response.social_tipping_point.qualifying_factors
                }
            elif isinstance(response.social_tipping_point, dict):
                stp_dict = response.social_tipping_point

        # Batch translate all content at once
        translated_batch = await translation_client.translate_batch_from_english(
            title=title_to_translate,
            response=response.response,
            target_language=target_language,
            social_tipping_point=stp_dict
        )

        # Update response with translated content
        if title_to_translate:
            response.title = translated_batch["title"]
        response.response = translated_batch["response"]

        # Update social tipping point if present
        if translated_batch.get("social_tipping_point"):
            stp_translated = translated_batch["social_tipping_point"]
            if hasattr(response.social_tipping_point, 'text'):
                response.social_tipping_point.text = stp_translated.get(
                    "text",
                    response.social_tipping_point.text
                )
                response.social_tipping_point.qualifying_factors = stp_translated.get(
                    "qualifying_factors",
                    response.social_tipping_point.qualifying_factors
                )

        logger.info(f"✅ Batch translated to {target_language}")

    except Exception as translation_error:
        logger.error(f"Batch translation error: {translation_error}")
        # Continue with English version if translation fails

    return response


async def process_with_translation(
    request: ChatRequest,
    orchestration_fn: Callable,
    conversation_type: str,
    session_id: Optional[UUID] = None,
    **orchestrator_kwargs
) -> ChatResponse:
    """
    Centralized translation workflow for chat endpoints with semaphore control.

    Workflow:
    1. Acquire chat processing semaphore (limit concurrent chat requests)
    2. Detect input language and translate to English
    3. Process with RAG pipeline (always in English)
    4. Translate response back to user's language
    5. Track analytics

    Args:
        request: The chat request
        orchestration_fn: The orchestrator function to call (start_new_conversation or continue_conversation)
        conversation_type: "start" or "continue"
        session_id: Optional session ID for continue conversations
        **orchestrator_kwargs: Additional arguments to pass to orchestration function

    Returns:
        Translated ChatResponse

    Raises:
        TimeoutError: If semaphore cannot be acquired (system overloaded)
    """
    start_time = time.perf_counter()
    semaphore_manager = get_semaphore_manager()

    # Acquire chat semaphore to limit concurrent processing
    logger.info(f"🔒 Waiting for chat semaphore (type: {conversation_type})...")
    async with semaphore_manager.chat_semaphore:
        logger.info(f"✅ Chat semaphore acquired (type: {conversation_type})")

        translation_client = get_translation_client()

        # GDPR: Set analytics consent for this request context
        analytics_consent = True  # Default: ON (opt-out model)
        if request.consent_metadata:
            analytics_consent = request.consent_metadata.analytics_consent

        set_analytics_consent(analytics_consent)
        logger.info(f"📊 Analytics consent for this request: {analytics_consent}")

        # Step 1: Input Translation (auto-detect → English)
        english_message, detected_language = await translation_client.translate_to_english(request.message)

        logger.info(f"🌍 Detected language: {detected_language} | Requested: {request.language}")

        # Step 2: Process with English message only (RAG in English)
        if session_id:
            # Continue conversation
            response = await orchestration_fn(
                message=english_message,
                session_id=session_id,
                language="en",
                **orchestrator_kwargs
            )
        else:
            # Start new conversation
            response = await orchestration_fn(
                initial_message=english_message,
                user_id="anonymous",
                language="en",
                **orchestrator_kwargs
            )

        # Reset session timer after response generation (timer starts when response is ready)
        try:
            session_manager = get_session_manager()
            response_session_id = session_id if session_id else response.session_id
            if response_session_id:
                session = await session_manager.get_session(response_session_id)
                if session:
                    session.last_activity_time = datetime.now()
                    await session_manager.update_session(response_session_id, session, update_activity=True)
                    logger.debug(f"Session timer reset after response generation: {response_session_id}")
        except Exception as e:
            logger.warning(f"Failed to reset session timer: {e}")

        # Step 3: Output Translation (English → user's detected or requested language)
        target_language = detected_language if detected_language != "en" else request.language

        if target_language != "en":
            response = await translate_response_to_language(response, target_language)

        # Step 4: Track Analytics
        response_time = time.perf_counter() - start_time

        await track_chat_analytics(
            query=english_message,
            response=response.dict(),
            session_id=str(session_id) if session_id else str(response.session_id),
            user_id="anonymous",
            language=target_language,
            difficulty_level=request.difficulty_level or "low",
            response_time=response_time,
            conversation_type=conversation_type
        )

        # Record response time in stats database
        try:
            from app.services.database.stats_database import get_stats_database
            stats_db = await get_stats_database()
            await stats_db.record_response_time(response_time)
        except Exception as e:
            logger.warning(f"Failed to record response time in stats database: {e}")

        logger.info(f"🔓 Chat semaphore released (type: {conversation_type})")
        return response


async def process_with_translation_and_tracing(
    request: ChatRequest,
    orchestration_fn: Callable,
    conversation_type: str,
    langfuse_span_name: str,
    session_id: Optional[UUID] = None,
    **orchestrator_kwargs
) -> ChatResponse:
    """
    Centralized translation workflow with Langfuse tracing and semaphore control.

    Same as process_with_translation but includes Langfuse tracing.

    Args:
        request: The chat request
        orchestration_fn: The orchestrator function to call
        conversation_type: "start" or "continue"
        langfuse_span_name: Name for the Langfuse span
        session_id: Optional session ID for continue conversations
        **orchestrator_kwargs: Additional arguments to pass to orchestration function

    Returns:
        Translated ChatResponse

    Raises:
        TimeoutError: If semaphore cannot be acquired (system overloaded)
    """
    from app.services.tracing import get_langfuse_client

    start_time = time.perf_counter()
    semaphore_manager = get_semaphore_manager()

    # Acquire chat semaphore to limit concurrent processing
    logger.info(f"🔒 Waiting for chat semaphore with tracing (type: {conversation_type})...")
    async with semaphore_manager.chat_semaphore:
        logger.info(f"✅ Chat semaphore acquired with tracing (type: {conversation_type})")

        translation_client = get_translation_client()
        langfuse_client = get_langfuse_client()

        # GDPR: Extract and set analytics consent for this request context
        consent_metadata = {}
        analytics_consent = True  # Default: ON (opt-out model)

        if request.consent_metadata:
            consent_metadata = {
                "consent_given": request.consent_metadata.consent_given,
                "analytics_consent": request.consent_metadata.analytics_consent,
                "consent_version": request.consent_metadata.consent_version,
                "consent_timestamp": request.consent_metadata.consent_timestamp
            }
            analytics_consent = request.consent_metadata.analytics_consent

        # Set consent in context - this will affect ALL trace creation in the call stack
        set_analytics_consent(analytics_consent)
        logger.info(f"📊 Analytics consent for this request: {analytics_consent}")

        # Check if user has consented to analytics/tracing (GDPR compliance)
        if not analytics_consent:
            logger.info(f"⚠️  User declined analytics consent - processing without traces")
            # Release semaphore and process without tracing
            # Note: We're already inside the semaphore context, so it will be released after this returns
            return await _process_without_tracing_inner(
                request=request,
                orchestration_fn=orchestration_fn,
                conversation_type=conversation_type,
                session_id=session_id,
                start_time=start_time,
                translation_client=translation_client,
                **orchestrator_kwargs
            )

        with langfuse_client.start_as_current_span(
            name=langfuse_span_name,
            input=request.message,
            metadata={
                "api_endpoint": conversation_type,
                "session_id": str(session_id) if session_id else "new",
                "frontend_language": request.language,
                "include_sources": request.include_sources,
                "translation_flow": "auto_detect_then_batch",
                **consent_metadata
            }
        ) as main_span:

            # Update trace with session info
            trace_session_id = str(session_id) if session_id else f"{conversation_type}_{int(time.time())}"
            main_span.update_trace(
                session_id=trace_session_id,
                user_id="anonymous",
                input=request.message,
                metadata={
                    "api_endpoint": conversation_type,
                    "session_id": str(session_id) if session_id else "new",
                    "original_message": request.message,
                    **consent_metadata
                }
            )

            try:
                # Step 1: Input Translation
                english_message, detected_language = await translation_client.translate_to_english(request.message)
                logger.info(f"🌍 Detected language: {detected_language} | Requested: {request.language}")

                # Step 2: Process
                if session_id:
                    response = await orchestration_fn(
                        message=english_message,
                        session_id=session_id,
                        language="en",
                        **orchestrator_kwargs
                    )
                else:
                    response = await orchestration_fn(
                        initial_message=english_message,
                        user_id="anonymous",
                        language="en",
                        **orchestrator_kwargs
                    )

                # Reset session timer after response generation (timer starts when response is ready)
                try:
                    session_manager = get_session_manager()
                    response_session_id = session_id if session_id else response.session_id
                    if response_session_id:
                        session = await session_manager.get_session(response_session_id)
                        if session:
                            session.last_activity_time = datetime.now()
                            await session_manager.update_session(response_session_id, session, update_activity=True)
                            logger.debug(f"Session timer reset after response generation: {response_session_id}")
                except Exception as e:
                    logger.warning(f"Failed to reset session timer: {e}")

                # Step 3: Output Translation
                target_language = detected_language if detected_language != "en" else request.language

                if target_language != "en":
                    response = await translate_response_to_language(response, target_language)

                # Step 4: Track Analytics
                response_time = time.perf_counter() - start_time

                await track_chat_analytics(
                    query=english_message,
                    response=response.dict(),
                    session_id=str(session_id) if session_id else str(response.session_id),
                    user_id="anonymous",
                    language=target_language,
                    difficulty_level=request.difficulty_level or "low",
                    response_time=response_time,
                    conversation_type=conversation_type
                )

                # Record response time
                try:
                    from app.services.database.stats_database import get_stats_database
                    stats_db = await get_stats_database()
                    await stats_db.record_response_time(response_time)
                except Exception as e:
                    logger.warning(f"Failed to record response time in stats database: {e}")

                # Update Langfuse span
                main_span.update(
                    output=response.response[:MAX_TRACE_OUTPUT_LENGTH],
                    metadata={
                        "session_id": str(session_id) if session_id else str(response.session_id),
                        "api_success": True,
                        "sources_count": len(response.sources),
                        "response_time": response_time,
                        "detected_language": detected_language,
                        "target_language": target_language,
                        "english_message": english_message,
                        "translation_applied": target_language != "en"
                    }
                )

                main_span.update_trace(
                    output=response.response[:MAX_TRACE_OUTPUT_LENGTH],
                    session_id=str(session_id) if session_id else str(response.session_id),
                    metadata={
                        "api_success": True,
                        "sources_count": len(response.sources),
                        "translation_traced": True,
                        **consent_metadata
                    }
                )

                logger.info(f"🔓 Chat semaphore released with tracing (type: {conversation_type})")
                return response

            except Exception as e:
                main_span.update(
                    output=f"Error: {str(e)}",
                    level="ERROR",
                    metadata={"api_success": False, "error": str(e)}
                )

                main_span.update_trace(
                    output=f"Error: {str(e)}",
                    metadata={"api_success": False}
                )

                raise
