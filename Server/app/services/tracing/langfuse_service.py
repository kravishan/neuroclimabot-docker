"""
Langfuse service with PROPER hierarchical tracing using context managers
"""

import logging
import time
from typing import Any, Dict, Optional, List
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Global langfuse client instance
_langfuse_client = None
_langfuse_enabled = False


def get_langfuse_client():
    """Get langfuse client instance"""
    global _langfuse_client
    
    if _langfuse_client is None:
        try:
            from app.config import get_settings
            settings = get_settings()
            
            if not settings.langfuse_is_configured:
                logger.info("Langfuse not configured - tracing disabled")
                return None
            
            from langfuse import Langfuse
            
            # Create client with minimal required parameters
            _langfuse_client = Langfuse(
                secret_key=settings.LANGFUSE_SECRET_KEY,
                public_key=settings.LANGFUSE_PUBLIC_KEY,
                host=settings.LANGFUSE_HOST,
                debug=getattr(settings, 'LANGFUSE_DEBUG', False),
                flush_at=getattr(settings, 'LANGFUSE_FLUSH_AT', 15),
                flush_interval=getattr(settings, 'LANGFUSE_FLUSH_INTERVAL', 10)
            )
            logger.info("✅ Langfuse client initialized")
            
        except ImportError:
            logger.info("Langfuse not installed - tracing disabled")
            _langfuse_client = None
        except Exception as e:
            logger.warning(f"Failed to initialize Langfuse: {e}")
            _langfuse_client = None
    
    return _langfuse_client


def is_langfuse_enabled(feature: str = None) -> bool:
    """Check if langfuse is enabled"""
    try:
        from app.config import get_settings
        settings = get_settings()
        
        if not settings.LANGFUSE_ENABLED:
            return False
        
        if not settings.langfuse_is_configured:
            return False
        
        return True
        
    except Exception:
        return False


