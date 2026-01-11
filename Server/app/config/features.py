"""
Feature flags and performance configuration.
Settings for enabling/disabling features and performance tuning.
"""

from pydantic import Field
from pydantic_settings import BaseSettings


class FeaturesConfig(BaseSettings):
    """Feature flags and performance settings."""

    # =============================================================================
    # Core Features
    # =============================================================================

    ENABLE_CHAT: bool = True
    ENABLE_DOCUMENT_UPLOAD: bool = True
    ENABLE_ADMIN_API: bool = True
    ENABLE_CONVERSATION_MEMORY: bool = True

    # =============================================================================
    # Performance Features
    # =============================================================================

    ENABLE_PARALLEL_RETRIEVAL: bool = True
    ENABLE_EARLY_STOPPING: bool = True

    # Performance Optimization Settings
    TARGET_RESPONSE_TIME_SECONDS: float = 20.0
    MAX_RESPONSE_TIME_SECONDS: float = 45.0
    MAX_CONCURRENT_REQUESTS: int = 10
    REQUEST_TIMEOUT_SECONDS: int = 30
    HTTP_CONNECTION_POOL_SIZE: int = 20
    HTTP_CONNECTION_TIMEOUT: int = 5
    HTTP_READ_TIMEOUT: int = 10

    # Enhanced Caching Configuration
    ENABLE_RESPONSE_CACHING: bool = True
    ENABLE_RESULT_CACHING: bool = True
    ENABLE_EMBEDDING_CACHING: bool = True
    CACHE_TTL_SECONDS: int = 300
    EMBEDDING_CACHE_SIZE: int = 1000
    QUERY_CACHE_SIZE: int = 500

    # Bucket-aware caching
    ENABLE_BUCKET_AWARE_CACHING: bool = Field(
        default=True,
        description="Enable bucket-aware caching for better cache utilization"
    )

    # =============================================================================
    # Advanced Features
    # =============================================================================

    ENABLE_MULTILINGUAL: bool = True
    ENABLE_VOICE_INPUT: bool = False
    ENABLE_ANALYTICS: bool = True
    ENABLE_FEEDBACK: bool = True

    # =============================================================================
    # Integration Features
    # =============================================================================

    ENABLE_GRAPH_INTEGRATION: bool = True
    ENABLE_GRAPHRAG_API: bool = Field(
        default=True,
        description="Enable GraphRAG local-search API integration"
    )
    ENABLE_RERANKING: bool = True

    # Bucket-related features
    ENABLE_BUCKET_FILTERING: bool = Field(
        default=False,
        description="Enable bucket filtering across the system"
    )
    ENABLE_BUCKET_AWARE_RESPONSES: bool = Field(
        default=True,
        description="Include bucket information in responses"
    )

    # =============================================================================
    # Experimental Features
    # =============================================================================

    # Disabled for speed
    ENABLE_QUERY_EXPANSION: bool = False
    ENABLE_AUTO_SUMMARIZATION: bool = False

    # =============================================================================
    # Monitoring & Observability
    # =============================================================================

    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 8001
    TRACK_RESPONSE_TIMES: bool = True
    PERFORMANCE_LOG_THRESHOLD: float = 2.0

    # GraphRAG API specific monitoring
    TRACK_GRAPHRAG_API_PERFORMANCE: bool = Field(
        default=True,
        description="Track GraphRAG API performance metrics"
    )
    TRACK_RELEVANCE_FILTERING: bool = Field(
        default=True,
        description="Track relevance filtering statistics"
    )
    TRACK_BUCKET_USAGE: bool = Field(
        default=True,
        description="Track bucket usage statistics"
    )
    TRACK_STP_PERFORMANCE: bool = Field(
        default=True,
        description="Track STP service performance metrics"
    )

    # =============================================================================
    # RAG Evaluation (TruLens)
    # =============================================================================

    TRULENS_ENABLED: bool = Field(
        default=False,
        description="Enable TruLens RAG evaluation (context relevance, groundedness, answer relevance)"
    )
    TRULENS_DB_PATH: str = Field(
        default="./data/trulens_evaluations.db",
        description="Path to TruLens SQLite database for storing evaluation results"
    )

    # TruLens OpenAI Configuration (Separate from main application)
    TRULENS_OPENAI_API_KEY: str = Field(
        default="",
        description="OpenAI API key specifically for TruLens evaluation (separate from main app)"
    )
    TRULENS_OPENAI_BASE_URL: str = Field(
        default="https://api.openai.com/v1",
        description="OpenAI API base URL for TruLens (use for Azure OpenAI or custom endpoints)"
    )
    TRULENS_OPENAI_MODEL: str = Field(
        default="gpt-4",
        description="OpenAI model for TruLens evaluation (gpt-4, gpt-4-turbo, gpt-3.5-turbo)"
    )
    TRULENS_OPENAI_ORGANIZATION: str = Field(
        default="",
        description="OpenAI organization ID for TruLens (optional)"
    )

    # Legacy setting (kept for backward compatibility)
    TRULENS_EVALUATION_MODEL: str = Field(
        default="gpt-4",
        description="DEPRECATED: Use TRULENS_OPENAI_MODEL instead. Fallback evaluation model."
    )

    TRULENS_GROUNDEDNESS_THRESHOLD: float = Field(
        default=0.7,
        description="Groundedness score threshold below which hallucination warnings are triggered"
    )

    # =============================================================================
    # Memory and Session Configuration
    # =============================================================================

    MEMORY_WINDOW_SIZE: int = 6
    MAX_CONVERSATION_HISTORY: int = 30
    SESSION_TIMEOUT_MINUTES: int = 30

    # Conversation Summary Settings
    ENABLE_CONVERSATION_SUMMARY: bool = True
    SUMMARY_MESSAGE_THRESHOLD: int = 10
    SUMMARY_MIN_MESSAGES: int = 8
    SUMMARY_MAX_LENGTH: int = 500
    SUMMARY_TIMEOUT: int = 15

    # =============================================================================
    # Connection Timeouts
    # =============================================================================

    EXTERNAL_SERVICE_CONNECT_TIMEOUT: float = 2.0
    EXTERNAL_SERVICE_READ_TIMEOUT: float = 5.0

    # =============================================================================
    # Computed Properties
    # =============================================================================

    @property
    def graphrag_api_is_enabled(self) -> bool:
        """Check if GraphRAG local-search API is enabled."""
        return self.ENABLE_GRAPHRAG_API

    @property
    def bucket_filtering_is_enabled(self) -> bool:
        """Check if bucket filtering is enabled across the system."""
        return self.ENABLE_BUCKET_FILTERING

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"
