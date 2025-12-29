"""
Enhanced prompt template manager with differentiated query processing for start vs continue conversations.
"""

from pathlib import Path
from typing import Any, Dict, Optional

from jinja2 import Environment, FileSystemLoader, Template

from app.config import get_settings
from app.core.exceptions import RAGException
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class EnhancedPromptManager:
    """Enhanced manager for prompt templates with differentiated query processing."""
    
    def __init__(self):
        self.templates_dir = Path(__file__).parent.parent.parent / "templates" / "prompts"
        self.env = None
        self.is_initialized = False
        
        self.language_names = {
            'en': 'English',
            'it': 'Italian',
            'pt': 'Portuguese',
            'el': 'Greek'
        }
    
    async def initialize(self):
        """Initialize the enhanced prompt manager with Jinja2 environment."""
        try:
            self.templates_dir.mkdir(parents=True, exist_ok=True)
            
            self.env = Environment(
                loader=FileSystemLoader(str(self.templates_dir)),
                trim_blocks=True,
                lstrip_blocks=True,
                keep_trailing_newline=True
            )
            
            self.is_initialized = True
            logger.info("✅ Prompt manager initialized with differentiated query processing")
            
        except Exception as e:
            logger.error(f"Failed to initialize prompt manager: {e}")
            raise RAGException(f"Prompt manager initialization failed: {str(e)}")
    
    def render_bot_identity_prompt(
        self,
        query: str,
        bot_identity_context: str,
        language: str = "en",
        query_type: str = "general_identity"
    ) -> str:
        """Render bot identity prompt for LLM processing using bot identity JSON context."""
        
        if not self.is_initialized:
            raise RAGException("Prompt manager not initialized")
        
        try:
            template = self.env.get_template("bot_identity.j2")
            
            return template.render(
                query=query,
                language_name=self.language_names.get(language, 'English'),
                query_type=query_type,
                identity_context=bot_identity_context
            )
            
        except Exception as e:
            logger.error(f"Error rendering bot identity prompt: {e}")
            raise RAGException(f"Bot identity prompt rendering failed: {str(e)}")
        
    def render_conversation_summary_prompt(
        self,
        existing_summary: Optional[str],
        new_conversation: str,
        max_length: int = 500
    ) -> str:
        """Render conversation summary prompt template."""
        
        if not self.is_initialized:
            raise RAGException("Prompt manager not initialized")
        
        try:
            template = self.env.get_template("conversation_summary.j2")
            
            return template.render(
                existing_summary=existing_summary,
                new_conversation=new_conversation,
                max_length=max_length
            )
            
        except Exception as e:
            logger.error(f"Error rendering conversation summary prompt: {e}")
            raise RAGException(f"Conversation summary prompt rendering failed: {str(e)}")        
    
    def render_start_conversation_prompt(
        self,
        original_query: str,
        processed_query: Optional[str],
        context: str,
        language: str = "en",
        difficulty_level: str = "low",
        was_processed: bool = False
    ) -> str:
        """Render start conversation prompt template - keeps TITLE tags."""
        
        if not self.is_initialized:
            raise RAGException("Prompt manager not initialized")
        
        try:
            template = self.env.get_template("start_conversation.j2")
            
            return template.render(
                original_query=original_query,
                processed_query=processed_query,
                context=context,
                language_name=self.language_names.get(language, 'English'),
                difficulty_level=difficulty_level,
                was_processed=was_processed
            )
            
        except Exception as e:
            logger.error(f"Error rendering start conversation prompt: {e}")
            raise RAGException(f"Start conversation prompt rendering failed: {str(e)}")
    
    def render_continue_conversation_prompt(
        self,
        original_query: str,
        processed_query: Optional[str],
        context: str,
        conversation_memory: str,
        language: str = "en",
        difficulty_level: str = "low",
        was_processed: bool = False,
        message_count: int = 1
    ) -> str:
        """Render continue conversation prompt template - no TITLE tags."""
        
        if not self.is_initialized:
            raise RAGException("Prompt manager not initialized")
        
        try:
            template = self.env.get_template("continue_conversation.j2")
            
            return template.render(
                original_query=original_query,
                processed_query=processed_query,
                context=context,
                conversation_memory=conversation_memory,
                language_name=self.language_names.get(language, 'English'),
                difficulty_level=difficulty_level,
                was_processed=was_processed,
                message_count=message_count
            )
            
        except Exception as e:
            logger.error(f"Error rendering continue conversation prompt: {e}")
            raise RAGException(f"Continue conversation prompt rendering failed: {str(e)}")
    
    def render_fallback_start_prompt(
        self,
        original_query: str,
        language: str = "en",
        difficulty_level: str = "low"
    ) -> str:
        """Render fallback start conversation prompt template - keeps TITLE tags."""
        
        if not self.is_initialized:
            raise RAGException("Prompt manager not initialized")
        
        try:
            template = self.env.get_template("fallback_start.j2")
            
            return template.render(
                original_query=original_query,
                language_name=self.language_names.get(language, 'English'),
                difficulty_level=difficulty_level
            )
            
        except Exception as e:
            logger.error(f"Error rendering fallback start prompt: {e}")
            raise RAGException(f"Fallback start prompt rendering failed: {str(e)}")
    
    def render_fallback_continue_prompt(
        self,
        original_query: str,
        conversation_memory: str,
        language: str = "en",
        difficulty_level: str = "low",
        message_count: int = 1,
        processed_query: Optional[str] = None,
        was_processed: bool = False
    ) -> str:
        """Render fallback continue conversation prompt template - no TITLE tags."""
        
        if not self.is_initialized:
            raise RAGException("Prompt manager not initialized")
        
        try:
            template = self.env.get_template("fallback_continue.j2")
            
            return template.render(
                original_query=original_query,
                processed_query=processed_query,
                conversation_memory=conversation_memory,
                language_name=self.language_names.get(language, 'English'),
                difficulty_level=difficulty_level,
                message_count=message_count,
                was_processed=was_processed
            )
            
        except Exception as e:
            logger.error(f"Error rendering fallback continue prompt: {e}")
            raise RAGException(f"Fallback continue prompt rendering failed: {str(e)}")
    
    def render_query_analysis_prompt(
        self,
        query: str,
        language: str = "en",
        conversation_context: Optional[str] = None
    ) -> str:
        """Render enhanced query analysis prompt template."""
        
        if not self.is_initialized:
            raise RAGException("Enhanced prompt manager not initialized")
        
        try:
            template = self.env.get_template("query_analysis.j2")
            
            return template.render(
                query=query,
                language=language,
                conversation_context=conversation_context
            )
            
        except Exception as e:
            logger.error(f"Error rendering query analysis prompt: {e}")
            raise RAGException(f"Query analysis prompt rendering failed: {str(e)}")
    
    def render_query_enhancement_start_prompt(
        self,
        query: str,
        language: str = "en",
        conversation_context: Optional[str] = None
    ) -> str:
        """Render query enhancement prompt for start conversations."""
        
        if not self.is_initialized:
            raise RAGException("Prompt manager not initialized")
        
        try:
            template = self.env.get_template("query_enhancement_start.j2")
            
            return template.render(
                query=query,
                language=language,
                conversation_context=conversation_context
            )
            
        except Exception as e:
            logger.error(f"Error rendering query enhancement start prompt: {e}")
            raise RAGException(f"Query enhancement start prompt rendering failed: {str(e)}")
    
    def render_query_enhancement_continue_prompt(
        self,
        query: str,
        language: str = "en",
        conversation_context: Optional[str] = None
    ) -> str:
        """Render query enhancement prompt for continue conversations."""
        
        if not self.is_initialized:
            raise RAGException("Prompt manager not initialized")
        
        try:
            template = self.env.get_template("query_enhancement_continue.j2")
            
            return template.render(
                query=query,
                language=language,
                conversation_context=conversation_context
            )
            
        except Exception as e:
            logger.error(f"Error rendering query enhancement continue prompt: {e}")
            raise RAGException(f"Query enhancement continue prompt rendering failed: {str(e)}")
    
    def render_knowledge_gap_response_prompt(
        self,
        query: str,
        language: str = "en",
        difficulty_level: str = "low"
    ) -> str:
        """Render improved knowledge gap response prompt template."""
        
        if not self.is_initialized:
            raise RAGException("Enhanced prompt manager not initialized")
        
        try:
            template = self.env.get_template("knowledge_gap_response.j2")
            
            language_name = self.language_names.get(language, 'English')
            
            return template.render(
                query=query,
                language_name=language_name,
                difficulty_level=difficulty_level
            )
            
        except Exception as e:
            logger.error(f"Error rendering knowledge gap response prompt: {e}")
            raise RAGException(f"Knowledge gap response prompt rendering failed: {str(e)}")
    
    def render_conversational_response_prompt(
        self,
        query: str,
        conversation_context: Optional[str] = None,
        language: str = "en"
    ) -> str:
        """Render conversational response generation prompt template."""
        
        if not self.is_initialized:
            raise RAGException("Prompt manager not initialized")
        
        try:
            template = self.env.get_template("conversational_response.j2")
            
            return template.render(
                query=query,
                conversation_context=conversation_context,
                language=language
            )
            
        except Exception as e:
            logger.error(f"Error rendering conversational response prompt: {e}")
            raise RAGException(f"Conversational response prompt rendering failed: {str(e)}")
    
    def render_error_response_prompt(
        self,
        query: str,
        error_type: str = "processing_error",
        language: str = "en"
    ) -> str:
        """Render error response prompt template."""
        
        if not self.is_initialized:
            raise RAGException("Prompt manager not initialized")
        
        try:
            template = self.env.get_template("error_response.j2")
            
            return template.render(
                query=query,
                error_type=error_type,
                language=language
            )
            
        except Exception as e:
            logger.error(f"Error rendering error response prompt: {e}")
            raise RAGException(f"Error response prompt rendering failed: {str(e)}")
    
    def render_llm_fallback_prompt(
        self,
        query: str,
        language: str = "en",
        difficulty_level: str = "low",
        conversation_type: str = "continue"
    ) -> str:
        """Render LLM fallback response prompt template."""
        
        if not self.is_initialized:
            raise RAGException("Prompt manager not initialized")
        
        try:
            template = self.env.get_template("llm_fallback_response.j2")
            
            language_name = self.language_names.get(language, 'English')
            
            return template.render(
                query=query,
                language_name=language_name,
                difficulty_level=difficulty_level,
                conversation_type=conversation_type
            )
            
        except Exception as e:
            logger.error(f"Error rendering LLM fallback prompt: {e}")
            raise RAGException(f"LLM fallback prompt rendering failed: {str(e)}")
    
    def render_emergency_response_prompt(
        self,
        query: str,
        language: str = "en"
    ) -> str:
        """Render emergency response prompt template."""
        
        if not self.is_initialized:
            raise RAGException("Prompt manager not initialized")
        
        try:
            template = self.env.get_template("emergency_llm_response.j2")
            
            return template.render(
                query=query,
                language=language
            )
            
        except Exception as e:
            logger.error(f"Error rendering emergency response prompt: {e}")
            raise RAGException(f"Emergency response prompt rendering failed: {str(e)}")
    
    def render_final_emergency_response_prompt(
        self,
        query: str,
        language: str = "en"
    ) -> str:
        """Render final emergency response prompt template."""
        
        if not self.is_initialized:
            raise RAGException("Prompt manager not initialized")
        
        try:
            template = self.env.get_template("final_emergency_response.j2")
            
            return template.render(
                query=query,
                language=language
            )
            
        except Exception as e:
            logger.error(f"Error rendering final emergency response prompt: {e}")
            raise RAGException(f"Final emergency response prompt rendering failed: {str(e)}")
    
    def render_custom_prompt(
        self,
        template_name: str,
        **kwargs
    ) -> str:
        """Render a custom prompt template with provided variables."""
        
        if not self.is_initialized:
            raise RAGException("Prompt manager not initialized")
        
        try:
            template = self.env.get_template(template_name)
            return template.render(**kwargs)
            
        except Exception as e:
            logger.error(f"Error rendering custom prompt {template_name}: {e}")
            raise RAGException(f"Custom prompt rendering failed: {str(e)}")
    
    def list_available_templates(self) -> list:
        """List all available prompt templates."""
        
        if not self.is_initialized:
            raise RAGException("Prompt manager not initialized")
        
        try:
            return self.env.list_templates()
        except Exception as e:
            logger.error(f"Error listing templates: {e}")
            return []
    
    def get_template_info(self) -> Dict[str, Any]:
        """Get information about available templates and their purposes."""
        
        template_info = {
            "conversation_templates": [
                "start_conversation.j2",
                "continue_conversation.j2",
                "fallback_start.j2",
                "fallback_continue.j2"
            ],
            "bot_identity_templates": [
                "bot_identity.j2"
            ],
            "llm_preprocessing_templates": [
                "query_analysis.j2",
                "conversational_response.j2",
                "query_enhancement_start.j2",
                "query_enhancement_continue.j2"
            ],
            "response_generation_templates": [
                "knowledge_gap_response.j2",
                "error_response.j2"
            ],
            "fallback_templates": [
                "llm_fallback_response.j2",
                "emergency_llm_response.j2",
                "final_emergency_response.j2"
            ],
            "web_search_templates": [
                "web_search_response.j2"
            ]
        }
        
        return template_info
    
    async def health_check(self) -> bool:
        """Check if enhanced prompt manager is healthy."""
        try:
            if not self.is_initialized:
                return False
            
            test_template = Template("Test: {{ test_var }}")
            result = test_template.render(test_var="success")
            
            required_templates = [
                "query_analysis.j2",
                "conversational_response.j2", 
                "knowledge_gap_response.j2",
                "llm_fallback_response.j2",
                "start_conversation.j2",
                "continue_conversation.j2",
                "fallback_continue.j2",
                "query_enhancement_start.j2",
                "query_enhancement_continue.j2",
                "bot_identity.j2"
            ]
            
            available_templates = self.list_available_templates()
            templates_exist = all(template in available_templates for template in required_templates)
            
            return "success" in result and templates_exist
            
        except Exception as e:
            logger.error(f"Prompt manager health check failed: {e}")
            return False


enhanced_prompt_manager = EnhancedPromptManager()


async def get_prompt_manager() -> EnhancedPromptManager:
    """Get the prompt manager instance."""
    if not enhanced_prompt_manager.is_initialized:
        await enhanced_prompt_manager.initialize()
    return enhanced_prompt_manager