class LangfuseService:
    """Langfuse service wrapper"""
    
    def __init__(self):
        self.client = None
        self.is_enabled = False
    
    async def initialize(self):
        """Initialize Langfuse service"""
        try:
            self.client = get_langfuse_client()
            self.is_enabled = is_langfuse_enabled()
            
            if self.is_enabled and self.client:
                logger.info("✅ Langfuse service initialized")
            else:
                logger.info("ℹ️  Langfuse service disabled")
                
        except Exception as e:
            logger.warning(f"Langfuse service initialization failed: {e}")
            self.is_enabled = False
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for Langfuse service"""
        try:
            if not self.is_enabled:
                return {
                    "status": "disabled",
                    "enabled": False,
                    "configured": False
                }
            
            if not self.client:
                return {
                    "status": "error", 
                    "enabled": True,
                    "configured": False,
                    "error": "Client not initialized"
                }
            
            return {
                "status": "healthy",
                "enabled": True,
                "configured": True
            }
            
        except Exception as e:
            return {
                "status": "error",
                "enabled": False,
                "configured": False,
                "error": str(e)
            }
    
    def get_config_info(self) -> Dict[str, Any]:
        """Get configuration information"""
        try:
            from app.config import get_settings
            settings = get_settings()
            
            return {
                "enabled": settings.LANGFUSE_ENABLED,
                "configured": settings.langfuse_is_configured,
                "host": settings.LANGFUSE_HOST,
                "public_key": settings.LANGFUSE_PUBLIC_KEY[:10] + "..." if settings.LANGFUSE_PUBLIC_KEY else None,
            }
            
        except Exception as e:
            return {
                "error": f"Failed to get config info: {e}",
                "enabled": False,
                "configured": False
            }
    
    async def shutdown(self):
        """Shutdown Langfuse service"""
        try:
            if self.client:
                self.client.flush()
                logger.info("Langfuse service shut down")
        except Exception as e:
            logger.error(f"Error shutting down Langfuse service: {e}")


# Global service instance
langfuse_service = LangfuseService()


async def get_langfuse_service() -> LangfuseService:
    """Get the Langfuse service instance"""
    if not langfuse_service.is_enabled:
        await langfuse_service.initialize()
    return langfuse_service


class ConversationTracer:
    """PROPER hierarchical conversation tracer using context managers"""
    
    def __init__(self, conversation_type: str, session_id: str, user_id: str = "anonymous"):
        self.conversation_type = conversation_type
        self.session_id = session_id
        self.user_id = user_id
        self.start_time = None
        self.main_span = None
        self.langfuse_client = None
        
    def start_conversation_trace(self, query: str, metadata: Dict = None):
        """Start main conversation trace using context manager"""
        if not is_langfuse_enabled():
            return

        # Check user consent for analytics - GDPR compliance
        if metadata and not metadata.get("analytics_consent", True):
            logger.info(f"⚠️  Skipping Langfuse trace - user declined analytics consent for session {self.session_id}")
            return

        self.langfuse_client = get_langfuse_client()
        if not self.langfuse_client:
            return

        try:
            self.start_time = time.time()
            
            # Create main trace with proper naming - THIS IS THE PARENT TRACE
            trace_name = "start_chat" if self.conversation_type == "start" else "continue_chat"
            
            # Use context manager to create the main span
            self.main_span = self.langfuse_client.start_as_current_span(
                name=trace_name,
                input=query,
                metadata={
                    "conversation_type": self.conversation_type,
                    "initial_query": query[:500],
                    "start_time": self.start_time,
                    "language": metadata.get("language", "en") if metadata else "en",
                    "difficulty": metadata.get("difficulty", "low") if metadata else "low",
                    "include_sources": metadata.get("include_sources", True) if metadata else True,
                    # Consent information for audit trail
                    "consent_given": metadata.get("consent_given", True) if metadata else True,
                    "analytics_consent": metadata.get("analytics_consent", True) if metadata else True,
                    "consent_version": metadata.get("consent_version") if metadata else None,
                    "consent_timestamp": metadata.get("consent_timestamp") if metadata else None,
                    **(metadata or {})
                }
            )
            
            # Update trace attributes
            self.main_span.update_trace(
                session_id=self.session_id,
                user_id=self.user_id,
                input=query,
                metadata={
                    "conversation_type": self.conversation_type,
                    "start_time": self.start_time,
                    **(metadata or {})
                }
            )
            
            logger.info(f"✅ Started Langfuse PARENT trace: {trace_name} for session {self.session_id}")
            
        except Exception as e:
            logger.error(f"Error starting conversation trace: {e}")
    
    def add_query_analysis_span(self, query: str, analysis_result: str = None):
        """Add query analysis as CHILD SPAN"""
        if not self.langfuse_client or not self.main_span:
            return
        
        try:
            # Create child span for query analysis
            with self.langfuse_client.start_as_current_span(
                name="query_analysis",
                input=query[:500],
                metadata={
                    "component": "llm_query_processor",
                    "step": "1_preprocessing",
                }
            ) as span:
                span.update(
                    output=analysis_result[:300] if analysis_result else "Query analyzed",
                    metadata={
                        "analysis_result": analysis_result[:300] if analysis_result else "Query analyzed"
                    }
                )
                logger.debug("✅ Added query_analysis CHILD SPAN")
            
        except Exception as e:
            logger.error(f"Error adding query analysis span: {e}")
    
    def add_retrieval_span(self, query: str, results: List[Dict] = None, metadata: Dict = None):
        """Add retrieval as CHILD SPAN"""
        if not self.langfuse_client or not self.main_span:
            return
        
        try:
            # Calculate result counts
            chunks_count = len([r for r in results if r.get("source") == "chunk"]) if results else 0
            summaries_count = len([r for r in results if r.get("source") == "summary"]) if results else 0
            graph_count = len([r for r in results if r.get("source") == "graph"]) if results else 0
            total_results = len(results) if results else 0
            
            # Create child span for retrieval
            with self.langfuse_client.start_as_current_span(
                name="retrieval",
                input=query[:500],
                metadata={
                    "component": "multi_source_retriever",
                    "step": "2_retrieval",
                    "total_results": total_results,
                    "chunks": chunks_count,
                    "summaries": summaries_count,
                    "graph": graph_count,
                    "retrieval_time": metadata.get("retrieval_time") if metadata else None,
                    **(metadata or {})
                }
            ) as span:
                span.update(
                    output=f"Retrieved {total_results} results: {chunks_count} chunks, {summaries_count} summaries, {graph_count} graph"
                )
                logger.debug("✅ Added retrieval CHILD SPAN")
            
        except Exception as e:
            logger.error(f"Error adding retrieval span: {e}")
    
    def add_reranking_span(self, query: str, input_count: int, output_count: int, metadata: Dict = None):
        """Add reranking as CHILD SPAN"""
        if not self.langfuse_client or not self.main_span:
            return
        
        try:
            # Create child span for reranking
            with self.langfuse_client.start_as_current_span(
                name="reranking",
                input=f"Reranking {input_count} results",
                metadata={
                    "component": "cross_encoder_reranker",
                    "step": "3_reranking",
                    "input_count": input_count,
                    "output_count": output_count,
                    "reranking_time": metadata.get("reranking_time") if metadata else None,
                    **(metadata or {})
                }
            ) as span:
                span.update(
                    output=f"Reranked to {output_count} results"
                )
                logger.debug("✅ Added reranking CHILD SPAN")
            
        except Exception as e:
            logger.error(f"Error adding reranking span: {e}")
    
    def add_llm_generation_span(self, prompt: str, response: str, model: str = "rag_llm", metadata: Dict = None):
        """Add LLM generation as CHILD SPAN"""
        if not self.langfuse_client or not self.main_span:
            return
        
        try:
            # Create child span for LLM generation
            with self.langfuse_client.start_as_current_span(
                name="llm_generation",
                input=prompt[:500],
                metadata={
                    "component": "response_generator",
                    "step": "4_generation",
                    "model": model,
                    "conversation_type": metadata.get("conversation_type") if metadata else self.conversation_type,
                    "language": metadata.get("language") if metadata else "en",
                    "fallback": metadata.get("fallback", False) if metadata else False,
                    "generation_time": metadata.get("generation_time") if metadata else None,
                    **(metadata or {})
                }
            ) as span:
                span.update(
                    output=response[:500]
                )
                logger.debug("✅ Added llm_generation CHILD SPAN")
            
        except Exception as e:
            logger.error(f"Error adding LLM generation span: {e}")
    
    def add_url_resolution_span(self, doc_names: List[str], resolved_urls: Dict[str, str]):
        """Add URL resolution as CHILD SPAN"""
        if not self.langfuse_client or not self.main_span:
            return
        
        try:
            # Create child span for URL resolution
            with self.langfuse_client.start_as_current_span(
                name="url_resolution",
                input=f"Resolving URLs for {len(doc_names)} documents",
                metadata={
                    "component": "inventory_service",
                    "step": "5_post_processing",
                    "document_count": len(doc_names),
                    "resolved_count": len(resolved_urls),
                    "sample_documents": doc_names[:5],
                    "resolution_rate": len(resolved_urls) / len(doc_names) if doc_names else 0
                }
            ) as span:
                span.update(
                    output=f"Resolved {len(resolved_urls)} URLs"
                )
                logger.debug("✅ Added url_resolution CHILD SPAN")
            
        except Exception as e:
            logger.error(f"Error adding URL resolution span: {e}")
    
    def add_fallback_span(self, reason: str, fallback_type: str, metadata: Dict = None):
        """Add fallback processing as CHILD SPAN"""
        if not self.langfuse_client or not self.main_span:
            return
        
        try:
            # Create child span for fallback
            with self.langfuse_client.start_as_current_span(
                name="fallback_processing",
                input=f"Fallback triggered: {reason}",
                metadata={
                    "component": "llm_fallback",
                    "step": "fallback",
                    "reason": reason,
                    "fallback_type": fallback_type,
                    **(metadata or {})
                }
            ) as span:
                span.update(
                    output=f"Using {fallback_type} fallback"
                )
                logger.debug("✅ Added fallback_processing CHILD SPAN")
            
        except Exception as e:
            logger.error(f"Error adding fallback span: {e}")
    
    def add_error(self, error: str, component: str = "unknown"):
        """Add error as CHILD SPAN"""
        if not self.langfuse_client or not self.main_span:
            return
        
        try:
            # Create child span for error
            with self.langfuse_client.start_as_current_span(
                name="error_occurred",
                input=f"Error in {component}",
                metadata={
                    "error": True,
                    "error_message": str(error)[:500],
                    "error_component": component,
                    "step": "error_handling"
                }
            ) as span:
                span.update(
                    output="Error handled",
                    level="ERROR"
                )
                logger.debug("✅ Added error_occurred CHILD SPAN")
            
        except Exception as e:
            logger.error(f"Error adding error span: {e}")
    
    def end_conversation_trace(self, final_response: str, metadata: Dict = None):
        """End conversation trace"""
        if not self.main_span:
            return
        
        try:
            duration = time.time() - self.start_time if self.start_time else 0
            
            # Update the main span with final output and metadata
            self.main_span.update(
                output=final_response[:500],
                metadata={
                    "conversation_type": self.conversation_type,
                    "total_duration": duration,
                    "completion_time": time.time(),
                    "success": True,
                    "response_length": len(final_response),
                    **(metadata or {})
                }
            )
            
            # Update trace attributes
            self.main_span.update_trace(
                output=final_response[:500],
                metadata={
                    "total_duration": duration,
                    "success": True,
                    "session_id": self.session_id,
                    **(metadata or {})
                }
            )
            
            # End the main span
            self.main_span.end()
            
            # Flush the trace to Langfuse
            if self.langfuse_client:
                self.langfuse_client.flush()
            
            logger.info(f"✅ Ended Langfuse PARENT trace for session {self.session_id}, duration: {duration:.3f}s")
                
        except Exception as e:
            logger.error(f"Error ending conversation trace: {e}")


def trace_api_call(operation_name: str):
    """Decorator for API calls - creates separate trace for non-conversation operations"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            if not is_langfuse_enabled():
                return await func(*args, **kwargs)
            
            client = get_langfuse_client()
            if not client:
                return await func(*args, **kwargs)
            
            start_time = time.time()
            
            # Create a separate trace for API operations using context manager
            with client.start_as_current_span(
                name=f"api_{operation_name}",
                metadata={
                    "type": "api_call",
                    "operation": operation_name,
                    "start_time": start_time
                }
            ) as span:
                try:
                    result = await func(*args, **kwargs)
                    
                    span.update(
                        output="API call successful",
                        metadata={
                            "status": "success",
                            "duration": time.time() - start_time
                        }
                    )
                    client.flush()
                    return result
                    
                except Exception as e:
                    span.update(
                        output=f"API call failed: {str(e)[:200]}",
                        level="ERROR",
                        metadata={
                            "status": "error",
                            "error": str(e)[:500],
                            "duration": time.time() - start_time
                        }
                    )
                    client.flush()
                    raise
                
        return wrapper
    return decorator