"""
Conversation memory management

"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.config import get_settings
from app.core.exceptions import SessionError
from app.schemas.chat import ChatMessage
from app.services.memory.session import get_session_manager
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class ConversationMemory:
    """Simple conversation memory manager that integrates with session storage."""
    
    def __init__(self, session_id: UUID):
        self.session_id = session_id
        self.session_manager = get_session_manager()
        self.memory_window_size = settings.MEMORY_WINDOW_SIZE
        self.conversation_history = []
    
    async def load_conversation_history(self) -> List[Dict[str, str]]:
        """Load conversation history from session storage."""
        try:
            messages = await self.session_manager.get_messages(
                self.session_id,
                limit=self.memory_window_size * 2  # Get more to fill the window
            )
            
            # Convert to simple format
            conversation_pairs = []
            for i in range(0, len(messages), 2):
                if i + 1 < len(messages):
                    human_msg = messages[i]
                    ai_msg = messages[i + 1]
                    
                    if human_msg.role == "user" and ai_msg.role == "assistant":
                        conversation_pairs.append({
                            "human": human_msg.content,
                            "ai": ai_msg.content,
                            "timestamp": human_msg.timestamp.isoformat()
                        })
            
            self.conversation_history = conversation_pairs
            return conversation_pairs
            
        except Exception as e:
            logger.error(f"Failed to load conversation history for session {self.session_id}: {e}")
            return []
    
    async def add_exchange(self, human_message: str, ai_message: str):
        """Add a human-AI message exchange to memory."""
        try:
            # Store in session storage
            user_msg = ChatMessage(role="user", content=human_message)
            ai_msg = ChatMessage(role="assistant", content=ai_message)
            
            await self.session_manager.add_message(self.session_id, user_msg)
            await self.session_manager.add_message(self.session_id, ai_msg)
            
            # Update local memory
            self.conversation_history.append({
                "human": human_message,
                "ai": ai_message,
                "timestamp": user_msg.timestamp.isoformat()
            })
            
            # Keep only recent exchanges
            if len(self.conversation_history) > self.memory_window_size:
                self.conversation_history = self.conversation_history[-self.memory_window_size:]
            
        except Exception as e:
            logger.error(f"Failed to add exchange to memory for session {self.session_id}: {e}")
            raise SessionError(f"Failed to add message exchange: {str(e)}")
    
    def get_memory_variables(self) -> Dict[str, Any]:
        """Get memory variables for use in chains."""
        # Create a simple chat history format
        chat_history = []
        for exchange in self.conversation_history:
            # Add as simple message objects with content attribute
            class SimpleMessage:
                def __init__(self, content: str):
                    self.content = content
            
            chat_history.append(SimpleMessage(exchange["human"]))
            chat_history.append(SimpleMessage(exchange["ai"]))
        
        return {
            "chat_history": chat_history,
            "conversation_history": self.conversation_history
        }
    
    def get_formatted_history(self, max_exchanges: int = 3) -> str:
        """Get formatted conversation history as a string."""
        if not self.conversation_history:
            return ""
        
        # Get recent exchanges
        recent_exchanges = self.conversation_history[-max_exchanges:] if max_exchanges else self.conversation_history
        
        formatted_parts = []
        for exchange in recent_exchanges:
            formatted_parts.append(f"Human: {exchange['human']}")
            formatted_parts.append(f"Assistant: {exchange['ai']}")
        
        return "\n".join(formatted_parts)
    
    def clear(self):
        """Clear the memory."""
        self.conversation_history.clear()
    
    def get_last_exchange(self) -> Optional[Dict[str, str]]:
        """Get the last conversation exchange."""
        if self.conversation_history:
            return self.conversation_history[-1]
        return None
    
    def get_exchange_count(self) -> int:
        """Get the number of conversation exchanges."""
        return len(self.conversation_history)


async def get_conversation_memory(session_id: UUID) -> ConversationMemory:
    """Get conversation memory for a session."""
    memory = ConversationMemory(session_id)
    await memory.load_conversation_history()
    return memory