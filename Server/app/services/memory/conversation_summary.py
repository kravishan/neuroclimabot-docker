# Server/app/services/memory/conversation_summary.py
"""
Conversation summarization for long conversations.
Maintains context even after 100+ messages by creating rolling summaries.
"""

import asyncio
import re
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
from dataclasses import dataclass

from app.services.llm.factory import get_llm
from app.services.memory.session import get_session_manager
from app.services.prompts.manager import get_prompt_manager
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


@dataclass
class ConversationSummary:
    """Summary of conversation with key points."""
    session_id: UUID
    summary: str
    key_topics: List[str]
    important_facts: List[str]
    last_updated_message_count: int
    last_updated_at: datetime


class ConversationSummarizer:
    """Summarize long conversations to maintain context."""
    
    def __init__(self):
        self.llm = None
        self.session_manager = get_session_manager()
        self.prompt_manager = None
        self.summary_threshold = settings.SUMMARY_MESSAGE_THRESHOLD
        self.min_messages = settings.SUMMARY_MIN_MESSAGES
        self.max_summary_length = settings.SUMMARY_MAX_LENGTH
        self.summary_timeout = settings.SUMMARY_TIMEOUT
        
        # Cache summaries to avoid repeated DB reads
        self.summaries = {}
        
        # Track ongoing summarizations to avoid duplicates
        self.pending_summaries = set()
        
        # Performance tracking
        self.stats = {
            "total_summaries_created": 0,
            "total_summaries_updated": 0,
            "total_summary_requests": 0,
            "avg_summary_time": 0.0,
            "cache_hits": 0,
            "cache_misses": 0
        }
    
    async def initialize(self):
        """Initialize the summarizer."""
        try:
            self.llm = await get_llm()
            self.prompt_manager = await get_prompt_manager()
            logger.info(f"✅ Conversation summarizer initialized (threshold: {self.summary_threshold} messages)")
        except Exception as e:
            logger.error(f"Failed to initialize conversation summarizer: {e}")
            raise
    
    async def get_or_create_summary(self, session_id: UUID) -> Optional[ConversationSummary]:
        """Get existing summary or return None if not yet available."""
        
        # Check cache first
        if session_id in self.summaries:
            self.stats["cache_hits"] += 1
            return self.summaries[session_id]
        
        self.stats["cache_misses"] += 1
        
        # Load from session metadata
        session = await self.session_manager.get_session(session_id)
        if not session:
            return None
        
        summary_data = session.metadata.get("conversation_summary")
        if not summary_data:
            return None
        
        try:
            summary = ConversationSummary(
                session_id=session_id,
                summary=summary_data.get("summary", ""),
                key_topics=summary_data.get("key_topics", []),
                important_facts=summary_data.get("important_facts", []),
                last_updated_message_count=summary_data.get("last_updated_message_count", 0),
                last_updated_at=datetime.fromisoformat(summary_data.get("last_updated_at", datetime.now().isoformat()))
            )
            
            # Cache it
            self.summaries[session_id] = summary
            return summary
            
        except Exception as e:
            logger.error(f"Error loading summary for session {session_id}: {e}")
            return None
    
    async def should_update_summary(self, session_id: UUID, current_message_count: int) -> bool:
        """Check if summary needs updating."""
        
        # Don't summarize very short conversations
        if current_message_count < self.min_messages:
            return False
        
        summary = await self.get_or_create_summary(session_id)
        
        # First summary after threshold
        if not summary:
            return current_message_count >= self.summary_threshold
        
        # Update every N messages
        messages_since_update = current_message_count - summary.last_updated_message_count
        return messages_since_update >= self.summary_threshold
    
    async def maybe_update_summary_async(self, session_id: UUID, current_message_count: int):
        """
        Asynchronously update summary if needed.
        This is fire-and-forget - doesn't block the response to user.
        """
        
        # Check if already summarizing
        if session_id in self.pending_summaries:
            logger.debug(f"Summary already in progress for {session_id}")
            return
        
        # Check if needs update
        should_update = await self.should_update_summary(session_id, current_message_count)
        
        if should_update:
            logger.info(f"🔄 Triggering async summary for session {session_id} (messages: {current_message_count})")
            self.pending_summaries.add(session_id)
            
            # Fire and forget - don't await
            asyncio.create_task(self._update_summary_background(session_id))
    
    async def _update_summary_background(self, session_id: UUID):
        """Background task for summarization - won't block user responses."""
        try:
            await self.update_summary(session_id)
            logger.info(f"✅ Background summary completed for {session_id}")
        except Exception as e:
            logger.error(f"❌ Background summary failed for {session_id}: {e}")
        finally:
            self.pending_summaries.discard(session_id)
    
    async def update_summary(self, session_id: UUID) -> Optional[ConversationSummary]:
        """Update conversation summary with recent messages."""
        
        if not self.llm:
            await self.initialize()
        
        import time
        start_time = time.perf_counter()
        
        try:
            self.stats["total_summary_requests"] += 1
            
            session = await self.session_manager.get_session(session_id)
            if not session:
                logger.warning(f"Session {session_id} not found for summary update")
                return None
            
            # Get all messages
            messages = session.messages
            current_count = len(messages)
            
            if current_count < self.min_messages:
                logger.debug(f"Not enough messages ({current_count}) for summary")
                return None
            
            # Get existing summary
            existing_summary = await self.get_or_create_summary(session_id)
            
            # Get messages since last summary
            if existing_summary:
                start_idx = existing_summary.last_updated_message_count
                new_messages = messages[start_idx:]
                logger.info(f"Updating summary with {len(new_messages)} new messages")
            else:
                new_messages = messages
                logger.info(f"Creating first summary with {len(new_messages)} messages")
            
            # Build conversation text for summarization
            conversation_text = self._format_messages_for_summary(new_messages)
            
            # Generate summary using prompt template
            prompt = self.prompt_manager.render_conversation_summary_prompt(
                existing_summary=existing_summary.summary if existing_summary else None,
                new_conversation=conversation_text,
                max_length=self.max_summary_length
            )
            
            # Call LLM with timeout
            summary_response = await asyncio.wait_for(
                self._call_llm(prompt),
                timeout=self.summary_timeout
            )
            
            # Parse the response
            parsed_summary = self._parse_summary_response(summary_response)
            
            # Create new summary object
            new_summary = ConversationSummary(
                session_id=session_id,
                summary=parsed_summary["summary"],
                key_topics=parsed_summary["key_topics"],
                important_facts=parsed_summary["important_facts"],
                last_updated_message_count=current_count,
                last_updated_at=datetime.now()
            )
            
            # Save to session metadata
            session.metadata["conversation_summary"] = {
                "summary": new_summary.summary,
                "key_topics": new_summary.key_topics,
                "important_facts": new_summary.important_facts,
                "last_updated_message_count": new_summary.last_updated_message_count,
                "last_updated_at": new_summary.last_updated_at.isoformat()
            }
            await self.session_manager.update_session(session_id, session)
            
            # Cache it
            self.summaries[session_id] = new_summary
            
            # Update stats
            if existing_summary:
                self.stats["total_summaries_updated"] += 1
            else:
                self.stats["total_summaries_created"] += 1
            
            summary_time = time.perf_counter() - start_time
            self._update_avg_summary_time(summary_time)
            
            logger.info(f"✅ Summary updated in {summary_time:.2f}s for session {session_id}")
            return new_summary
            
        except asyncio.TimeoutError:
            logger.error(f"Summary generation timed out for session {session_id}")
            return None
        except Exception as e:
            logger.error(f"Failed to update summary for session {session_id}: {e}")
            return None
    
    def _format_messages_for_summary(self, messages) -> str:
        """Format messages for summarization."""
        parts = []
        for msg in messages:
            role = "User" if msg.role == "user" else "Assistant"
            # Truncate very long messages for efficiency
            content = msg.content[:500] + "..." if len(msg.content) > 500 else msg.content
            parts.append(f"{role}: {content}")
        return "\n\n".join(parts)
    
    async def _call_llm(self, prompt: str) -> str:
        """Call LLM for summarization."""
        if hasattr(self.llm, '_acall'):
            return await self.llm._acall(prompt)
        else:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.llm, prompt)
    
    def _parse_summary_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM summary response."""
        
        summary = ""
        key_topics = []
        important_facts = []
        
        try:
            # Extract summary
            summary_match = re.search(r'<SUMMARY>(.*?)</SUMMARY>', response, re.DOTALL | re.IGNORECASE)
            if summary_match:
                summary = summary_match.group(1).strip()
            
            # Extract key topics
            topics_match = re.search(r'<KEY_TOPICS>(.*?)</KEY_TOPICS>', response, re.DOTALL | re.IGNORECASE)
            if topics_match:
                topics_text = topics_match.group(1).strip()
                # Parse bullet points
                key_topics = [
                    t.strip('- ').strip() 
                    for t in topics_text.split('\n') 
                    if t.strip() and len(t.strip()) > 3
                ]
            
            # Extract important facts
            facts_match = re.search(r'<IMPORTANT_FACTS>(.*?)</IMPORTANT_FACTS>', response, re.DOTALL | re.IGNORECASE)
            if facts_match:
                facts_text = facts_match.group(1).strip()
                # Parse bullet points
                important_facts = [
                    f.strip('- ').strip() 
                    for f in facts_text.split('\n') 
                    if f.strip() and len(f.strip()) > 3
                ]
        
        except Exception as e:
            logger.error(f"Error parsing summary response: {e}")
        
        return {
            "summary": summary or "Conversation about climate topics.",
            "key_topics": key_topics[:5],  # Max 5 topics
            "important_facts": important_facts[:5]  # Max 5 facts
        }
    
    async def get_conversation_context(self, session_id: UUID) -> str:
        """
        Get conversation context for LLM processing.
        Returns: Summary + last 2 messages only (hybrid approach)
        """
        
        session = await self.session_manager.get_session(session_id)
        if not session:
            return ""
        
        total_messages = len(session.messages)
        
        # For very short conversations: Use raw messages only
        if total_messages < self.min_messages:
            return self._format_recent_messages(session.messages[-4:])
        
        # For longer conversations: Summary + last 2 messages ONLY
        summary = await self.get_or_create_summary(session_id)
        
        # Always use only last 2 messages for recent context
        recent_messages = session.messages[-2:] if len(session.messages) >= 2 else session.messages
        recent_text = self._format_recent_messages(recent_messages)
        
        # Build context
        if summary:
            context_parts = ["=== CONVERSATION BACKGROUND ==="]
            context_parts.append(summary.summary)
            
            if summary.key_topics:
                context_parts.append(f"\nTopics Discussed: {', '.join(summary.key_topics)}")
            
            if summary.important_facts:
                context_parts.append("\nKey Points:")
                for fact in summary.important_facts:
                    context_parts.append(f"  • {fact}")
            
            context_parts.append("\n=== RECENT CONVERSATION (Last 2 Messages) ===")
            context_parts.append(recent_text)
            
            return "\n".join(context_parts)
        else:
            # No summary yet, use last 4 messages
            return self._format_recent_messages(session.messages[-4:])
    
    def _format_recent_messages(self, messages) -> str:
        """Format recent messages for context."""
        parts = []
        for msg in messages:
            role = "User" if msg.role == "user" else "Assistant"
            # Truncate if too long
            content = msg.content[:300] + "..." if len(msg.content) > 300 else msg.content
            parts.append(f"{role}: {content}")
        return "\n".join(parts)
    
    def _update_avg_summary_time(self, summary_time: float):
        """Update average summary time statistic."""
        total = self.stats["total_summary_requests"]
        current_avg = self.stats["avg_summary_time"]
        new_avg = ((current_avg * (total - 1)) + summary_time) / total
        self.stats["avg_summary_time"] = new_avg
    
    def get_stats(self) -> Dict[str, Any]:
        """Get summarizer statistics."""
        return {
            **self.stats,
            "summary_threshold": self.summary_threshold,
            "min_messages": self.min_messages,
            "max_summary_length": self.max_summary_length,
            "cached_summaries": len(self.summaries),
            "pending_summaries": len(self.pending_summaries),
            "recent_messages_in_context": 2
        }
    
    async def health_check(self) -> bool:
        """Health check for summarizer."""
        try:
            if not self.llm:
                return False
            if not self.prompt_manager:
                return False
            return True
        except Exception as e:
            logger.error(f"Summarizer health check failed: {e}")
            return False


# Global instance
conversation_summarizer = ConversationSummarizer()


async def get_conversation_summarizer() -> ConversationSummarizer:
    """Get the conversation summarizer instance."""
    if not conversation_summarizer.llm:
        await conversation_summarizer.initialize()
    return conversation_summarizer