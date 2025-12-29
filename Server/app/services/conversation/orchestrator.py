from typing import Any, Dict, List, Optional
from uuid import UUID
import asyncio

from app.config import get_settings
from app.core.exceptions import RAGException, SessionError
from app.services.rag.chain import get_rag_service
from app.services.memory.session import get_session_manager
from app.services.memory.conversation import get_conversation_memory
from app.services.memory.conversation_summary import get_conversation_summarizer
from app.services.tracing import get_langfuse_client, is_langfuse_enabled
from app.schemas.chat import ChatMessage, ChatResponse, Source, SocialTippingPoint
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class ConversationOrchestrator:
    """Clean conversation orchestrator """
    
    def __init__(self):
        self.rag_service = None
        self.session_manager = None
        self.is_initialized = False
    
    async def initialize(self):
        """Initialize the conversation orchestrator."""
        try:
            self.rag_service = await get_rag_service()
            self.session_manager = get_session_manager()
            
            self.is_initialized = True
            logger.info("✅ Conversation orchestrator initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize conversation orchestrator: {e}")
            raise RAGException(f"Conversation orchestrator initialization failed: {str(e)}")
    
    async def start_new_conversation(
        self,
        initial_message: str,
        user_id: str = "anonymous",
        language: str = "en",
        difficulty_level: str = "low",
        include_sources: bool = True
    ) -> ChatResponse:
        """Start a new conversation """
        
        if not self.is_initialized:
            await self.initialize()
        
        try:
            if is_langfuse_enabled():
                langfuse_client = get_langfuse_client()
                
                with langfuse_client.start_as_current_span(
                    name="session_creation",
                    input=f"Creating session for user: {user_id}",
                    metadata={"component": "session_manager", "step": "session_setup"}
                ) as span:
                    session_id = await self.session_manager.create_session(
                        user_id=user_id,
                        language=language,  # Target language for session
                        title=self._generate_conversation_title(initial_message)
                    )
                    span.update(
                        output=f"Created session: {session_id}",
                        metadata={"session_id": str(session_id), "user_id": user_id, "target_language": language}
                    )
            else:
                session_id = await self.session_manager.create_session(
                    user_id=user_id,
                    language=language,
                    title=self._generate_conversation_title(initial_message)
                )
            
            logger.info(f"Starting new conversation, session {session_id}")
            
            # Pass conversation_type="start" to prevent context loading
            response = await self.process_chat_message(
                message=initial_message,  # English message
                session_id=session_id,
                language="en",  # Process in English
                difficulty_level=difficulty_level,
                include_sources=include_sources,
                conversation_type="start"
            )
            
            logger.info(f"✅ New conversation started")
            
            return response
            
        except Exception as e:
            logger.error(f"Error starting new conversation: {e}")
            raise RAGException(f"Failed to start new conversation: {str(e)}")
    
    async def continue_conversation(
        self,
        message: str,
        session_id: UUID,
        language: Optional[str] = None,
        difficulty_level: Optional[str] = None,
        include_sources: bool = True
    ) -> ChatResponse:
        """Continue an existing conversation - message is already in English"""
        
        if not self.is_initialized:
            await self.initialize()
        
        try:
            if is_langfuse_enabled():
                langfuse_client = get_langfuse_client()
                
                with langfuse_client.start_as_current_span(
                    name="session_validation",
                    input=f"Validating session: {session_id}",
                    metadata={"component": "session_manager", "step": "session_validation"}
                ) as span:
                    session = await self.session_manager.get_session(session_id)
                    if not session:
                        span.update(output="Session not found", level="ERROR")
                        raise SessionError(f"Session {session_id} not found or expired")
                    
                    span.update(
                        output=f"Session validated: {session_id}",
                        metadata={"session_id": str(session_id), "session_active": session.is_active}
                    )
            else:
                session = await self.session_manager.get_session(session_id)
                if not session:
                    raise SessionError(f"Session {session_id} not found or expired")
            
            # Use session defaults if not provided
            actual_difficulty = difficulty_level or "low"
            
            logger.info(f"Continuing conversation for session {session_id}")
            
            # Pass conversation_type="continue" to enable context loading
            response = await self.process_chat_message(
                message=message,  # English message
                session_id=session_id,
                language="en",  # Process in English
                difficulty_level=actual_difficulty,
                include_sources=include_sources,
                conversation_type="continue"
            )
            
            logger.info(f"✅ Conversation continued")
            
            return response
            
        except Exception as e:
            logger.error(f"Error continuing conversation: {e}")
            raise RAGException(f"Failed to continue conversation: {str(e)}")
    
    async def process_chat_message(
        self,
        message: str,  # English message
        session_id: UUID,
        language: str = "en",  # Always English
        difficulty_level: str = "low",
        include_sources: bool = True,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        conversation_type: str = "continue"
    ) -> ChatResponse:
        """Process a chat message - pure English processing with structured STP"""
        
        if not self.is_initialized:
            await self.initialize()
        
        try:
            logger.info(f"Processing {conversation_type} chat message for session {session_id}")
            
            # Store English user message
            user_message = ChatMessage(
                role="user",
                content=message
            )
            
            if is_langfuse_enabled():
                langfuse_client = get_langfuse_client()
                with langfuse_client.start_as_current_span(
                    name="message_storage",
                    input=f"Storing user message",
                    metadata={"component": "session_manager", "step": "message_storage"}
                ) as span:
                    await self.session_manager.add_message(session_id, user_message)
                    span.update(
                        output="User message stored",
                        metadata={
                            "message_id": str(user_message.id), 
                            "role": "user", 
                            "language": "en",
                            "conversation_type": conversation_type
                        }
                    )
            else:
                await self.session_manager.add_message(session_id, user_message)
            
            # Pass conversation_type to RAG service
            rag_result = await self.rag_service.query(
                question=message,
                session_id=str(session_id),
                include_sources=include_sources,
                max_tokens=max_tokens,
                temperature=temperature,
                language="en",
                difficulty_level=difficulty_level,
                conversation_type=conversation_type
            )
            
            # English response from RAG
            english_response = rag_result["answer"]
            
            # Create English assistant message
            assistant_message = ChatMessage(
                role="assistant",
                content=english_response  # English response
            )
            
            # Store English assistant message and update memory
            if is_langfuse_enabled():
                langfuse_client = get_langfuse_client()
                with langfuse_client.start_as_current_span(
                    name="response_storage",
                    input="Storing assistant response and updating memory",
                    metadata={"component": "session_manager", "step": "response_storage"}
                ) as span:
                    await self.session_manager.add_message(session_id, assistant_message)
                    
                    try:
                        conv_memory = await get_conversation_memory(session_id)
                        # Store English versions in memory
                        await conv_memory.add_exchange(message, english_response)
                        memory_updated = True
                    except Exception as e:
                        logger.warning(f"Failed to update conversation memory: {e}")
                        memory_updated = False
                    
                    span.update(
                        output="Response stored and memory updated",
                        metadata={
                            "message_id": str(assistant_message.id),
                            "role": "assistant",
                            "memory_updated": memory_updated,
                            "language": "en",
                            "stp_format": "structured",
                            "conversation_type": conversation_type
                        }
                    )
            else:
                await self.session_manager.add_message(session_id, assistant_message)
                
                try:
                    conv_memory = await get_conversation_memory(session_id)
                    # Store English versions in memory
                    await conv_memory.add_exchange(message, english_response)
                except Exception as e:
                    logger.warning(f"Failed to update conversation memory: {e}")
            
            # TRIGGER ASYNC SUMMARY UPDATE (after storing messages)
            if settings.ENABLE_CONVERSATION_SUMMARY:
                try:
                    summarizer = await get_conversation_summarizer()
                    session = await self.session_manager.get_session(session_id)
                    
                    # Doesn't block response
                    asyncio.create_task(
                        summarizer.maybe_update_summary_async(session_id, session.message_count)
                    )
                    logger.debug(f"Triggered summary check for session {session_id}")

                except Exception as e:
                    logger.warning(f"Failed to trigger summary: {e}")
            
            # Convert sources to clean format
            clean_sources = self._convert_to_clean_sources(rag_result.get("sources", []))

            # Handle structured STP response
            structured_stp = self._convert_to_structured_stp(rag_result.get("social_tipping_point", {}))

            # Determine if RAG was used (based on whether sources were retrieved)
            uses_rag = len(clean_sources) > 0 or rag_result.get("total_references", 0) > 0

            # Create clean English response with structured STP
            response = ChatResponse(
                success=True,
                session_id=session_id,
                message_id=assistant_message.id,
                response=english_response,
                title=rag_result.get("title", "Climate Information"),
                social_tipping_point=structured_stp,
                sources=clean_sources,
                total_references=rag_result.get("total_references", 0),
                uses_rag=uses_rag
            )
            
            logger.info("✅ Chat processing completed with structured STP", extra={
                "sources_count": len(clean_sources),
                "total_references": rag_result.get("total_references", 0),
                "conversation_type": conversation_type,
                "session_id": str(session_id),
                "language": "en",
                "stp_qualifying_factors_count": len(structured_stp.qualifying_factors)
            })
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing chat message: {e}")
            raise RAGException(f"Chat message processing failed: {str(e)}")
    
    def _convert_to_clean_sources(self, sources: List[Dict[str, Any]]) -> List[Source]:
        """Convert sources to clean format with only required fields."""
        clean_sources = []
        
        for source in sources:
            try:
                clean_source = Source(
                    title=source.get("title", "Unknown Document"),
                    doc_name=source.get("doc_name", "Unknown"),
                    url=source.get("url", ""),
                    similarity_score=round(float(source.get("similarity_score", 0.0)), 1)
                )
                
                clean_sources.append(clean_source)
                
            except Exception as e:
                logger.warning(f"Error converting source to clean format: {e}")
                continue
        
        return clean_sources
    
    def _convert_to_structured_stp(self, stp_data: Any) -> SocialTippingPoint:
        """Convert STP data to SocialTippingPoint model with proper factor parsing."""
        
        try:
            # If it's already a dict with expected structured format
            if isinstance(stp_data, dict):
                text = stp_data.get("text", "No specific social tipping point available for this query.")
                qualifying_factors = stp_data.get("qualifying_factors", [])
                
                # Ensure qualifying_factors is a list
                if not isinstance(qualifying_factors, list):
                    logger.warning(f"Qualifying factors is not a list: {type(qualifying_factors)}")
                    qualifying_factors = []
                
                # Clean up the qualifying factors (remove empty strings, trim whitespace)
                clean_factors = []
                for factor in qualifying_factors:
                    if factor and isinstance(factor, str):
                        cleaned = factor.strip()
                        if cleaned:
                            clean_factors.append(cleaned)
                
                logger.info(f"Converted structured STP: text_length={len(text)}, factors={len(clean_factors)}")
                
                return SocialTippingPoint(
                    text=text,
                    qualifying_factors=clean_factors
                )
            
            # If it's a string (legacy format), parse it
            elif isinstance(stp_data, str):
                # Check if it contains qualifying factors
                if "Qualifying factors:" in stp_data or "qualifying factors:" in stp_data:
                    # Split on "Qualifying factors:" (case insensitive)
                    import re
                    parts = re.split(r'Qualifying factors:', stp_data, flags=re.IGNORECASE)
                    
                    if len(parts) >= 2:
                        main_text = parts[0].strip()
                        factors_text = parts[1].strip()
                        
                        # Parse factors - split by newlines or numbered patterns
                        qualifying_factors = []
                        
                        # Try splitting by newlines first
                        lines = factors_text.split('\n')
                        for line in lines:
                            line = line.strip()
                            if line and len(line) > 5:  # Ignore very short lines
                                # Remove leading numbers and dots if present
                                cleaned = re.sub(r'^\d+[\.\)]\s*', '', line)
                                if cleaned:
                                    qualifying_factors.append(cleaned)
                        
                        # If no factors from newlines, try comma separation
                        if not qualifying_factors:
                            qualifying_factors = [f.strip() for f in factors_text.split(',') if f.strip()]
                        
                        logger.info(f"Parsed legacy STP format: {len(qualifying_factors)} factors")
                    else:
                        main_text = stp_data.strip()
                        qualifying_factors = []
                else:
                    main_text = stp_data.strip()
                    qualifying_factors = []
                
                return SocialTippingPoint(
                    text=main_text,
                    qualifying_factors=qualifying_factors
                )
            
            else:
                # Fallback for unexpected data types
                logger.warning(f"Unexpected STP data type: {type(stp_data)}")
                return SocialTippingPoint(
                    text="No specific social tipping point available for this query.",
                    qualifying_factors=[]
                )
                
        except Exception as e:
            logger.error(f"Error converting STP to structured format: {e}")
            return SocialTippingPoint(
                text="No specific social tipping point available for this query.",
                qualifying_factors=[]
            )
    
    async def get_conversation_history(
        self,
        session_id: UUID,
        limit: Optional[int] = None
    ) -> List[ChatMessage]:
        """Get conversation history for a session."""
        if not self.is_initialized:
            await self.initialize()
        
        try:
            return await self.session_manager.get_messages(session_id, limit)
        except Exception as e:
            logger.error(f"Error getting conversation history: {e}")
            raise SessionError(f"Failed to get conversation history: {str(e)}")
    
    async def delete_conversation(self, session_id: UUID) -> bool:
        """Delete a conversation session."""
        if not self.is_initialized:
            await self.initialize()
        
        try:
            return await self.session_manager.delete_session(session_id)
        except Exception as e:
            logger.error(f"Error deleting conversation: {e}")
            raise SessionError(f"Failed to delete conversation: {str(e)}")
    
    async def get_user_conversations(
        self,
        user_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get user's conversation list."""
        if not self.is_initialized:
            await self.initialize()
        
        try:
            sessions = await self.session_manager.list_user_sessions(user_id, limit)
            
            conversations = []
            for session in sessions:
                conversations.append({
                    "session_id": session.id,
                    "title": session.title or f"Conversation {session.id.hex[:8]}",
                    "last_activity": session.updated_at,
                    "message_count": session.message_count,
                    "language": session.language,
                    "is_active": session.is_active
                })
            
            return conversations
            
        except Exception as e:
            logger.error(f"Error getting user conversations: {e}")
            raise SessionError(f"Failed to get user conversations: {str(e)}")
    
    def _generate_conversation_title(self, initial_message: str) -> str:
        """Generate a title for the conversation based on initial message."""
        words = initial_message.split()[:5]
        title = " ".join(words)
        
        if len(title) > 50:
            title = title[:47] + "..."
        
        return title or "New Conversation"
    
    async def health_check(self) -> Dict[str, bool]:
        """Health check with structured STP support."""
        if not self.is_initialized:
            return {"initialized": False}
        
        try:
            rag_health = await self.rag_service.health_check() if self.rag_service else False
            session_health = await self.session_manager.health_check() if self.session_manager else False
            
            # Check summarizer health if enabled
            summarizer_health = True
            if settings.ENABLE_CONVERSATION_SUMMARY:
                try:
                    summarizer = await get_conversation_summarizer()
                    summarizer_health = await summarizer.health_check()
                except Exception as e:
                    logger.warning(f"Summarizer health check failed: {e}")
                    summarizer_health = False
            
            health_status = {
                "initialized": True,
                "rag_service": rag_health,
                "session_manager": session_health,
                "conversation_summarizer": summarizer_health,
                "overall": rag_health and session_health,
                "pure_english_processing": True,
                "structured_stp_support": True,
                "conversation_summary_enabled": settings.ENABLE_CONVERSATION_SUMMARY,
                "conversation_type_aware": True
            }
            
            return health_status
            
        except Exception as e:
            logger.error(f"Conversation orchestrator health check failed: {e}")
            return {"initialized": False, "error": str(e)}


# Global conversation orchestrator instance
conversation_orchestrator = ConversationOrchestrator()


async def get_conversation_orchestrator() -> ConversationOrchestrator:
    """Get the conversation orchestrator instance."""
    if not conversation_orchestrator.is_initialized:
        await conversation_orchestrator.initialize()
    return conversation_orchestrator