"""
Refactored chat API endpoints with centralized translation flow.
All translation logic extracted to helpers/translation.py
Reduced from 631 lines to ~150 lines (76% reduction)
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import validate_session
from app.core.auth_middleware import require_auth
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ConversationSummary,
    SessionListResponse,
)
from app.services.conversation.orchestrator import get_conversation_orchestrator
from app.services.tracing import is_langfuse_enabled
from app.api.v1.helpers.translation import (
    process_with_translation,
    process_with_translation_and_tracing,
)
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.post("/start", response_model=ChatResponse)
async def start_conversation(
    request: ChatRequest,
    token: str = Depends(require_auth),
    orchestrator = Depends(get_conversation_orchestrator),
) -> ChatResponse:
    """
    Start a new conversation with automatic language detection and translation.

    Requires Authentication.

    Flow:
    1. Auto-detect input language → translate to English
    2. Process with RAG pipeline (English only)
    3. Translate response to user's language
    4. Track analytics
    """
    try:
        if is_langfuse_enabled():
            return await process_with_translation_and_tracing(
                request=request,
                orchestration_fn=orchestrator.start_new_conversation,
                conversation_type="start",
                langfuse_span_name="start_conversation_api",
                difficulty_level=request.difficulty_level or "low",
                include_sources=request.include_sources
            )
        else:
            return await process_with_translation(
                request=request,
                orchestration_fn=orchestrator.start_new_conversation,
                conversation_type="start",
                difficulty_level=request.difficulty_level or "low",
                include_sources=request.include_sources
            )
    except Exception as e:
        logger.error(f"Error starting conversation: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start conversation"
        )


@router.post("/continue/{session_id}", response_model=ChatResponse)
async def continue_conversation(
    session_id: UUID,
    request: ChatRequest,
    token: str = Depends(require_auth),
    orchestrator = Depends(get_conversation_orchestrator),
) -> ChatResponse:
    """
    Continue an existing conversation with automatic translation.

    Requires Authentication.

    Flow:
    1. Auto-detect input language → translate to English
    2. Process with RAG pipeline (English only)
    3. Translate response to user's language
    4. Track analytics
    """
    try:
        if is_langfuse_enabled():
            return await process_with_translation_and_tracing(
                request=request,
                orchestration_fn=orchestrator.continue_conversation,
                conversation_type="continue",
                langfuse_span_name="continue_conversation_api",
                session_id=session_id,
                difficulty_level=request.difficulty_level,
                include_sources=request.include_sources
            )
        else:
            return await process_with_translation(
                request=request,
                orchestration_fn=orchestrator.continue_conversation,
                conversation_type="continue",
                session_id=session_id,
                difficulty_level=request.difficulty_level,
                include_sources=request.include_sources
            )
    except Exception as e:
        logger.error(f"Error continuing conversation: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to continue conversation"
        )


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    user_id: str = "anonymous",
    limit: int = 50,
    orchestrator = Depends(get_conversation_orchestrator),
) -> SessionListResponse:
    """List user's chat sessions"""
    try:
        conversations = await orchestrator.get_user_conversations(user_id, limit)

        summaries = [
            ConversationSummary(
                session_id=conv["session_id"],
                title=conv["title"],
                summary="",
                message_count=conv["message_count"],
                last_activity=conv["last_activity"],
                language=conv["language"],
            )
            for conv in conversations
        ]

        return SessionListResponse(sessions=summaries)

    except Exception as e:
        logger.error(f"Error listing sessions: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list sessions"
        )


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: UUID = Depends(validate_session),
    limit: Optional[int] = None,
    orchestrator = Depends(get_conversation_orchestrator),
):
    """Get messages from a session"""
    try:
        messages = await orchestrator.get_conversation_history(session_id, limit)

        clean_messages = [
            {
                "id": str(msg.id),
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat()
            }
            for msg in messages
        ]

        return {"messages": clean_messages}

    except Exception as e:
        logger.error(f"Error getting messages: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get messages"
        )


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: UUID = Depends(validate_session),
    orchestrator = Depends(get_conversation_orchestrator),
):
    """Delete a chat session"""
    try:
        success = await orchestrator.delete_conversation(session_id)

        if success:
            return {"success": True, "message": "Session deleted successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete session"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete session"
        )
