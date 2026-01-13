"""
Refactored chat API endpoints with centralized translation flow.
All translation logic extracted to helpers/translation.py
Reduced from 631 lines to ~150 lines (76% reduction)
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status

from app.core.dependencies import validate_session
from app.core.auth_middleware import require_auth
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ConversationSummary,
    SessionListResponse,
)
from app.services.conversation.orchestrator import get_conversation_orchestrator
from app.services.memory.session import get_session_manager
from app.services.tracing import is_langfuse_enabled
from app.api.v1.helpers.translation import (
    process_with_translation,
    process_with_translation_and_tracing,
)
from app.utils.logger import get_logger
from app.config.database import get_redis_config

router = APIRouter()
logger = get_logger(__name__)

# Get session timeout configuration
redis_config = get_redis_config()
SESSION_TIMEOUT_SECONDS = redis_config.SESSION_TIMEOUT_MINUTES * 60


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


@router.post("/sessions/{session_id}/activity")
async def record_activity(
    session_id: UUID = Depends(validate_session),
):
    """Record user activity to reset session timeout"""
    try:
        session_manager = get_session_manager()
        session = await session_manager.get_session(session_id)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )

        # Update session activity
        session.last_activity_time = datetime.now()
        success = await session_manager.update_session(session_id, session, update_activity=True)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update activity"
            )

        # Calculate remaining time
        elapsed = (datetime.now() - session.last_activity_time).total_seconds()
        remaining_seconds = max(0, SESSION_TIMEOUT_SECONDS - elapsed)

        return {
            "success": True,
            "session_id": str(session_id),
            "last_activity": session.last_activity_time.isoformat(),
            "remaining_seconds": int(remaining_seconds)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recording activity for session {session_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record activity"
        )


@router.websocket("/sessions/{session_id}/ws")
async def session_status_websocket(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time session status updates.

    Sends countdown updates every second and handles session timeout.
    Client can send activity pings to reset the timer.
    """
    await websocket.accept()
    logger.info(f"WebSocket connected for session {session_id}")

    try:
        # Validate session exists
        try:
            session_uuid = UUID(session_id)
        except ValueError:
            await websocket.send_json({
                "type": "error",
                "message": "Invalid session ID"
            })
            await websocket.close()
            return

        session_manager = get_session_manager()
        session = await session_manager.get_session(session_uuid)

        if not session:
            await websocket.send_json({
                "type": "error",
                "message": "Session not found"
            })
            await websocket.close()
            return

        # Send initial connection success
        await websocket.send_json({
            "type": "connected",
            "session_id": session_id,
            "timeout_seconds": SESSION_TIMEOUT_SECONDS
        })

        # Start monitoring loop
        async def send_status_updates():
            """Send session status updates every second"""
            while True:
                try:
                    # Get fresh session data
                    session = await session_manager.get_session(session_uuid)

                    if not session:
                        # Session was deleted
                        await websocket.send_json({
                            "type": "session_expired",
                            "message": "Session no longer exists"
                        })
                        break

                    # Calculate remaining time
                    elapsed = (datetime.now() - session.last_activity_time).total_seconds()
                    remaining_seconds = max(0, SESSION_TIMEOUT_SECONDS - elapsed)

                    # Check if session expired
                    if remaining_seconds <= 0:
                        # Delete the session
                        await session_manager.delete_session(session_uuid)

                        await websocket.send_json({
                            "type": "session_expired",
                            "message": "Session timed out due to inactivity"
                        })
                        break

                    # Send status update
                    minutes = int(remaining_seconds // 60)
                    seconds = int(remaining_seconds % 60)

                    # Determine warning level
                    is_warning = remaining_seconds <= 300  # 5 minutes
                    is_critical = remaining_seconds <= 60  # 1 minute

                    await websocket.send_json({
                        "type": "status_update",
                        "remaining_seconds": int(remaining_seconds),
                        "minutes": minutes,
                        "seconds": seconds,
                        "is_warning": is_warning,
                        "is_critical": is_critical,
                        "last_activity": session.last_activity_time.isoformat()
                    })

                    # Wait 1 second before next update
                    await asyncio.sleep(1)

                except Exception as e:
                    logger.error(f"Error in status update loop: {e}")
                    break

        # Start status update task
        update_task = asyncio.create_task(send_status_updates())

        try:
            # Listen for client messages (activity pings)
            while True:
                data = await websocket.receive_json()

                if data.get("type") == "activity":
                    # Update activity timestamp
                    session = await session_manager.get_session(session_uuid)
                    if session:
                        session.last_activity_time = datetime.now()
                        await session_manager.update_session(session_uuid, session, update_activity=True)

                        logger.debug(f"Activity recorded for session {session_id}")

                        # Send acknowledgment
                        await websocket.send_json({
                            "type": "activity_recorded",
                            "timestamp": datetime.now().isoformat()
                        })

        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected for session {session_id}")
            update_task.cancel()

        except Exception as e:
            logger.error(f"Error in WebSocket message handling: {e}")
            update_task.cancel()

    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except:
            pass

    finally:
        try:
            await websocket.close()
        except:
            pass
        logger.info(f"WebSocket closed for session {session_id}")
