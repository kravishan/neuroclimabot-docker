"""
Session management with Redis backend and Prometheus metrics integration.
"""

import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

import redis.asyncio as redis
from pydantic import BaseModel, Field, field_validator

from app.config.database import get_redis_config
from app.core.exceptions import SessionError
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ChatMessage(BaseModel):
    """Individual chat message with fixed metadata handling."""
    id: UUID = Field(default_factory=uuid4)
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('metadata', mode='before')
    @classmethod
    def validate_metadata(cls, v):
        """Ensure metadata is always a dict, never None."""
        if v is None:
            return {}
        if not isinstance(v, dict):
            return {}
        return v
    
    @field_validator('timestamp', mode='before')
    @classmethod
    def parse_timestamp(cls, v):
        """Handle timestamp parsing from string or datetime."""
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v.replace('Z', '+00:00'))
            except ValueError:
                return datetime.now()
        elif isinstance(v, datetime):
            return v
        else:
            return datetime.now()


class SessionData(BaseModel):
    """Session data model with fixed message validation."""
    id: UUID
    user_id: str
    language: str = "en"
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_activity_time: datetime = Field(default_factory=datetime.now)
    is_active: bool = True
    message_count: int = 0
    messages: List[ChatMessage] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('metadata', mode='before')
    @classmethod
    def validate_metadata(cls, v):
        """Ensure metadata is always a dict, never None."""
        if v is None:
            return {}
        if not isinstance(v, dict):
            return {}
        return v
    
    @field_validator('messages', mode='before')
    @classmethod
    def validate_messages(cls, v):
        """Handle message validation with metadata fixes."""
        if not v:
            return []
        
        validated_messages = []
        for msg in v:
            if isinstance(msg, dict):
                # Ensure metadata is never None
                if msg.get('metadata') is None:
                    msg['metadata'] = {}
                validated_messages.append(msg)
            elif isinstance(msg, ChatMessage):
                validated_messages.append(msg)
        
        return validated_messages
    
    @field_validator('created_at', 'updated_at', 'last_activity_time', mode='before')
    @classmethod
    def parse_timestamp(cls, v):
        """Handle timestamp parsing from string or datetime."""
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v.replace('Z', '+00:00'))
            except ValueError:
                return datetime.now()
        elif isinstance(v, datetime):
            return v
        else:
            return datetime.now()


