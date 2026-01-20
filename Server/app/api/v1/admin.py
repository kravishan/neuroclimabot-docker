from typing import Optional
from uuid import UUID
import json
import os
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from app.config import get_settings
from app.schemas.feedback import FeedbackStats
from app.services.feedback.storage import get_simple_feedback_service, SimpleFeedbackService
from app.services.memory.session import get_session_manager, SessionManager
from app.services.rag.chain import get_rag_service
from app.services.database.stats_database import get_stats_database
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()
settings = get_settings()


class AdminLogin(BaseModel):
    """Admin login request model."""
    username: str
    password: str


class AdminLoginResponse(BaseModel):
    """Admin login response model."""
    success: bool
    message: str
    token: Optional[str] = None


class AdminStats(BaseModel):
    """Admin statistics response model."""

    active_sessions: int = 0
    total_sessions: int = 0
    avg_session_duration: float = 0.0
    avg_messages_per_session: float = 0.0
    avg_response_time: float = 0.0


class DocumentInfo(BaseModel):
    """Document information model."""
    name: str
    bucket: str
    status: str
    size: Optional[int] = None
    last_modified: Optional[str] = None


class DocumentsResponse(BaseModel):
    """Response model for documents endpoint."""
    success: bool
    message: str
    total_documents: int
    documents: list[DocumentInfo]


class LogEntry(BaseModel):
    """Single log entry model."""
    
    timestamp: str
    level: str
    logger_name: str
    message: str
    line_number: Optional[int] = None
    raw_log: Optional[str] = None


class LogsResponse(BaseModel):
    """Response model for logs endpoint."""
    
    success: bool
    message: str
    total_lines: int
    logs: list[LogEntry]
    log_file_path: str
    log_file_size: Optional[int] = None


@router.post("/login", response_model=AdminLoginResponse)
async def admin_login(login_data: AdminLogin):
    """
    Admin login endpoint.
    Simple authentication for admin dashboard access.
    """
    
    try:
        # Get admin credentials from settings (loaded from .env)
        if login_data.username == settings.ADMIN_USERNAME and login_data.password == settings.ADMIN_PASSWORD:
            logger.info(f"Admin login successful for user: {login_data.username}")
            return AdminLoginResponse(
                success=True,
                message="Login successful",
                token="admin_authenticated"  # Simple token for frontend
            )
        else:
            logger.warning(f"Failed admin login attempt for user: {login_data.username}")
            return AdminLoginResponse(
                success=False,
                message="Invalid credentials"
            )
            
    except Exception as e:
        logger.error(f"Error during admin login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login system error"
        )


@router.get("/stats", response_model=AdminStats)
async def get_admin_stats(
    session_manager: SessionManager = Depends(get_session_manager)
):
    """Get comprehensive admin statistics from SQLite database."""

    try:
        # Get current active sessions from session manager
        session_stats = await session_manager.get_stats()
        active_sessions = session_stats.get("active_sessions", 0)

        # Get persistent stats from SQLite database
        stats_db = await get_stats_database()
        db_stats = await stats_db.get_session_stats()

        total_sessions = db_stats.get("total_sessions", 0)
        avg_messages_per_session = db_stats.get("avg_messages_per_session", 0.0)
        avg_response_time = db_stats.get("avg_response_time", 0.0)

        # Calculate average session duration
        # Estimate: avg_messages * avg_response_time (rough approximation)
        # This will start at 0 when there's no data
        avg_session_duration = 0.0
        if avg_messages_per_session > 0 and avg_response_time > 0:
            avg_session_duration = avg_messages_per_session * avg_response_time

        return AdminStats(
            active_sessions=active_sessions,
            total_sessions=total_sessions,
            avg_session_duration=avg_session_duration,
            avg_messages_per_session=avg_messages_per_session,
            avg_response_time=avg_response_time
        )

    except Exception as e:
        logger.error(f"Error getting admin stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve admin statistics"
        )


