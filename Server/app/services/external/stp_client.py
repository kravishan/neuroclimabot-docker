"""
Social Tipping Point (STP) service client with confidence and similarity threshold checking
Clean version - parses 5 numbered qualifying factors and validates both confidence score and similarity
"""

import aiohttp
import re
from typing import Dict, Any, List

from app.config import get_settings
from app.services.tracing import get_langfuse_client, is_langfuse_enabled
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class STPStructuredResponse:
    """Structured STP response for frontend display."""
    
    def __init__(
        self, 
        text: str, 
        qualifying_factors: List[str] = None, 
        source: str = "external_stp_server",
        confidence: float = 0.0,
        similarity: float = 0.0
    ):
        self.text = text
        self.qualifying_factors = qualifying_factors or []
        self.source = source
        self.confidence = confidence
        self.similarity = similarity
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for schema compatibility."""
        return {
            "text": self.text,
            "qualifying_factors": self.qualifying_factors,
            "source": self.source
        }


class STPClient:
    """Client for external Social Tipping Point service with confidence and similarity checking."""
    
    def __init__(self):
        self.base_url = settings.STP_SERVICE_URL
        self.stp_endpoint = settings.STP_SERVICE_ENDPOINT
        self.timeout = settings.STP_SERVICE_TIMEOUT
        self.confidence_threshold = settings.STP_CONFIDENCE_THRESHOLD
        self.similarity_threshold = getattr(settings, 'STP_SIMILARITY_THRESHOLD', 0.5)  # Default 0.5
        self.fallback_message = settings.STP_FALLBACK_MESSAGE
        self.is_initialized = True
    
    async def get_social_tipping_point_structured(
        self, 
        query: str, 
        top_k: int = None, 
        include_metadata: bool = None,
        min_similarity: float = None
    ) -> STPStructuredResponse:
        """Get social tipping point as structured data with confidence and similarity validation."""
        
        if not query or not query.strip():
            return self._get_fallback_response()
        
        # Use settings defaults if not provided
        if top_k is None:
            top_k = settings.STP_TOP_K
        if include_metadata is None:
            include_metadata = settings.STP_INCLUDE_METADATA
        if min_similarity is None:
            min_similarity = self.similarity_threshold
        
        if is_langfuse_enabled():
            langfuse_client = get_langfuse_client()
            with langfuse_client.start_as_current_span(
                name="stp_search_structured",
                input=query[:200],
                metadata={
                    "component": "stp_service",
                    "step": "social_tipping_point_search",
                    "top_k": top_k,
                    "service": "external_server",
                    "confidence_threshold": self.confidence_threshold,
                    "similarity_threshold": min_similarity
                }
            ) as span:
                try:
                    result = await self._make_stp_request(query, top_k, include_metadata, min_similarity)
                    
                    span.update(
                        output=f"Text: {result.text[:100]}..., QF: {len(result.qualifying_factors)} factors, Confidence: {result.confidence:.3f}, Similarity: {result.similarity:.3f}",
                        metadata={
                            "stp_search_success": True,
                            "qualifying_factors_count": len(result.qualifying_factors),
                            "confidence_score": result.confidence,
                            "similarity_score": result.similarity,
                            "above_confidence_threshold": result.confidence >= self.confidence_threshold,
                            "above_similarity_threshold": result.similarity >= min_similarity
                        }
                    )
                    return result
                except Exception as e:
                    span.update(
                        output=f"STP search failed: {str(e)}",
                        level="ERROR",
                        metadata={"stp_search_success": False, "error": str(e)}
                    )
                    logger.error(f"Error getting structured social tipping point: {e}")
                    return self._get_fallback_response()
        else:
            try:
                return await self._make_stp_request(query, top_k, include_metadata, min_similarity)
            except Exception as e:
                logger.error(f"Error getting structured social tipping point: {e}")
                return self._get_fallback_response()
    
    async def get_social_tipping_point(
        self, 
        query: str, 
        top_k: int = None, 
        include_metadata: bool = None,
        min_similarity: float = None
    ) -> str:
        """Get social tipping point as formatted string (legacy method)."""
        structured_result = await self.get_social_tipping_point_structured(
            query, top_k, include_metadata, min_similarity
        )
        
        if not structured_result.text or structured_result.text == self.fallback_message:
            return structured_result.text
        
        if structured_result.qualifying_factors:
            factors_text = "\n".join(
                f"{i+1}. {factor}" 
                for i, factor in enumerate(structured_result.qualifying_factors)
            )
            return f"{structured_result.text}\n\nQualifying factors:\n{factors_text}"
        else:
            return structured_result.text
    
    async def get_social_tipping_point_silent(
        self, 
        query: str, 
        top_k: int = None, 
        include_metadata: bool = None,
        min_similarity: float = None
    ) -> str:
        """Get social tipping point as formatted string WITHOUT tracing (legacy method)."""
        try:
            structured_result = await self._make_stp_request(
                query, top_k, include_metadata, min_similarity
            )
            
            if not structured_result.text or structured_result.text == self.fallback_message:
                return structured_result.text
            
            if structured_result.qualifying_factors:
                factors_text = "\n".join(
                    f"{i+1}. {factor}" 
                    for i, factor in enumerate(structured_result.qualifying_factors)
                )
                return f"{structured_result.text}\n\nQualifying factors:\n{factors_text}"
            else:
                return structured_result.text
        except Exception as e:
            logger.error(f"Error in silent STP search: {e}")
            return self.fallback_message
    
    async def _make_stp_request(
        self, 
        query: str, 
        top_k: int, 
        include_metadata: bool,
        min_similarity: float
    ) -> STPStructuredResponse:
        """Make STP request and return structured data with confidence and similarity validation."""
        
        payload = {
            "text": query,
            "top_k": top_k,
            "include_metadata": include_metadata,
            "min_similarity": min_similarity
        }
        
        url = f"{self.base_url}{self.stp_endpoint}"
        
        logger.debug(f"🔍 STP request: {url} with min_similarity={min_similarity}")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, 
                json=payload, 
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return self._extract_stp_from_response(result, min_similarity)
                else:
                    logger.error(f"STP search failed with status {response.status}")
                    return self._get_fallback_response()
    
    def _extract_stp_from_response(
        self, 
        response_data: Dict[str, Any],
        min_similarity: float
    ) -> STPStructuredResponse:
        """Extract structured STP data from API response with confidence and similarity checking."""
        try:
            if not isinstance(response_data, dict):
                logger.warning("STP response is not a dictionary")
                return self._get_fallback_response()
            
            # Check if results are empty (filtered by min_similarity)
            results = response_data.get("results", [])
            total_results = response_data.get("total_results", 0)
            
            if total_results == 0 or not results or not isinstance(results, list):
                logger.info(f"No STP results found with similarity >= {min_similarity}")
                return STPStructuredResponse(
                    text=self.fallback_message,
                    qualifying_factors=[],
                    source="no_results_above_threshold",
                    confidence=0.0,
                    similarity=0.0
                )
            
            # Get the best result (first one after filtering)
            best_result = results[0]
            if not isinstance(best_result, dict):
                logger.warning("Best STP result is not a dictionary")
                return self._get_fallback_response()
            
            # Extract confidence score
            confidence = float(best_result.get("stp_confidence", 0.0))
            
            # Extract similarity score
            similarity = float(best_result.get("similarity_score", 0.0))
            
            # Check confidence threshold
            if confidence < self.confidence_threshold:
                logger.info(
                    f"STP confidence {confidence:.3f} below threshold {self.confidence_threshold}"
                )
                return STPStructuredResponse(
                    text=self.fallback_message,
                    qualifying_factors=[],
                    source="below_confidence_threshold",
                    confidence=confidence,
                    similarity=similarity
                )
            
            # Check similarity threshold (double-check even though server filtered)
            if similarity < min_similarity:
                logger.info(
                    f"STP similarity {similarity:.3f} below threshold {min_similarity}"
                )
                return STPStructuredResponse(
                    text=self.fallback_message,
                    qualifying_factors=[],
                    source="below_similarity_threshold",
                    confidence=confidence,
                    similarity=similarity
                )
            
            # Extract main text (rephrased content)
            main_text = best_result.get("rephrased_content", "").strip()
            if not main_text or len(main_text) < 10:
                logger.warning("STP text too short or empty")
                return self._get_fallback_response()
            
            # Extract qualifying factors
            qualifying_factors = []
            raw_qf = best_result.get("qualifying_factors", None)
            
            if raw_qf and isinstance(raw_qf, str):
                qualifying_factors = self._parse_qualifying_factors(raw_qf)
            elif raw_qf and isinstance(raw_qf, list):
                qualifying_factors = [str(f).strip() for f in raw_qf if f]
            
            logger.info(
                f"✅ STP extracted: confidence={confidence:.3f}, "
                f"similarity={similarity:.3f}, factors={len(qualifying_factors)}"
            )
            
            return STPStructuredResponse(
                text=main_text,
                qualifying_factors=qualifying_factors,
                source="external_stp_server",
                confidence=confidence,
                similarity=similarity
            )
            
        except Exception as e:
            logger.error(f"Error extracting STP from response: {e}")
            return self._get_fallback_response()
    
    def _parse_qualifying_factors(self, factors_string: str) -> List[str]:
        """Parse 5 numbered qualifying factors from a single string."""
        factors = []
        
        try:
            # Normalize whitespace
            normalized = re.sub(r'\s+', ' ', factors_string.strip())
            
            # Split by numbered patterns (1., 2., 3., 4., 5.)
            parts = re.split(r'(?=\d+\.\s+)', normalized)
            parts = [p.strip() for p in parts if p.strip()]
            
            for part in parts:
                # Extract text after the number
                if re.match(r'^\d+\.\s+', part):
                    factor_match = re.match(r'^\d+\.\s+(.+)$', part)
                    if factor_match:
                        factor_text = factor_match.group(1).strip()
                        if factor_text:
                            factors.append(factor_text)
            
            # Validate count
            if len(factors) != 5:
                logger.warning(f"Expected 5 qualifying factors, but parsed {len(factors)}")
            
            # Limit to 5 factors
            return factors[:5]
            
        except Exception as e:
            logger.error(f"Error parsing qualifying factors: {e}")
            return []
    
    def _get_fallback_response(self) -> STPStructuredResponse:
        """Get fallback response when STP request fails or thresholds not met."""
        return STPStructuredResponse(
            text=self.fallback_message,
            qualifying_factors=[],
            source="fallback",
            confidence=0.0,
            similarity=0.0
        )
    
    async def health_check(self) -> bool:
        """Check if STP service is healthy."""
        try:
            test_payload = {
                "text": "climate change",
                "top_k": 1,
                "include_metadata": True,
                "min_similarity": 0.0  # No filtering for health check
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}{self.stp_endpoint}",
                    json=test_payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        # Check if we got a valid response structure
                        return bool(
                            result and 
                            "status" in result and 
                            result.get("status") == "success"
                        )
                    return False
        except Exception as e:
            logger.error(f"STP service health check failed: {e}")
            return False
    
    def get_service_info(self) -> Dict[str, Any]:
        """Get information about the STP service configuration."""
        return {
            "base_url": self.base_url,
            "endpoint": self.stp_endpoint,
            "full_url": f"{self.base_url}{self.stp_endpoint}",
            "timeout": self.timeout,
            "confidence_threshold": self.confidence_threshold,
            "similarity_threshold": self.similarity_threshold,
            "fallback_message": self.fallback_message,
            "service_type": "external_server",
            "supports_qualifying_factors": True,
            "expected_factor_count": 5,
            "structured_response": True,
            "confidence_filtering_enabled": True,
            "similarity_filtering_enabled": True,
            "is_initialized": self.is_initialized
        }


# Global instance
_stp_client = None


def get_stp_client() -> STPClient:
    """Get STP client instance."""
    global _stp_client
    if _stp_client is None:
        _stp_client = STPClient()
    return _stp_client