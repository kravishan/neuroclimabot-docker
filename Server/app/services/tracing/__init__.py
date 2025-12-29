"""Tracing services for observability and monitoring."""

# Import with fallbacks to avoid circular imports
try:
    from .langfuse_service import (
        get_langfuse_service,
        get_langfuse_client,
        is_langfuse_enabled,
        langfuse_service,
        ConversationTracer,
        trace_api_call
    )
except ImportError as e:
    # Fallback implementations to avoid breaking the app
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"Could not import langfuse_service: {e}")
    
    # Create minimal fallback implementations
    async def get_langfuse_service():
        return None
    
    def get_langfuse_client():
        return None
    
    def is_langfuse_enabled(feature=None):
        return False
    
    langfuse_service = None
    
    # Simple fallback tracer
    class ConversationTracer:
        def __init__(self, conversation_type: str, session_id: str, user_id: str = "anonymous"):
            self.conversation_type = conversation_type
            self.session_id = session_id
            self.user_id = user_id
        
        def start_conversation_trace(self, query: str, metadata: dict = None):
            pass
        
        def add_query_analysis_span(self, query: str, analysis_result: str = None):
            pass
        
        def add_retrieval_span(self, query: str, results: list = None, metadata: dict = None):
            pass
        
        def add_reranking_span(self, query: str, input_count: int, output_count: int, metadata: dict = None):
            pass
        
        def add_llm_generation_span(self, prompt: str, response: str, model: str = "rag_llm", metadata: dict = None):
            pass
        
        def add_url_resolution_span(self, doc_names: list, resolved_urls: dict):
            pass
        
        def add_fallback_span(self, reason: str, fallback_type: str, metadata: dict = None):
            pass
        
        def add_error(self, error: str, component: str = "unknown"):
            pass
        
        def end_conversation_trace(self, final_response: str, metadata: dict = None):
            pass
    
    def trace_api_call(operation_name: str):
        def decorator(func):
            return func
        return decorator

__all__ = [
    "get_langfuse_service",
    "get_langfuse_client", 
    "is_langfuse_enabled",
    "langfuse_service",
    "ConversationTracer",
    "trace_api_call"
]