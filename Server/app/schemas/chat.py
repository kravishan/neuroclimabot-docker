"""
Updated chat schemas with proper STP structure for 5 qualifying factors
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .common import BaseResponse


class ChatMessage(BaseModel):
    """Chat message model."""
    
    id: UUID = Field(default_factory=uuid4)
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Optional[Dict] = None


class ChatSession(BaseModel):
    """Chat session model with conversation tracking."""
    
    id: UUID = Field(default_factory=uuid4)
    title: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    message_count: int = 0
    language: str = "en"
    difficulty_level: str = "low"
    is_active: bool = True
    conversation_type: Optional[str] = None  # "start" or "continue"


class StartConversationRequest(BaseModel):
    """Request model for starting a new conversation."""
    
    message: str = Field(..., min_length=1, max_length=2000, description="Initial user message")
    language: str = Field("en", description="Response language (en, it, pt, el)")
    difficulty_level: str = Field("low", description="Response complexity (low, high)")
    user_id: Optional[str] = Field("anonymous", description="User identifier")
    include_sources: bool = Field(True, description="Include source documents")
    max_tokens: Optional[int] = Field(None, ge=1, le=4000, description="Maximum response tokens")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="Response creativity")


class ContinueConversationRequest(BaseModel):
    """Request model for continuing an existing conversation."""
    
    message: str = Field(..., min_length=1, max_length=2000, description="Follow-up user message")
    language: Optional[str] = Field(None, description="Response language override")
    difficulty_level: Optional[str] = Field(None, description="Response complexity override")
    include_sources: bool = Field(True, description="Include source documents")
    max_tokens: Optional[int] = Field(None, ge=1, le=4000, description="Maximum response tokens")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="Response creativity")


class ConsentMetadata(BaseModel):
    """GDPR consent metadata from frontend."""

    consent_given: bool = Field(True, description="Whether user has provided consent")
    analytics_consent: bool = Field(True, description="Whether user consented to analytics/training data")
    consent_version: Optional[str] = Field(None, description="Consent policy version")
    consent_timestamp: Optional[str] = Field(None, description="When consent was given")


class ChatRequest(BaseModel):
    """Generic chat request model (for backward compatibility)."""

    message: str = Field(..., min_length=1, max_length=2000, description="User message")
    session_id: Optional[UUID] = None
    language: str = Field("en", description="Response language")
    difficulty_level: str = Field("low", description="Response complexity")
    stream: bool = Field(False, description="Enable streaming response")
    include_sources: bool = Field(True, description="Include source documents")
    max_tokens: Optional[int] = Field(None, ge=1, le=4000, description="Maximum response tokens")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="Response creativity")
    consent_metadata: Optional[ConsentMetadata] = Field(None, description="GDPR consent metadata")


class Source(BaseModel):
    """Source reference with Pydantic V2 compatibility."""
    
    title: str = Field(..., description="Clean document title for display")
    doc_name: str = Field(..., description="Document name from database")
    url: str = Field(..., description="Document URL from inventory")
    similarity_score: float = Field(..., ge=0.0, le=100.0, description="Similarity score as percentage")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "Climate Policy Framework 2024",
                "doc_name": "Climate Policy Framework 2024.pdf",
                "url": "https://example.com/documents/climate-policy-2024.pdf",
                "similarity_score": 92.5
            }
        }
    }


class SocialTippingPoint(BaseModel):
    """
    Social tipping point information with structured qualifying factors.
    
    The qualifying_factors field contains exactly 5 factors from the external STP service:
    1. Environmental problems with perceived societal consequences
    2. Shared awareness of the problem
    3. Shared understanding of causes and effects
    4. Expressed perception for a change regarding habits/lifestyle
    5. Socio-political demand for explanations, solutions and actions
    
    Each factor includes the factor name, level (Strong/Moderate/Weak/Not evident), 
    and a description.
    """
    
    text: str = Field(
        ..., 
        description="Main social tipping point description text"
    )
    qualifying_factors: List[str] = Field(
        default_factory=list, 
        description="List of 5 qualifying factor descriptions with levels and details"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "text": "The GFCM implements spatial management measures and establishes Fisheries Restricted Areas (FRAs) to protect vulnerable marine ecosystems and fish stocks in the Mediterranean Sea.",
                "qualifying_factors": [
                    "Environmental problems with perceived societal consequences: Strong, The state of fish stocks in the Mediterranean is described as being in poor condition, with significant implications for marine ecosystems and fishing communities.",
                    "Shared awareness of the problem: Strong, The GFCM is aware of the need to protect vulnerable ecosystems and fish stocks, demonstrating institutional recognition of environmental challenges.",
                    "Shared understanding of causes and effects, up to a certain degree: Moderate, The need to balance fisheries management with environmental protection is understood, though complexities remain in implementation.",
                    "Expressed perception for a change regarding habits/lifestyle: Not evident, There is no mention of changing individual or collective behaviors at the community or industry level.",
                    "Socio-political demand for explanations, solutions and actions: Strong, The GFCM implements spatial management measures and establishes FRAs to address environmental concerns, showing strong policy response."
                ]
            }
        }
    }


class SpecializedProcessing(BaseModel):
    """Information about specialized conversation processing."""
    
    type: str = Field(..., description="Processing type: start_conversation or continue_conversation")
    features: List[str] = Field(default_factory=list, description="Processing features applied")
    query_preprocessed: bool = Field(False, description="Whether query was preprocessed")
    preprocessing_details: Dict = Field(default_factory=dict, description="Preprocessing details")
    context_used: Optional[Dict] = Field(None, description="Context information used")


class ChatResponse(BaseResponse):
    """
    Chat response with structured STP containing 5 qualifying factors.

    The social_tipping_point field is structured with:
    - text: Main tipping point description
    - qualifying_factors: Array of exactly 5 factor descriptions

    Frontend should display these separately for better UX.
    """

    # Core response data that frontend needs (REQUIRED)
    session_id: UUID
    message_id: UUID
    response: str = Field(..., description="The main chat response content")
    title: Optional[str] = Field(None, description="Response title (None for continue conversations)")
    social_tipping_point: SocialTippingPoint = Field(
        ...,
        description="Social tipping point with structured text and 5 qualifying factors"
    )
    sources: List[Source] = Field(default_factory=list, description="Source documents")
    total_references: int = Field(0, description="Total number of unique references found")
    uses_rag: bool = Field(True, description="Whether RAG was used for this response (false for conversational/bot_identity)")


class StreamChatResponse(BaseModel):
    """Streaming chat response chunk."""
    
    session_id: UUID
    message_id: UUID
    chunk: str
    is_final: bool = False
    conversation_type: str = "continue"
    sources: Optional[List[Source]] = None
    total_references: Optional[int] = None
    title: Optional[str] = None
    social_tipping_point: Optional[SocialTippingPoint] = None
    parallel_processing_time: Optional[float] = None


class ConversationSummary(BaseModel):
    """Conversation summary with metadata."""
    
    session_id: UUID
    title: str
    summary: str
    message_count: int
    last_activity: datetime
    language: str
    conversation_type: str = Field(..., description="Type: start or continue")
    specialized_features_used: Optional[List[str]] = None
    parallel_processing_enabled: bool = Field(True, description="Parallel processing support")


class SessionListResponse(BaseResponse):
    """Session list response."""
    
    sessions: List[ConversationSummary]


class ConversationStats(BaseModel):
    """Detailed conversation statistics."""
    
    session_id: UUID
    message_count: int
    conversation_type: str
    language: str
    difficulty_level: str
    processing_features_used: List[str]
    total_processing_time: float
    average_response_time: float
    parallel_processing_time: Optional[float] = None
    parallel_time_savings: Optional[float] = None
    query_preprocessing_count: int
    context_sources_used: Dict[str, int]
    memory_context_available: bool
    created_at: datetime
    last_activity: datetime
    
    # RAG-only statistics
    rag_responses: int = Field(0, description="Number of responses from RAG")
    source_breakdown: Dict[str, int] = Field(default_factory=dict, description="Breakdown by source type")
    
    # STP statistics
    stp_requests: int = Field(0, description="Number of STP requests made")
    stp_with_qualifying_factors: int = Field(0, description="Number of STPs with all 5 factors")


class ProcessingCapabilities(BaseModel):
    """Information about conversation processing capabilities."""
    
    conversation_types: Dict[str, Dict] = Field(
        default_factory=lambda: {
            "start_conversation": {
                "description": "First-time user interactions with welcoming approach",
                "preprocessing_features": [
                    "minimal_spelling_grammar_fixes",
                    "preserves_user_vocabulary",
                    "welcoming_tone_optimization"
                ],
                "response_features": [
                    "warm_greeting_introduction",
                    "engagement_oriented",
                    "clear_explanation_style",
                    "encourages_follow_up_questions"
                ],
                "parallel_processing": True,
                "source_options": ["rag"],
                "stp_integration": True
            },
            "continue_conversation": {
                "description": "Context-aware follow-up interactions with conversation flow",
                "preprocessing_features": [
                    "pronoun_resolution",
                    "context_aware_enhancement",
                    "conversation_flow_optimization",
                    "session_memory_integration"
                ],
                "response_features": [
                    "builds_on_previous_exchanges",
                    "context_aware_responses",
                    "progressive_conversation_depth",
                    "natural_conversation_flow"
                ],
                "parallel_processing": True,
                "source_options": ["rag"],
                "stp_integration": True
            }
        }
    )
    technical_capabilities: Dict[str, bool] = Field(
        default_factory=lambda: {
            "session_management": True,
            "memory_integration": True,
            "context_awareness": True,
            "conversation_flow_tracking": True,
            "specialized_llm_prompting": True,
            "multilingual_support": True,
            "difficulty_level_adaptation": True,
            "reranking_enabled": True,
            "graph_api_integration": True,
            "simplified_4_field_sources": True,
            "total_references_count": True,
            "parallel_llm_source_processing": True,
            "async_url_resolution": True,
            "concurrent_task_execution": True,
            "rag_source_tracking": True,
            "web_search_integration": False,
            "structured_stp_with_5_factors": True,
            "separate_stp_display_fields": True,
            "external_stp_service_integration": True
        }
    )
    supported_languages: List[str] = ["en", "it", "pt", "el"]
    supported_difficulty_levels: List[str] = ["low", "high"]
    source_fields: List[str] = ["title", "doc_name", "url", "similarity_score"]
    response_fields: List[str] = [
        "response", 
        "title", 
        "sources", 
        "total_references", 
        "social_tipping_point"
    ]
    stp_fields: List[str] = ["text", "qualifying_factors"]
    performance_features: List[str] = [
        "parallel_llm_parsing",
        "concurrent_url_generation", 
        "batch_source_processing",
        "30_50_percent_speedup",
        "graceful_error_handling",
        "rag_source_processing",
        "external_stp_parallel_processing",
        "structured_stp_parsing"
    ]
    
    # RAG-only source tracking
    source_tracking: Dict[str, Any] = Field(
        default_factory=lambda: {
            "supported_sources": ["rag"],
            "automatic_detection": True,
            "fallback_chain": ["rag"],
            "triggers": ["substantive_queries", "knowledge_base_queries"],
            "source_metadata_included": True
        }
    )
    
    # STP field structure and capabilities
    social_tipping_point_structure: Dict[str, Any] = Field(
        default_factory=lambda: {
            "service": "external_stp_api",
            "endpoint": "http://86.50.229.248:8000/api/v1/stp/search",
            "separate_fields": True,
            "structured_response": True,
            "fields": {
                "text": {
                    "type": "string",
                    "description": "Main tipping point description",
                    "display": "main_content_area"
                },
                "qualifying_factors": {
                    "type": "array",
                    "description": "List of 5 qualifying factor descriptions",
                    "count": 5,
                    "display": "sidebar_or_details_section",
                    "factors": [
                        "1. Environmental problems with perceived societal consequences",
                        "2. Shared awareness of the problem",
                        "3. Shared understanding of causes and effects",
                        "4. Expressed perception for a change regarding habits/lifestyle",
                        "5. Socio-political demand for explanations, solutions and actions"
                    ]
                }
            },
            "parsing": {
                "method": "regex_based_number_splitting",
                "input_format": "single_string_with_5_numbered_factors",
                "normalization": "whitespace_and_newline_normalization",
                "validation": "exactly_5_factors_expected"
            },
            "display_recommendations": {
                "text": "Display in main content area as primary STP description",
                "qualifying_factors": "Display as numbered list in sidebar or expandable section",
                "styling": "Use distinct visual treatment for factors (e.g., badges, cards, or list items)",
                "mobile": "Consider collapsible section for qualifying factors on mobile"
            },
            "fallback_messages": {
                "no_tipping_point": "No specific social tipping point available for this query.",
                "empty_qualifying_factors": [],
                "parsing_error": "Unable to parse qualifying factors from STP service."
            },
            "integration": {
                "parallel_processing": True,
                "timeout": "30 seconds",
                "error_handling": "graceful_degradation",
                "caching": False
            }
        }
    )
    
    # Example response structure for documentation
    example_response: Dict[str, Any] = Field(
        default_factory=lambda: {
            "session_id": "123e4567-e89b-12d3-a456-426614174000",
            "message_id": "123e4567-e89b-12d3-a456-426614174001",
            "response": "Based on the documents, sea level rise is a significant climate change impact...",
            "title": "Understanding Sea Level Rise",
            "social_tipping_point": {
                "text": "Coastal communities implementing comprehensive adaptation strategies once sea level rise exceeds 50cm threshold.",
                "qualifying_factors": [
                    "Environmental problems with perceived societal consequences: Strong, Rising sea levels directly threaten coastal infrastructure and communities.",
                    "Shared awareness of the problem: Strong, Scientific consensus and visible impacts increase public awareness.",
                    "Shared understanding of causes and effects: Moderate, Connection between emissions and sea level rise is increasingly understood.",
                    "Expressed perception for a change: Moderate, Coastal communities beginning to advocate for adaptation measures.",
                    "Socio-political demand for explanations: Strong, Governments facing pressure to implement coastal protection policies."
                ]
            },
            "sources": [
                {
                    "title": "IPCC Sea Level Report 2023",
                    "doc_name": "ipcc_sea_level_2023.pdf",
                    "url": "https://example.com/ipcc_sea_level_2023.pdf",
                    "similarity_score": 95.2
                }
            ],
            "total_references": 3
        }
    )