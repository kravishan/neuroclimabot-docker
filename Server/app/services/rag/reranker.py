"""
Ultra-fast reranker replacement - no ML dependencies.
"""

import asyncio
import time
from typing import Any, Dict, List, Optional

from app.config import get_settings
from app.core.exceptions import RAGException
from app.utils.logger import get_logger
from app.constants import (
    TITLE_EXACT_MATCH_BOOST,
    TITLE_PARTIAL_MATCH_BOOST,
    SOURCE_EXACT_MATCH_BOOST,
    QUERY_TERM_MATCH_BOOST,
    COLLECTION_PRIORITY_BOOST,
    CHUNK_CONTENT_PREVIEW_LENGTH
)

logger = get_logger(__name__)
settings = get_settings()


class UltraFastReranker:
    """Ultra-fast reranker using only similarity scores and query matching."""
    
    def __init__(self):
        self.is_initialized = True  # No initialization needed
        self.min_score_threshold = getattr(settings, 'RERANKER_MIN_SCORE', 0.3)
        self.top_k_default = getattr(settings, 'TOP_K_RERANK', 8)
    
    async def initialize(self):
        """No initialization needed for ultra-fast reranker."""
        pass
    
    async def rerank_results(
        self, 
        query: str, 
        results: List[Dict[str, Any]], 
        top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Ultra-fast reranking using scores and query matching."""
        
        if not results:
            return []
        
        top_k = top_k or self.top_k_default
        start_time = time.perf_counter()
        
        try:
            logger.info(f"Ultra-fast reranking {len(results)} results")
            
            query_lower = query.lower().strip()
            query_words = set(query_lower.split())
            
            # Process each result
            for result in results:
                # Get base similarity score
                base_score = (
                    result.get("score", 0.0) or 
                    result.get("similarity_score", 0.0) or 
                    0.0
                )
                
                # Extract content for matching
                content = self._extract_content(result).lower()
                content_words = set(content.split())
                
                # Calculate boosts
                word_overlap_boost = self._calculate_word_overlap_boost(query_words, content_words)
                phrase_boost = self._calculate_phrase_boost(query_lower, content)
                source_boost = self._calculate_source_boost(result)
                
                # Final rerank score
                total_boost = word_overlap_boost + phrase_boost + source_boost
                final_score = min(1.0, max(0.0, base_score + total_boost))
                
                result["rerank_score"] = final_score
                result["rerank_raw_score"] = final_score
            
            # Sort by rerank score (descending)
            reranked = sorted(
                results,
                key=lambda x: x.get("rerank_raw_score", 0.0),
                reverse=True
            )
            
            # Filter by threshold and limit
            filtered = [
                r for r in reranked 
                if r.get("rerank_score", 0.0) >= self.min_score_threshold
            ][:top_k]
            
            processing_time = time.perf_counter() - start_time
            logger.info(f"Ultra-fast reranking completed in {processing_time:.4f}s -> {len(filtered)} results")
            
            return filtered
            
        except Exception as e:
            logger.error(f"Ultra-fast reranking error: {e}")
            # Fallback: return top results by original score
            return sorted(
                results, 
                key=lambda x: x.get("score", x.get("similarity_score", 0.0)), 
                reverse=True
            )[:top_k]
    
    def _extract_content(self, result: Dict[str, Any]) -> str:
        """Extract content from result for analysis."""
        source_type = result.get("source", "")
        
        if source_type == "chunk":
            content = result.get("content", "")
        elif source_type == "summary":
            content = result.get("summary", result.get("content", ""))
        elif source_type == "graph":
            content = result.get("content", "")
            # Add entity information for graph results
            entities = result.get("entities", [])
            if entities:
                content += " " + " ".join(entities[:3])
        else:
            content = (
                result.get("content", "") or 
                result.get("summary", "") or 
                result.get("text", "") or 
                result.get("doc_name", "")
            )
        
        # Truncate for performance
        return content[:CHUNK_CONTENT_PREVIEW_LENGTH] if content else ""
    
    def _calculate_word_overlap_boost(self, query_words: set, content_words: set) -> float:
        """Calculate boost based on word overlap."""
        if not query_words or not content_words:
            return 0.0
        
        overlap_count = len(query_words & content_words)
        overlap_ratio = overlap_count / len(query_words)
        
        # Boost up to TITLE_EXACT_MATCH_BOOST based on overlap
        return min(TITLE_EXACT_MATCH_BOOST, overlap_ratio * 0.2)
    
    def _calculate_phrase_boost(self, query_lower: str, content_lower: str) -> float:
        """Calculate boost for exact phrase matches."""
        if not query_lower or not content_lower:
            return 0.0
        
        # Exact query match
        if query_lower in content_lower:
            return TITLE_PARTIAL_MATCH_BOOST

        # Partial phrase matches for longer queries
        if len(query_lower) > 20:
            query_parts = query_lower.split()
            if len(query_parts) >= 3:
                # Check for 3-word phrases
                for i in range(len(query_parts) - 2):
                    phrase = " ".join(query_parts[i:i+3])
                    if phrase in content_lower:
                        return SOURCE_EXACT_MATCH_BOOST
        
        return 0.0
    
    def _calculate_source_boost(self, result: Dict[str, Any]) -> float:
        """Calculate boost based on source type."""
        source_type = result.get("source", "")
        
        # Slight preference for different source types
        if source_type == "chunk":
            return QUERY_TERM_MATCH_BOOST  # Chunks are most detailed
        elif source_type == "summary":
            return QUERY_TERM_MATCH_BOOST / 2  # Summaries are good overviews
        elif source_type == "graph":
            return COLLECTION_PRIORITY_BOOST  # Graph data might have unique insights
        
        return 0.0
    
    async def health_check(self) -> bool:
        """Health check - always healthy since no dependencies."""
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        return {
            "type": "ultra_fast_score_based",
            "dependencies": "none",
            "speed": "ultra_fast",
            "is_initialized": True,
            "min_score_threshold": self.min_score_threshold
        }


# Global ultra-fast reranker instance
ultra_fast_reranker = UltraFastReranker()


async def get_reranker_service() -> UltraFastReranker:
    """Get the ultra-fast reranker service."""
    return ultra_fast_reranker