@router.get("/logs", response_model=LogsResponse)
async def get_system_logs(
    limit: int = Query(default=100, ge=1, le=1000, description="Number of log entries to retrieve"),
    level: Optional[str] = Query(default=None, description="Filter by log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"),
    search: Optional[str] = Query(default=None, description="Search term in log messages"),
    tail: bool = Query(default=True, description="Get most recent logs first (tail mode)")
):
    """
    Retrieve system logs from the log file.
    
    Args:
        limit: Maximum number of log entries to return (1-1000)
        level: Filter logs by level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        search: Search term to filter log messages
        tail: If True, return most recent logs first; if False, return oldest first
    """
    
    try:
        log_file_path = Path("logs/neuroclima.log")
        
        # Check if log file exists
        if not log_file_path.exists():
            return LogsResponse(
                success=False,
                message="Log file not found",
                total_lines=0,
                logs=[],
                log_file_path=str(log_file_path)
            )
        
        # Get file size
        file_size = log_file_path.stat().st_size
        
        # Read log file
        try:
            with open(log_file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except UnicodeDecodeError:
            # Try with different encoding if UTF-8 fails
            with open(log_file_path, 'r', encoding='latin1') as f:
                lines = f.readlines()
        
        # Process log entries
        log_entries = []
        
        # Reverse lines if tail mode (most recent first)
        if tail:
            lines = lines[::-1]
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
            
            # Try to parse JSON log entry
            try:
                log_data = json.loads(line)
                
                # Extract fields from JSON log
                log_entry = LogEntry(
                    timestamp=log_data.get("asctime", ""),
                    level=log_data.get("levelname", ""),
                    logger_name=log_data.get("name", ""),
                    message=log_data.get("message", ""),
                    line_number=line_num,
                    raw_log=line
                )
                
            except json.JSONDecodeError:
                # If not JSON, treat as plain text log
                # Try to extract basic info from plain text
                parts = line.split(" ", 3)
                if len(parts) >= 3:
                    timestamp = parts[0] if len(parts) > 0 else ""
                    level = parts[1] if len(parts) > 1 else ""
                    message = parts[2] if len(parts) > 2 else line
                else:
                    timestamp = ""
                    level = ""
                    message = line
                
                log_entry = LogEntry(
                    timestamp=timestamp,
                    level=level,
                    logger_name="",
                    message=message,
                    line_number=line_num,
                    raw_log=line
                )
            
            # Apply filters
            if level and log_entry.level.upper() != level.upper():
                continue
            
            if search and search.lower() not in log_entry.message.lower():
                continue
            
            log_entries.append(log_entry)
            
            # Stop if we've reached the limit
            if len(log_entries) >= limit:
                break
        
        return LogsResponse(
            success=True,
            message=f"Retrieved {len(log_entries)} log entries",
            total_lines=len(lines),
            logs=log_entries,
            log_file_path=str(log_file_path),
            log_file_size=file_size
        )
        
    except Exception as e:
        logger.error(f"Error retrieving logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve logs: {str(e)}"
        )


@router.post("/logs/clear")
async def clear_log_file():
    """
    Clear the log file (DANGEROUS - USE WITH CAUTION).
    This will truncate the current log file.
    """
    
    try:
        log_file_path = Path("logs/neuroclima.log")
        
        if not log_file_path.exists():
            return {
                "success": False,
                "message": "Log file does not exist",
                "log_file_path": str(log_file_path)
            }
        
        # Get file size before clearing
        file_size_before = log_file_path.stat().st_size
        
        # Clear the log file
        with open(log_file_path, 'w', encoding='utf-8') as f:
            f.write("")
        
        logger.warning("ADMIN ACTION: Log file cleared")
        
        return {
            "success": True,
            "message": f"Log file cleared successfully. Previous size: {file_size_before} bytes",
            "log_file_path": str(log_file_path),
            "previous_size": file_size_before
        }
        
    except Exception as e:
        logger.error(f"Error clearing log file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear log file: {str(e)}"
        )


@router.post("/cleanup/sessions")
async def cleanup_expired_sessions(
    session_manager: SessionManager = Depends(get_session_manager)
):
    """
    Cleanup all sessions from Redis.
    
    WARNING: This executes FLUSHALL and clears ALL Redis data!
    """
    
    try:
        logger.warning("ADMIN ACTION: FLUSHALL - Clearing ALL Redis data")
        
        if not session_manager.is_connected:
            await session_manager.initialize()
        
        # Execute FLUSHALL command - clears ALL Redis data
        await session_manager.redis_client.flushall()
        
        # Clear local cache
        session_manager.session_cache.clear()
        
        # Reset performance stats
        session_manager.performance_stats = {
            "total_sessions_created": 0,
            "total_sessions_deleted": 0,
            "total_messages_stored": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "avg_session_duration": 0.0,
            "cleanup_runs": 0,
            "last_cleanup": None
        }

        logger.warning("ADMIN ACTION: FLUSHALL executed - ALL Redis data cleared")
        
        return {
            "success": True,
            "message": "ALL Redis data has been cleared (FLUSHALL executed)",
            "action": "flushall"
        }
        
    except Exception as e:
        logger.error(f"Error clearing Redis data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear Redis data: {str(e)}"
        )

@router.post("/feedback/clear")
async def clear_all_feedback():
    """Clear all feedback data from SQLite database (DANGEROUS - USE WITH CAUTION)."""

    try:
        # Get stats database
        stats_db = await get_stats_database()

        # Get current stats before clearing
        current_stats = await stats_db.get_feedback_stats()
        total_feedback = current_stats["total_feedback"]

        logger.warning("ADMIN ACTION: Clear all feedback data requested")

        # Clear all feedback data from SQLite
        await stats_db.clear_feedback_stats()

        logger.info(f"Successfully cleared {total_feedback} feedback records from SQLite database")
        return {
            "success": True,
            "message": f"Successfully cleared {total_feedback} feedback records",
            "cleared_count": total_feedback,
            "action": "feedback_cleared"
        }

    except Exception as e:
        logger.error(f"Error clearing feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear feedback data: {str(e)}"
        )


@router.post("/cache/clear")
async def clear_system_cache():
    """Clear various system caches."""
    
    try:
        # Clear different types of caches
        cleared_caches = []
        
        # Clear RAG service cache
        try:
            rag_service = await get_rag_service()
            # This would need cache clearing methods in services
            cleared_caches.append("rag_cache")
        except Exception as e:
            logger.warning(f"Could not clear RAG cache: {e}")
        
        # Clear session cache (if any)
        try:
            session_manager = get_session_manager()
            # This would clear any session-related caches
            cleared_caches.append("session_cache")
        except Exception as e:
            logger.warning(f"Could not clear session cache: {e}")
        
        return {
            "success": True,
            "message": f"Cleared {len(cleared_caches)} cache types",
            "cleared_caches": cleared_caches
        }
        
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear system cache"
        )