class SessionManager:
    """Session manager with Redis backend and fixed Pydantic validation."""
    
    def __init__(self):
        self.config = get_redis_config()
        self.redis_client: Optional[redis.Redis] = None
        self.is_connected = False
        
        # Configuration
        self.session_timeout = self.config.SESSION_TIMEOUT_MINUTES * 60  # Convert to seconds
        self.max_conversation_history = self.config.MAX_CONVERSATION_HISTORY
        self.memory_window_size = self.config.MEMORY_WINDOW_SIZE
        
        # Performance tracking
        self.performance_stats = {
            "total_sessions_created": 0,
            "total_sessions_deleted": 0,
            "total_messages_stored": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "avg_session_duration": 0.0,
            "cleanup_runs": 0,
            "last_cleanup": None
        }
        
        # Cache for frequently accessed sessions
        self.session_cache = {}
        self.cache_max_size = 100
        self.cache_ttl = 300  # 5 minutes
    
    async def initialize(self):
        """Initialize Redis connection and metrics."""
        try:
            connection_kwargs = self.config.connection_kwargs
            self.redis_client = redis.from_url(**connection_kwargs)
            
            # Test connection
            await self.redis_client.ping()
            self.is_connected = True
            
            logger.info("✅ Session manager initialized with Redis")
            logger.info(f"Session timeout: {self.session_timeout}s, Max history: {self.max_conversation_history}")
            
        except Exception as e:
            logger.error(f"Failed to initialize session manager: {e}")
            raise SessionError(f"Session manager initialization failed: {str(e)}")
    
    async def create_session(
        self,
        user_id: str = "anonymous",
        language: str = "en",
        title: Optional[str] = None
    ) -> UUID:
        """Create a new session with metrics tracking."""
        if not self.is_connected:
            await self.initialize()
        
        try:
            session_id = uuid4()
            now = datetime.now()

            session_data = SessionData(
                id=session_id,
                user_id=user_id,
                language=language,
                title=title or f"Session {session_id.hex[:8]}",
                created_at=now,
                updated_at=now,
                last_activity_time=now,
                is_active=True,
                message_count=0,
                messages=[],
                metadata={}
            )
            
            # Store session in Redis using model_dump_json for proper serialization
            session_key = self._get_session_key(session_id)
            session_json = session_data.model_dump_json()
            await self.redis_client.setex(session_key, self.session_timeout, session_json)
            
            # Add to user session list
            user_sessions_key = self._get_user_sessions_key(user_id)
            await self.redis_client.lpush(user_sessions_key, str(session_id))
            await self.redis_client.expire(user_sessions_key, self.session_timeout * 2)
            
            # Cache the session locally
            self._cache_session(session_id, session_data)
            
            # Update performance stats
            self.performance_stats["total_sessions_created"] += 1

            # Update stats database
            try:
                from app.services.database.stats_database import get_stats_database
                stats_db = await get_stats_database()
                await stats_db.increment_session_count()
            except Exception as e:
                logger.warning(f"Failed to update session count in stats database: {e}")


            logger.info(f"Created session {session_id} for user {user_id} (language: {language})")
            return session_id
            
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise SessionError(f"Failed to create session: {str(e)}")
    
    async def get_session(self, session_id: UUID) -> Optional[SessionData]:
        """Get session by ID with caching and fixed validation."""
        if not self.is_connected:
            await self.initialize()
        
        try:
            # Check local cache first
            cached_session = self._get_cached_session(session_id)
            if cached_session:
                self.performance_stats["cache_hits"] += 1
                return cached_session
            
            # Get from Redis
            session_key = self._get_session_key(session_id)
            session_data = await self.redis_client.get(session_key)
            
            if session_data:
                try:
                    # Parse JSON data with error handling
                    session_dict = json.loads(session_data)
                    
                    # Fix any None metadata before validation
                    if session_dict.get('metadata') is None:
                        session_dict['metadata'] = {}
                    
                    # Fix messages metadata
                    messages = session_dict.get('messages', [])
                    for msg in messages:
                        if isinstance(msg, dict) and msg.get('metadata') is None:
                            msg['metadata'] = {}
                    
                    # Create SessionData with fixed data
                    session = SessionData.model_validate(session_dict)
                    
                    # Cache the session
                    self._cache_session(session_id, session)
                    
                    self.performance_stats["cache_misses"] += 1
                        
                    return session
                    
                except Exception as validation_error:
                    logger.error(f"Session validation error for {session_id}: {validation_error}")
                    # Clean up corrupted session
                    await self.redis_client.delete(session_key)
                    self.performance_stats["cache_misses"] += 1
                    return None
            else:
                self.performance_stats["cache_misses"] += 1
                return None
                
        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            return None
    
    async def update_session(self, session_id: UUID, session_data: SessionData, update_activity: bool = True) -> bool:
        """Update session data with proper serialization and activity tracking."""
        if not self.is_connected:
            await self.initialize()

        try:
            now = datetime.now()
            session_data.updated_at = now
            if update_activity:
                session_data.last_activity_time = now

            # Update in Redis using model_dump_json
            session_key = self._get_session_key(session_id)
            session_json = session_data.model_dump_json()
            await self.redis_client.setex(session_key, self.session_timeout, session_json)

            # Update cache
            self._cache_session(session_id, session_data)

            return True

        except Exception as e:
            logger.error(f"Failed to update session {session_id}: {e}")
            return False
    
    async def add_message(self, session_id: UUID, message: ChatMessage) -> bool:
        """Add a message to the session with proper validation."""
        if not self.is_connected:
            await self.initialize()
        
        try:
            session = await self.get_session(session_id)
            if not session:
                logger.warning(f"Session {session_id} not found when adding message")
                return False
            
            # Ensure message metadata is not None
            if message.metadata is None:
                message.metadata = {}
            
            # Add message to session
            session.messages.append(message)
            session.message_count = len(session.messages)
            session.updated_at = datetime.now()
            
            # Limit conversation history
            if len(session.messages) > self.max_conversation_history:
                # Keep the most recent messages
                session.messages = session.messages[-self.max_conversation_history:]
                session.message_count = len(session.messages)
                logger.debug(f"Trimmed conversation history for session {session_id}")
            
            # Update session
            success = await self.update_session(session_id, session)
            
            if success:
                self.performance_stats["total_messages_stored"] += 1
                logger.debug(f"Added {message.role} message to session {session_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to add message to session {session_id}: {e}")
            return False
    
    async def delete_session(self, session_id: UUID) -> bool:
        """Delete a session with metrics tracking and improved error handling."""
        if not self.is_connected:
            await self.initialize()
        
        try:
            session_key = self._get_session_key(session_id)
            
            # Get session for cleanup and stats (with error handling)
            user_id = "unknown"
            try:
                session_data = await self.redis_client.get(session_key)
                if session_data:
                    session_dict = json.loads(session_data)
                    user_id = session_dict.get('user_id', 'unknown')

                    # Calculate session duration for stats
                    created_at_str = session_dict.get('created_at')
                    if created_at_str:
                        try:
                            created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                            duration = (datetime.now() - created_at).total_seconds()
                            self._update_avg_session_duration(duration)
                        except ValueError:
                            pass  # Skip duration calculation on parse error

                    # Record message count in stats database
                    message_count = session_dict.get('message_count', 0)
                    if message_count > 0:
                        try:
                            from app.services.database.stats_database import get_stats_database
                            stats_db = await get_stats_database()
                            await stats_db.record_session_message(message_count)
                        except Exception as e:
                            logger.warning(f"Failed to record session messages in stats database: {e}")

                    # Remove from user session list
                    user_sessions_key = self._get_user_sessions_key(user_id)
                    await self.redis_client.lrem(user_sessions_key, 0, str(session_id))
            except Exception as cleanup_error:
                logger.warning(f"Error during session cleanup for {session_id}: {cleanup_error}")
            
            # Delete session from Redis
            result = await self.redis_client.delete(session_key)
            
            # Remove from cache
            self._remove_from_cache(session_id)
            
            # Update performance stats
            if result:
                self.performance_stats["total_sessions_deleted"] += 1
            
            
            if result:
                logger.info(f"Deleted session {session_id}")
                return True
            else:
                logger.warning(f"Session {session_id} not found for deletion")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False
    
    # Rest of the methods remain the same...
    async def get_messages(
        self, 
        session_id: UUID, 
        limit: Optional[int] = None
    ) -> List[ChatMessage]:
        """Get messages from a session."""
        try:
            session = await self.get_session(session_id)
            if not session:
                return []
            
            messages = session.messages
            if limit:
                messages = messages[-limit:]
            
            return messages
            
        except Exception as e:
            logger.error(f"Failed to get messages for session {session_id}: {e}")
            return []
    
    async def list_user_sessions(
        self, 
        user_id: str, 
        limit: int = 50
    ) -> List[SessionData]:
        """List sessions for a user."""
        if not self.is_connected:
            await self.initialize()
        
        try:
            user_sessions_key = self._get_user_sessions_key(user_id)
            session_ids = await self.redis_client.lrange(user_sessions_key, 0, limit - 1)
            
            sessions = []
            for session_id_str in session_ids:
                try:
                    session_id = UUID(session_id_str)
                    session = await self.get_session(session_id)
                    if session and session.is_active:
                        sessions.append(session)
                except (ValueError, TypeError):
                    # Invalid UUID, skip
                    continue
            
            # Sort by updated_at (most recent first)
            sessions.sort(key=lambda s: s.updated_at, reverse=True)
            
            return sessions
            
        except Exception as e:
            logger.error(f"Failed to list sessions for user {user_id}: {e}")
            return []
    
    # Helper methods remain the same
    def _get_session_key(self, session_id: UUID) -> str:
        """Get Redis key for session."""
        return f"session:{session_id}"
    
    def _get_user_sessions_key(self, user_id: str) -> str:
        """Get Redis key for user sessions list."""
        return f"user_sessions:{user_id}"
    
    def _cache_session(self, session_id: UUID, session: SessionData):
        """Cache session locally."""
        try:
            # Implement LRU cache behavior
            if len(self.session_cache) >= self.cache_max_size:
                # Remove oldest entry
                oldest_key = next(iter(self.session_cache))
                del self.session_cache[oldest_key]
            
            self.session_cache[session_id] = {
                "session": session,
                "cached_at": time.time()
            }
            
        except Exception as e:
            logger.warning(f"Error caching session {session_id}: {e}")
    
    def _get_cached_session(self, session_id: UUID) -> Optional[SessionData]:
        """Get session from local cache."""
        try:
            cached_item = self.session_cache.get(session_id)
            if cached_item:
                # Check if cache entry is still valid
                if time.time() - cached_item["cached_at"] < self.cache_ttl:
                    return cached_item["session"]
                else:
                    # Cache expired, remove it
                    del self.session_cache[session_id]
            
            return None
            
        except Exception as e:
            logger.warning(f"Error getting cached session {session_id}: {e}")
            return None
    
    def _remove_from_cache(self, session_id: UUID):
        """Remove session from local cache."""
        try:
            if session_id in self.session_cache:
                del self.session_cache[session_id]
        except Exception as e:
            logger.warning(f"Error removing session {session_id} from cache: {e}")
    
    def _update_avg_session_duration(self, duration: float):
        """Update average session duration."""
        try:
            total_deleted = self.performance_stats["total_sessions_deleted"]
            if total_deleted > 0:
                current_avg = self.performance_stats["avg_session_duration"]
                new_avg = ((current_avg * (total_deleted - 1)) + duration) / total_deleted
                self.performance_stats["avg_session_duration"] = new_avg
                
        except Exception as e:
            logger.warning(f"Error updating avg session duration: {e}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive session statistics."""
        if not self.is_connected:
            try:
                await self.initialize()
            except:
                return {"error": "Redis not connected"}
        
        try:
            # Count active sessions
            pattern = self._get_session_key("*").replace(str(uuid4()), "*")
            session_keys = await self.redis_client.keys(pattern)
            active_sessions = len(session_keys)

            # Calculate cache hit rate
            total_requests = self.performance_stats["cache_hits"] + self.performance_stats["cache_misses"]
            cache_hit_rate = (
                self.performance_stats["cache_hits"] / total_requests 
                if total_requests > 0 else 0.0
            )
            
            return {
                "active_sessions": active_sessions,
                "redis_connected": True,
                "performance_stats": self.performance_stats.copy(),
                "cache_stats": {
                    "hit_rate": cache_hit_rate,
                    "cache_size": len(self.session_cache),
                    "max_cache_size": self.cache_max_size
                },
                "configuration": {
                    "session_timeout_minutes": self.config.SESSION_TIMEOUT_MINUTES,
                    "max_conversation_history": self.max_conversation_history,
                    "memory_window_size": self.memory_window_size
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get session stats: {e}")
            return {
                "active_sessions": 0,
                "redis_connected": False,
                "error": str(e),
                "performance_stats": self.performance_stats.copy()
            }
    
    async def health_check(self) -> bool:
        """Health check for session manager."""
        try:
            if not self.redis_client:
                return False
            
            # Test Redis connection
            await self.redis_client.ping()
            
            return True
            
        except Exception as e:
            logger.error(f"Session manager health check failed: {e}")
            return False
    
    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions with better error handling."""
        if not self.is_connected:
            await self.initialize()
        
        try:
            cleanup_start = time.perf_counter()
            cleaned_count = 0

            # Get all session keys
            pattern = "session:*"
            session_keys = await self.redis_client.keys(pattern)
            
            logger.info(f"Starting cleanup of {len(session_keys)} session keys")
            
            for key in session_keys:
                try:
                    # Check if key still exists (might have expired)
                    exists = await self.redis_client.exists(key)
                    if not exists:
                        cleaned_count += 1
                        continue
                    
                    # Check if session is old and corrupted
                    session_data = await self.redis_client.get(key)
                    if session_data:
                        try:
                            session_dict = json.loads(session_data)
                            
                            # Try to validate the session structure
                            if session_dict.get('metadata') is None:
                                session_dict['metadata'] = {}
                            
                            # Fix messages metadata
                            messages = session_dict.get('messages', [])
                            for msg in messages:
                                if isinstance(msg, dict) and msg.get('metadata') is None:
                                    msg['metadata'] = {}
                            
                            # Test if we can create a valid SessionData
                            SessionData.model_validate(session_dict)
                            
                            # Check if session is inactive based on last_activity_time
                            last_activity_str = session_dict.get('last_activity_time')
                            if last_activity_str:
                                try:
                                    last_activity = datetime.fromisoformat(last_activity_str.replace('Z', '+00:00'))
                                    inactive_time = (datetime.now() - last_activity).total_seconds()

                                    # Delete if inactive longer than session timeout
                                    if inactive_time > self.session_timeout:
                                        await self.redis_client.delete(key)
                                        cleaned_count += 1

                                        # Extract session_id and remove from cache
                                        session_id_str = key.split(':')[-1]
                                        try:
                                            session_id = UUID(session_id_str)
                                            self._remove_from_cache(session_id)
                                        except ValueError:
                                            pass
                                except ValueError:
                                    # Invalid timestamp, delete the session
                                    await self.redis_client.delete(key)
                                    cleaned_count += 1
                            else:
                                # No last_activity_time, fall back to updated_at
                                updated_at_str = session_dict.get('updated_at')
                                if updated_at_str:
                                    try:
                                        updated_at = datetime.fromisoformat(updated_at_str.replace('Z', '+00:00'))
                                        age = (datetime.now() - updated_at).total_seconds()

                                        # Delete if older than timeout
                                        if age > self.session_timeout:
                                            await self.redis_client.delete(key)
                                            cleaned_count += 1

                                            # Extract session_id and remove from cache
                                            session_id_str = key.split(':')[-1]
                                            try:
                                                session_id = UUID(session_id_str)
                                                self._remove_from_cache(session_id)
                                            except ValueError:
                                                pass
                                    except ValueError:
                                        # Invalid timestamp, delete the session
                                        await self.redis_client.delete(key)
                                        cleaned_count += 1
                            
                        except Exception as validation_error:
                            # Session is corrupted, delete it
                            logger.warning(f"Deleting corrupted session {key}: {validation_error}")
                            await self.redis_client.delete(key)
                            cleaned_count += 1
                            
                            # Remove from cache if present
                            session_id_str = key.split(':')[-1]
                            try:
                                session_id = UUID(session_id_str)
                                self._remove_from_cache(session_id)
                            except ValueError:
                                pass
                    
                except Exception as e:
                    logger.warning(f"Error processing session key {key}: {e}")
                    continue
            
            # Clean up user session lists
            user_pattern = self._get_user_sessions_key("*").replace("*", "*")
            user_keys = await self.redis_client.keys(user_pattern)
            
            for user_key in user_keys:
                try:
                    # Remove expired session IDs from user lists
                    session_ids = await self.redis_client.lrange(user_key, 0, -1)
                    for session_id_str in session_ids:
                        try:
                            session_id = UUID(session_id_str)
                            session_key = self._get_session_key(session_id)
                            exists = await self.redis_client.exists(session_key)
                            if not exists:
                                await self.redis_client.lrem(user_key, 0, session_id_str)
                        except (ValueError, TypeError):
                            # Invalid UUID, remove it
                            await self.redis_client.lrem(user_key, 0, session_id_str)
                            
                except Exception as e:
                    logger.warning(f"Error cleaning user key {user_key}: {e}")
                    continue
            
            # Clean local cache
            self._cleanup_local_cache()
            
            # Update performance stats
            cleanup_time = time.perf_counter() - cleanup_start
            self.performance_stats["cleanup_runs"] += 1
            self.performance_stats["last_cleanup"] = datetime.now().isoformat()
            
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} expired/corrupted sessions in {cleanup_time:.2f}s")
            else:
                logger.debug(f"No expired sessions found during cleanup ({cleanup_time:.2f}s)")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error during session cleanup: {e}")
            return 0
    
    def _cleanup_local_cache(self):
        """Clean up expired entries from local cache."""
        try:
            current_time = time.time()
            expired_keys = []
            
            for session_id, cached_item in self.session_cache.items():
                if current_time - cached_item["cached_at"] > self.cache_ttl:
                    expired_keys.append(session_id)
            
            for key in expired_keys:
                del self.session_cache[key]
                
            if expired_keys:
                logger.debug(f"Cleaned {len(expired_keys)} expired entries from session cache")
                
        except Exception as e:
            logger.warning(f"Error cleaning local cache: {e}")
    
    async def close(self):
        """Close Redis connection."""
        try:
            if self.redis_client:
                await self.redis_client.close()
                self.is_connected = False
                logger.info("Redis connection closed")
        except Exception as e:
            logger.error(f"Error closing Redis connection: {e}")


# Global session manager instance
session_manager = SessionManager()


def get_session_manager() -> SessionManager:
    """Get the session manager instance."""
    return session_manager