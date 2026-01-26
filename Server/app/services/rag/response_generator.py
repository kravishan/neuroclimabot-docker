"""
Clean response generation service with PURE SCORE-BASED context building.
Prioritizes highest relevance scores across all sources - no diversity guarantees.
STP is now handled AFTER response generation in the chain service.
Features: Robust parsing with smart === marker detection, paragraph preservation
"""

import asyncio
import time
import re
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

from app.config import get_settings
from app.services.llm.factory import get_llm
from app.services.prompts.manager import get_prompt_manager
from app.core.exceptions import RAGException
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


@dataclass
class GenerationResult:
    """Result from response generation WITHOUT STP (handled separately now)."""
    title: Optional[str]  # None for continue conversations, string for start conversations
    content: str
    generation_time: float
    context_length: int


class ResponseGeneratorService:
    """Response generator with pure score-based context building and smart parsing."""
    
    def __init__(self):
        self.llm = None
        self.prompt_manager = None
        self.is_initialized = False
        self.max_context_length = settings.MAX_CONTEXT_LENGTH
        self.response_timeout = settings.BEDROCK_TIMEOUT
        
        # Content length limits per source type
        self.CONTENT_LIMITS = {
            "chunk": 400,
            "summary": 300,
            "graph": 200
        }
        
        # Performance tracking
        self.performance_stats = {
            "total_generations": 0,
            "avg_generation_time": 0.0,
            "start_conversations": 0,
            "continue_conversations": 0,
            "parsing_successes": 0,
            "parsing_fallbacks": 0
        }
    
    async def initialize(self):
        """Initialize the response generator."""
        try:
            self.llm, self.prompt_manager = await asyncio.gather(
                get_llm(),
                get_prompt_manager()
            )
            
            self.is_initialized = True
            logger.info("✅ Response generator initialized with smart === marker parsing")
            
        except Exception as e:
            logger.error(f"Failed to initialize response generator: {e}")
            raise RAGException(f"Response generator initialization failed: {str(e)}")
    
    async def generate_start_conversation_response(
        self,
        original_query: str,
        processed_query: Optional[str],
        chunks: List[Dict[str, Any]],
        summaries: List[Dict[str, Any]],
        graph_data: List[Dict[str, Any]],
        language: str = "en",
        difficulty_level: str = "low",
        was_processed: bool = False
    ) -> GenerationResult:
        """Generate start conversation response with pure score-based context."""
        
        if not self.is_initialized:
            await self.initialize()
        
        start_time = time.perf_counter()
        self.performance_stats["total_generations"] += 1
        self.performance_stats["start_conversations"] += 1
        
        try:
            # Build context using pure score-based method
            context, context_length = self._build_context_by_score(
                chunks=chunks[:settings.MAX_CONTEXT_CHUNKS],
                summaries=summaries[:settings.MAX_CONTEXT_SUMMARIES],
                graph_data=graph_data[:settings.MAX_CONTEXT_GRAPH_ITEMS]
            )
            
            # Generate prompt
            if context_length > 0:
                prompt = self.prompt_manager.render_start_conversation_prompt(
                    original_query=original_query,
                    processed_query=processed_query,
                    context=context,
                    language=language,
                    difficulty_level=difficulty_level,
                    was_processed=was_processed
                )
            else:
                prompt = self.prompt_manager.render_fallback_start_prompt(
                    original_query=original_query,
                    language=language,
                    difficulty_level=difficulty_level
                )
            
            # Generate LLM response
            raw_response = await self._generate_llm_response_with_timeout(prompt)
            
            # Parse response
            title, content = self._parse_start_response_robust(raw_response)
            generation_time = time.perf_counter() - start_time
            self._update_stats(generation_time)
            
            logger.info(f"✅ Generated start response in {generation_time:.3f}s")
            
            return GenerationResult(
                title=title,
                content=content,
                generation_time=generation_time,
                context_length=context_length
            )
            
        except Exception as e:
            logger.error(f"Error generating start response: {e}")
            return self._create_fallback_response(original_query, time.perf_counter() - start_time, True)
    
    async def generate_continue_conversation_response(
        self,
        original_query: str,
        processed_query: Optional[str],
        chunks: List[Dict[str, Any]],
        summaries: List[Dict[str, Any]],
        graph_data: List[Dict[str, Any]],
        conversation_memory: str,
        language: str = "en",
        difficulty_level: str = "low",
        was_processed: bool = False,
        message_count: int = 1
    ) -> GenerationResult:
        """Generate continue conversation response with pure score-based context."""
        
        if not self.is_initialized:
            await self.initialize()
        
        start_time = time.perf_counter()
        self.performance_stats["total_generations"] += 1
        self.performance_stats["continue_conversations"] += 1
        
        try:
            # Build context
            context, context_length = self._build_context_by_score(
                chunks=chunks[:settings.MAX_CONTEXT_CHUNKS + 2],
                summaries=summaries[:settings.MAX_CONTEXT_SUMMARIES + 1],
                graph_data=graph_data[:settings.MAX_CONTEXT_GRAPH_ITEMS + 1]
            )
            
            optimized_memory = self._optimize_memory(conversation_memory)
            
            # Generate prompt
            if context_length > 0:
                prompt = self.prompt_manager.render_continue_conversation_prompt(
                    original_query=original_query,
                    processed_query=processed_query,
                    context=context,
                    conversation_memory=optimized_memory,
                    language=language,
                    difficulty_level=difficulty_level,
                    was_processed=was_processed,
                    message_count=message_count
                )
            else:
                prompt = self.prompt_manager.render_fallback_continue_prompt(
                    original_query=original_query,
                    processed_query=processed_query,
                    conversation_memory=optimized_memory,
                    language=language,
                    difficulty_level=difficulty_level,
                    message_count=message_count,
                    was_processed=was_processed
                )
            
            # Generate LLM response
            raw_response = await self._generate_llm_response_with_timeout(prompt)
            
            # Parse response
            content = self._parse_continue_response_robust(raw_response)
            generation_time = time.perf_counter() - start_time
            self._update_stats(generation_time)
            
            logger.info(f"✅ Generated continue response in {generation_time:.3f}s")

            return GenerationResult(
                title=None,  # No title for continue conversations
                content=content,
                generation_time=generation_time,
                context_length=context_length
            )
            
        except Exception as e:
            logger.error(f"Error generating continue response: {e}")
            return self._create_fallback_response(original_query, time.perf_counter() - start_time, False)
    
    def _parse_start_response_robust(self, response_text: str) -> Tuple[str, str]:
        """
        ROBUST parser for start responses with smart === marker detection.
        Handles: ===TITLE_START===, ===Title===, <TITLE>, and raw text.
        Never fails - always returns valid response.
        """
        
        default_title = "Climate Information"
        default_content = "I'm here to help with climate questions."
        
        try:
            # Strategy 1: Correct === markers (PRIMARY)
            title = self._extract_between_markers(response_text, "===TITLE_START===", "===TITLE_END===")
            content = self._extract_between_markers(response_text, "===CONTENT_START===", "===CONTENT_END===")
            
            if title and content:
                self.performance_stats["parsing_successes"] += 1
                cleaned_title = self._clean_extracted_text(title, max_length=100)
                cleaned_content = self._clean_extracted_text(content)

                # Validate title is not empty or still contains marker text after cleaning
                cleaned_title = self._validate_title(cleaned_title, default_title)

                return (cleaned_title, cleaned_content)
            
            # Strategy 1.5: Smart detection of ===Title=== format (LLM's common variation)
            if not title and content:
                # Content found but title missing - look for ===Title=== pattern
                lines = response_text.split('\n')
                for line in lines[:10]:  # Check first 10 lines
                    line = line.strip()
                    # Look for ===Something=== that's not a marker keyword
                    if (line.startswith('===') and line.endswith('===') and 
                        'TITLE_START' not in line and 'CONTENT_START' not in line and
                        'TITLE_END' not in line and 'CONTENT_END' not in line):
                        
                        potential_title = line.strip('=').strip()
                        if potential_title and len(potential_title.split()) <= 12:
                            self.performance_stats["parsing_successes"] += 1
                            # Validate title
                            validated_title = self._validate_title(potential_title[:100], default_title)
                            return (
                                validated_title,
                                self._clean_extracted_text(content)
                            )
            
            # Strategy 2: <TAG> format (FALLBACK)
            title_match = re.search(r'<\s*TITLE\s*>(.*?)<\s*/\s*TITLE\s*>', response_text, re.IGNORECASE | re.DOTALL)
            content_match = re.search(r'<\s*CONTENT\s*>(.*?)<\s*/\s*CONTENT\s*>', response_text, re.IGNORECASE | re.DOTALL)
            
            if title_match and content_match:
                self.performance_stats["parsing_fallbacks"] += 1
                cleaned_title = self._clean_extracted_text(title_match.group(1), max_length=100)
                cleaned_content = self._clean_extracted_text(content_match.group(1))

                # Validate title
                cleaned_title = self._validate_title(cleaned_title, default_title)

                return (cleaned_title, cleaned_content)
            
            # Strategy 3: Raw extraction (LAST RESORT)
            self.performance_stats["parsing_fallbacks"] += 1
            title = self._extract_title_from_raw(response_text) or default_title
            content = self._extract_content_from_raw(response_text) or default_content

            # Validate extracted title
            title = self._validate_title(title, default_title)

            return title, content
            
        except Exception as e:
            logger.error(f"Parser failed: {e}")
            return default_title, default_content
    
    def _parse_continue_response_robust(self, response_text: str) -> str:
        """
        ROBUST parser for continue responses.
        Handles: ===CONTENT_START===, <CONTENT>, and raw text.
        Never fails - always returns valid response.
        """
        
        default_content = "I'm here to help with your climate questions."
        
        try:
            # Strategy 1: === markers (PRIMARY)
            content = self._extract_between_markers(response_text, "===CONTENT_START===", "===CONTENT_END===")
            
            if content:
                self.performance_stats["parsing_successes"] += 1
                return self._clean_extracted_text(content)
            
            # Strategy 2: <TAG> format (FALLBACK)
            content_match = re.search(r'<\s*CONTENT\s*>(.*?)<\s*/\s*CONTENT\s*>', response_text, re.IGNORECASE | re.DOTALL)
            
            if content_match:
                self.performance_stats["parsing_fallbacks"] += 1
                return self._clean_extracted_text(content_match.group(1))
            
            # Strategy 3: Raw extraction (LAST RESORT)
            self.performance_stats["parsing_fallbacks"] += 1
            return self._extract_content_from_raw(response_text) or default_content
            
        except Exception as e:
            logger.error(f"Continue parser failed: {e}")
            return default_content
    
    def _extract_between_markers(self, text: str, start: str, end: str) -> Optional[str]:
        """Extract text between two markers."""
        try:
            start_idx = text.find(start)
            end_idx = text.find(end)
            
            if start_idx == -1 or end_idx == -1 or start_idx >= end_idx:
                return None
            
            return text[start_idx + len(start):end_idx].strip()
        except:
            return None
    
    def _clean_extracted_text(self, text: str, max_length: Optional[int] = None) -> str:
        """Clean extracted text while preserving paragraph structure."""
        if not text:
            return ""
        
        # Split into lines to preserve paragraph structure
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines at the start
            if not cleaned_lines and not line:
                continue
            
            # Keep empty lines for paragraph breaks
            if not line:
                cleaned_lines.append('')
                continue
            
            # Clean the line content
            line = ' '.join(line.split())
            cleaned_lines.append(line)
        
        # Join back with newlines
        cleaned = '\n'.join(cleaned_lines)
        
        # Remove wrapping quotes
        cleaned = cleaned.strip()
        if (cleaned.startswith('"') and cleaned.endswith('"')) or (cleaned.startswith("'") and cleaned.endswith("'")):
            cleaned = cleaned[1:-1].strip()
        
        # Remove tag artifacts and marker text from the very start
        for pattern in [r'^content\s*:\s*', r'^title\s*:\s*', r'^response\s*:\s*',
                        r'^title_start\s*', r'^title_end\s*', r'^content_start\s*', r'^content_end\s*']:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)

        # Remove any remaining marker text or partial markers that might have leaked through
        marker_artifacts = [
            r'===\s*TITLE_START\s*===', r'===\s*TITLE_END\s*===',
            r'===\s*CONTENT_START\s*===', r'===\s*CONTENT_END\s*===',
            r'TITLE_START', r'TITLE_END', r'CONTENT_START', r'CONTENT_END',
            r'<\s*TITLE\s*>', r'<\s*/\s*TITLE\s*>', r'<\s*CONTENT\s*>', r'<\s*/\s*CONTENT\s*>'
        ]
        for artifact in marker_artifacts:
            cleaned = re.sub(artifact, '', cleaned, flags=re.IGNORECASE)

        # For titles (max_length specified), collapse whitespace to single line
        # For content, preserve paragraph structure (newlines handled earlier)
        if max_length:
            cleaned = ' '.join(cleaned.split())

        # Limit length if specified
        if max_length and len(cleaned) > max_length:
            cleaned = cleaned[:max_length]
        
        # Final cleanup: remove excessive blank lines (more than 2 consecutive)
        while '\n\n\n' in cleaned:
            cleaned = cleaned.replace('\n\n\n', '\n\n')
        
        return cleaned.strip()

    def _validate_title(self, title: str, default_title: str) -> str:
        """
        Validate title and return default if invalid.
        Checks for empty titles, whitespace-only, and remaining marker text.
        """
        if not title or not title.strip():
            return default_title

        # Check if title still contains marker text (case-insensitive)
        title_upper = title.upper()
        marker_keywords = [
            'TITLE_START', 'TITLE_END', 'CONTENT_START', 'CONTENT_END',
            'TITLE START', 'TITLE END', 'CONTENT START', 'CONTENT END'
        ]

        for marker in marker_keywords:
            if marker in title_upper:
                logger.warning(f"Title still contains marker text: {title}, using default")
                return default_title

        # Check if title is suspiciously short (likely a marker fragment)
        if len(title.strip()) < 3:
            return default_title

        return title

    def _extract_title_from_raw(self, text: str) -> Optional[str]:
        """Extract title from raw text - handles === wrapped titles."""
        lines = text.strip().split('\n')
        
        for line in lines[:5]:
            line = line.strip()
            
            if not line:
                continue
            
            # Check if line is wrapped in === markers
            if line.startswith('===') and line.endswith('==='):
                title = line.strip('=').strip()
                if title:
                    return title[:100]
            
            # Skip other marker lines and tags
            if '===' in line or '<' in line:
                continue
            
            # Check if line looks like a title
            words = line.split()
            if 3 <= len(words) <= 12:
                caps = sum(1 for w in words if w and w[0].isupper())
                if caps / len(words) >= 0.5:
                    return ' '.join(line.split())[:100]
        
        return None
    
    def _extract_content_from_raw(self, text: str) -> Optional[str]:
        """Extract content from raw text - PRESERVES PARAGRAPHS."""
        
        # Remove markers and tags but KEEP newlines
        cleaned = re.sub(r'===.*?===', '', text, flags=re.DOTALL)
        cleaned = re.sub(r'<.*?>', '', cleaned, flags=re.DOTALL)
        
        # Clean up each line individually to preserve paragraph structure
        lines = cleaned.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            # Keep empty lines for paragraph breaks
            if not line:
                if cleaned_lines and cleaned_lines[-1] != '':
                    cleaned_lines.append('')
            else:
                cleaned_lines.append(line)
        
        # Remove leading/trailing empty lines
        while cleaned_lines and cleaned_lines[0] == '':
            cleaned_lines.pop(0)
        while cleaned_lines and cleaned_lines[-1] == '':
            cleaned_lines.pop()
        
        # Join with newlines to preserve paragraphs
        result = '\n'.join(cleaned_lines)
        
        # Limit length if needed
        if len(result) > settings.MAX_RESPONSE_LENGTH:
            result = result[:settings.MAX_RESPONSE_LENGTH]
        
        return result if result else None
    
    def _build_context_by_score(self, chunks, summaries, graph_data) -> tuple[str, int]:
        """Build context by pure score priority - highest scores win."""
        
        chunks = chunks or []
        summaries = summaries or []
        graph_data = graph_data or []
        
        if not chunks and not summaries and not graph_data:
            return "No relevant data found.", 25
        
        # Combine all sources with scores
        all_items = []
        
        for chunk in chunks:
            all_items.append({
                **chunk, 
                "source_type": "chunk", 
                "score": chunk.get("rerank_score", chunk.get("score", 0.0))
            })
        
        for summary in summaries:
            all_items.append({
                **summary, 
                "source_type": "summary", 
                "score": summary.get("rerank_score", summary.get("score", 0.0))
            })
        
        for graph in graph_data:
            all_items.append({
                **graph, 
                "source_type": "graph", 
                "score": graph.get("rerank_score", graph.get("score", 0.0))
            })
        
        # Sort by score (highest first)
        all_items.sort(key=lambda x: x["score"], reverse=True)
        
        # Build context until full
        context_parts = []
        current_length = 0
        
        for item in all_items:
            text = self._format_item(item)
            if current_length + len(text) > self.max_context_length:
                break
            context_parts.append(text)
            current_length += len(text)
        
        return "\n".join(context_parts) if context_parts else "No relevant content.", current_length
    
    def _format_item(self, item: Dict[str, Any]) -> str:
        """Format a context item."""
        source_type = item["source_type"]
        score = item["score"]
        doc_name = item.get("doc_name", "Unknown")[:30]
        
        if source_type == "chunk":
            content = item.get("content", "")[:self.CONTENT_LIMITS["chunk"]]
            return f"[Chunk: {doc_name} ({score:.2f})]\n{content}\n"
        elif source_type == "summary":
            content = item.get("summary", item.get("content", ""))[:self.CONTENT_LIMITS["summary"]]
            return f"[Summary: {doc_name} ({score:.2f})]\n{content}\n"
        else:  # graph
            content = item.get("content", "")[:self.CONTENT_LIMITS["graph"]]
            entities = item.get("entities", []) or []
            text = f"[Graph: {doc_name} ({score:.2f})]\n{content}"
            if entities:
                text += f"\nEntities: {', '.join(entities[:5])}"
            return text + "\n"
    
    def _optimize_memory(self, memory: str) -> str:
        """Optimize conversation memory."""
        if not memory or len(memory) <= 500:
            return memory
        
        lines = memory.split('\n')
        recent = lines[-6:] if len(lines) > 6 else lines
        optimized = '\n'.join(recent)
        
        return optimized[-500:] if len(optimized) > 500 else optimized
    
    async def _generate_llm_response_with_timeout(self, prompt: str) -> str:
        """Generate LLM response with timeout."""
        try:
            response_task = self._generate_llm_response(prompt)
            response = await asyncio.wait_for(response_task, timeout=self.response_timeout)
            return response.strip()
        except asyncio.TimeoutError:
            raise RAGException("Response generation timed out")
        except Exception as e:
            raise RAGException(f"LLM generation failed: {str(e)}")
    
    async def _generate_llm_response(self, prompt: str) -> str:
        """Generate response using LLM."""
        if hasattr(self.llm, '_acall'):
            return await self.llm._acall(prompt)
        else:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.llm, prompt)
    
    def _create_fallback_response(self, query: str, generation_time: float, include_title: bool) -> GenerationResult:
        """Create fallback response."""
        return GenerationResult(
            title="Climate Assistant" if include_title else "",
            content=f"Thank you for your question about '{query[:50]}...'. I'm having technical difficulties. Please try again.",
            generation_time=generation_time,
            context_length=0
        )
    
    def _update_stats(self, generation_time: float):
        """Update performance stats."""
        total = self.performance_stats["total_generations"]
        current_avg = self.performance_stats["avg_generation_time"]
        new_avg = ((current_avg * (total - 1)) + generation_time) / total
        self.performance_stats["avg_generation_time"] = new_avg
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        total = self.performance_stats["total_generations"]
        total_parsing = self.performance_stats["parsing_successes"] + self.performance_stats["parsing_fallbacks"]
        
        return {
            **self.performance_stats,
            "context_building_method": "pure_score_based",
            "parsing_method": "smart_marker_detection",
            "parsing_success_rate": self.performance_stats["parsing_successes"] / total_parsing if total_parsing > 0 else 0.0,
            "start_ratio": self.performance_stats["start_conversations"] / total if total > 0 else 0.0,
            "continue_ratio": self.performance_stats["continue_conversations"] / total if total > 0 else 0.0
        }
    
    async def health_check(self) -> bool:
        """Health check."""
        try:
            return self.is_initialized and self.llm is not None and await self.prompt_manager.health_check()
        except:
            return False


# Global instance
response_generator_service = ResponseGeneratorService()


async def get_response_generator_service() -> ResponseGeneratorService:
    """Get the response generator service instance."""
    if not response_generator_service.is_initialized:
        await response_generator_service.initialize()
    return response_generator_service