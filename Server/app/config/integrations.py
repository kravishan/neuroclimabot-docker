"""
External integrations configuration.
Settings for Langfuse, GraphRAG, STP, MinIO, and other external services.
"""

from typing import Optional, List, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class IntegrationsConfig(BaseSettings):
    """External service integrations."""

    # =============================================================================
    # Langfuse Configuration
    # =============================================================================

    # Langfuse Authentication (from .env)
    LANGFUSE_SECRET_KEY: Optional[str] = None  # From .env
    LANGFUSE_PUBLIC_KEY: Optional[str] = None  # From .env
    LANGFUSE_HOST: Optional[str] = None  # From .env

    # Langfuse Settings
    LANGFUSE_ENABLED: bool = True
    LANGFUSE_DEBUG: bool = False
    LANGFUSE_FLUSH_AT: int = 15
    LANGFUSE_FLUSH_INTERVAL: int = 10
    LANGFUSE_SAMPLE_RATE: float = 1.0
    LANGFUSE_ENABLE_GENERATIONS: bool = True
    LANGFUSE_ENABLE_SCORES: bool = True

    # Advanced Langfuse Settings
    LANGFUSE_MAX_RETRIES: int = 3
    LANGFUSE_TIMEOUT: int = 20

    # Langfuse Feature Flags
    LANGFUSE_TRACE_RAG_PIPELINE: bool = True
    LANGFUSE_TRACE_LLM_CALLS: bool = True
    LANGFUSE_TRACE_RETRIEVAL: bool = True
    LANGFUSE_TRACE_RERANKING: bool = True
    LANGFUSE_TRACE_API_CALLS: bool = True
    LANGFUSE_TRACE_SESSIONS: bool = True

    # Langfuse Metadata
    LANGFUSE_RELEASE: Optional[str] = None
    LANGFUSE_USER_ID: str = "neuroclima-system"
    LANGFUSE_SESSION_ID_PREFIX: str = "nc"

    # =============================================================================
    # GraphRAG API Server Configuration
    # =============================================================================

    # GraphRAG API URL and timeout (from .env)
    GRAPHRAG_SERVER_URL: str  # From .env
    GRAPHRAG_API_TIMEOUT: float  # From .env

    # GraphRAG LLM Configuration (from .env)
    GRAPHRAG_LLM_API_BASE: Optional[str] = None  # OpenAI-compatible API base URL
    GRAPHRAG_LLM_API_KEY: Optional[str] = None  # API key for GraphRAG LLM
    GRAPHRAG_LLM_MODEL: str = "mistral.mistral-7b-instruct-v0:2"  # Model for GraphRAG queries

    # GraphRAG API Performance Settings
    GRAPHRAG_API_MAX_RETRIES: int = 3
    GRAPHRAG_API_RETRY_DELAY: float = 1.0
    GRAPHRAG_API_CONNECTION_TIMEOUT: float = 10.0
    GRAPHRAG_API_READ_TIMEOUT: float = 25.0

    # GraphRAG Local Search Configuration
    GRAPHRAG_LOCAL_SEARCH_MAX_ENTITIES: int = Field(
        default=20,
        description="Maximum entities to request from local-search endpoint"
    )
    GRAPHRAG_LOCAL_SEARCH_MAX_RELATIONSHIPS: int = Field(
        default=30,
        description="Maximum relationships to request from local-search endpoint"
    )
    GRAPHRAG_LOCAL_SEARCH_MAX_COMMUNITIES: int = Field(
        default=10,
        description="Maximum communities to request from local-search endpoint"
    )
    GRAPHRAG_LOCAL_SEARCH_CONTEXT_DEPTH: int = Field(
        default=1,
        description="Context depth for local-search expansion"
    )
    GRAPHRAG_LOCAL_SEARCH_MIN_RELEVANCE_SCORE: float = Field(
        default=0.6,
        description="Minimum relevance score for local-search results"
    )
    GRAPHRAG_LOCAL_SEARCH_INCLUDE_COMMUNITY_CONTEXT: bool = Field(
        default=True,
        description="Include community context in local-search"
    )
    GRAPHRAG_LOCAL_SEARCH_USE_LLM_EXTRACTION: bool = Field(
        default=True,
        description="Use LLM-based entity extraction in local-search"
    )

    # GraphRAG Visualization Configuration
    GRAPHRAG_VISUALIZATION_MAX_NODES: int = Field(
        default=200,
        description="Maximum nodes for visualization requests"
    )
    GRAPHRAG_VISUALIZATION_MAX_EDGES: int = Field(
        default=400,
        description="Maximum edges for visualization requests"
    )
    GRAPHRAG_VISUALIZATION_INCLUDE_SUMMARY: bool = Field(
        default=True,
        description="Include summary in visualization response"
    )

    # GraphRAG API Features
    GRAPHRAG_API_ENABLE_COMMUNITIES: bool = True
    GRAPHRAG_API_ENABLE_RELATIONSHIPS: bool = True
    GRAPHRAG_API_DEFAULT_SEARCH_TYPE: str = "local"

    # GraphRAG Relevance Scoring Configuration
    GRAPH_MIN_RELEVANCE_SCORE: float = Field(
        default=0.6,
        description="Minimum relevance score threshold for graph data (0.0-1.0)"
    )
    GRAPH_RETRIEVAL_LIMIT: int = Field(
        default=15,
        description="Maximum number of graph items to retrieve from GraphRAG API"
    )

    GRAPHRAG_LOCAL_SEARCH_MAX_RESULTS: int = Field(
        default=50,
        description="Maximum number of results for GraphRAG local search vector queries"
    )

    # Bucket Configuration
    GRAPHRAG_ENABLE_BUCKET_FILTERING: bool = Field(
        default=True,
        description="Enable bucket filtering for GraphRAG requests"
    )
    GRAPHRAG_DEFAULT_BUCKET: str = Field(
        default="researchpapers",
        description="Default bucket for GraphRAG requests when none specified"
    )
    GRAPHRAG_AVAILABLE_BUCKETS: Union[str, List[str]] = Field(
        default=["researchpapers", "news", "policies", "reports", "scientificdata"],
        description="List of available buckets for filtering"
    )

    # =============================================================================
    # MinIO Configuration
    # =============================================================================

    # MinIO Connection Settings (from .env - SECURITY: Never hardcode credentials!)
    MINIO_ENDPOINT: str  # From .env
    MINIO_ACCESS_KEY: str  # From .env
    MINIO_SECRET_KEY: str  # From .env
    MINIO_SECURE: bool  # From .env
    MINIO_REGION: str = "s-east-1"  # Default region
    MINIO_TIMEOUT: int = 10  # Default timeout

    # MinIO Bucket Configuration
    MINIO_BUCKET_NEWS: str = "news"
    MINIO_BUCKET_POLICY: str = "policies"
    MINIO_BUCKET_RESEARCH_PAPERS: str = "researchpapers"
    MINIO_BUCKET_SCIENTIFIC_DATA: str = "scientificdata"
    MINIO_BUCKET_REPORTS: str = "reports"
    MINIO_DEFAULT_BUCKET: str = "researchpapers"

    # Shareable URL Settings
    MINIO_PRESIGNED_URL_EXPIRY_MINUTES: int = 30
    MINIO_SHAREABLE_URL_EXPIRY_MINUTES: int = 30
    MINIO_ENABLE_PUBLIC_SHARING: bool = True
    MINIO_URL_TYPE: str = "shareable"  # "shareable" or "presigned"

    # MinIO Performance Settings
    MINIO_MAX_CONCURRENT_OPERATIONS: int = 8
    MINIO_PATH_CACHE_DURATION_HOURS: int = 1
    MINIO_ENABLE_PATH_CACHING: bool = True

    # =============================================================================
    # STP Service Configuration
    # =============================================================================

    # STP Service Connection
    STP_SERVICE_URL: str = Field(
        default="http://localhost:5000",
        description="Base URL for the external STP service"
    )
    STP_SERVICE_ENDPOINT: str = Field(
        default="/stp/search",
        description="STP search endpoint path"
    )

    # STP Service Settings
    STP_SERVICE_TIMEOUT: float = Field(
        default=30.0,
        description="Timeout for STP service calls in seconds"
    )
    STP_CONFIDENCE_THRESHOLD: float = Field(
        default=0.1,
        description="Minimum confidence score to include STP (0.0-1.0)"
    )
    STP_SIMILARITY_THRESHOLD: float = Field(
        default=0.3,
        description="Minimum similarity score to include STP (0.0-1.0)"
    )
    STP_TOP_K: int = Field(
        default=1,
        description="Number of top STP results to request"
    )
    STP_INCLUDE_METADATA: bool = Field(
        default=True,
        description="Include metadata (qualifying factors) in STP response"
    )

    # STP Feature Flags
    STP_SERVICE_ENABLED: bool = Field(
        default=True,
        description="Enable/disable STP service integration"
    )
    STP_PARALLEL_PROCESSING: bool = Field(
        default=True,
        description="Process STP requests in parallel with LLM"
    )
    STP_FALLBACK_MESSAGE: str = Field(
        default="No specific social tipping point available for this query.",
        description="Fallback message when STP confidence or similarity is below threshold"
    )

    # STP Performance Settings
    STP_MAX_RETRIES: int = Field(
        default=2,
        description="Maximum retry attempts for failed STP requests"
    )
    STP_RETRY_DELAY: float = Field(
        default=1.0,
        description="Delay between retry attempts in seconds"
    )
    STP_CACHE_ENABLED: bool = Field(
        default=False,
        description="Enable caching of STP responses"
    )

    # =============================================================================
    # Translation Service Configuration
    # =============================================================================

    # Translation Service Connection (from .env)
    TRANSLATION_SERVICE_URL: str = Field(
        default="http://localhost:5000",
        description="Base URL for the translation service"
    )

    # Translation Service Settings
    TRANSLATION_SERVICE_TIMEOUT: float = Field(
        default=60.0,
        description="Timeout for translation service calls in seconds"
    )
    TRANSLATION_DETECT_ENDPOINT: str = Field(
        default="/detect",
        description="Language detection endpoint path"
    )
    TRANSLATION_TRANSLATE_ENDPOINT: str = Field(
        default="/translate",
        description="Translation endpoint path"
    )
    TRANSLATION_BATCH_ENDPOINT: str = Field(
        default="/translate/batch",
        description="Batch translation endpoint path"
    )

    # Supported Languages
    TRANSLATION_SUPPORTED_LANGUAGES: Union[str, List[str]] = Field(
        default=["en", "it", "pt", "el"],
        description="List of supported translation languages"
    )
    TRANSLATION_DEFAULT_LANGUAGE: str = Field(
        default="en",
        description="Default/target language for translations"
    )

    # Translation Feature Flags
    TRANSLATION_SERVICE_ENABLED: bool = Field(
        default=True,
        description="Enable/disable translation service integration"
    )
    TRANSLATION_AUTO_DETECT: bool = Field(
        default=True,
        description="Automatically detect source language"
    )
    TRANSLATION_FALLBACK_TO_ORIGINAL: bool = Field(
        default=True,
        description="Return original text if translation fails"
    )

    # =============================================================================
    # Email Configuration (from .env)
    # =============================================================================

    EMAIL_PROVIDER: str  # From .env

    # Maileroo API Settings (from .env)
    MAILEROO_API_KEY: str  # From .env
    MAILEROO_FROM_EMAIL: str  # From .env
    MAILEROO_FROM_NAME: str  # From .env
    MAILEROO_API_URL: str = "https://smtp.maileroo.com/api/v2/emails"  # Default API URL

    # SMTP Fallback Settings
    SMTP_SERVER: str = "localhost"  # Default SMTP server
    SMTP_PORT: int = 587  # Default SMTP port
    SMTP_USERNAME: Optional[str] = None  # Optional from .env
    SMTP_PASSWORD: Optional[str] = None  # Optional from .env
    FROM_EMAIL: str = "noreply@neuroclima.com"  # Default from email

    # Email Settings (from .env)
    EMAIL_TIMEOUT_SECONDS: int  # From .env
    EMAIL_RETRY_ATTEMPTS: int  # From .env
    EMAIL_RETRY_DELAY_SECONDS: float  # From .env

    # =============================================================================
    # Validators
    # =============================================================================

    @field_validator("LANGFUSE_SAMPLE_RATE")
    @classmethod
    def validate_sample_rate(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("LANGFUSE_SAMPLE_RATE must be between 0.0 and 1.0")
        return v

    @field_validator("MINIO_SHAREABLE_URL_EXPIRY_MINUTES")
    @classmethod
    def validate_url_expiry(cls, v: int) -> int:
        if not 1 <= v <= 120:
            raise ValueError("MINIO_SHAREABLE_URL_EXPIRY_MINUTES must be between 1 and 120 minutes")
        return v

    @field_validator("GRAPHRAG_SERVER_URL", "STP_SERVICE_URL")
    @classmethod
    def validate_server_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("Server URL must start with http:// or https://")
        return v.rstrip("/")

    @field_validator("EMAIL_PROVIDER")
    @classmethod
    def validate_email_provider(cls, v: str) -> str:
        valid_providers = ["maileroo", "smtp"]
        if v.lower() not in valid_providers:
            raise ValueError(f"EMAIL_PROVIDER must be one of {valid_providers}")
        return v.lower()

    @field_validator("GRAPHRAG_AVAILABLE_BUCKETS", mode="before")
    @classmethod
    def parse_available_buckets(cls, v: Union[str, List[str]]) -> List[str]:
        # Handle None or empty string
        if v is None or v == "":
            return ["researchpapers", "news", "policies", "reports", "scientificdata"]
        # Handle string values
        if isinstance(v, str):
            return [bucket.strip().strip('"\'') for bucket in v.split(",") if bucket.strip()]
        # Handle list values
        elif isinstance(v, list):
            return v
        raise ValueError(f"Invalid GRAPHRAG_AVAILABLE_BUCKETS value: {v}")

    @field_validator("TRANSLATION_SUPPORTED_LANGUAGES", mode="before")
    @classmethod
    def parse_supported_languages(cls, v: Union[str, List[str]]) -> List[str]:
        # Handle None or empty string
        if v is None or v == "":
            return ["en", "it", "pt", "el"]
        # Handle string values
        if isinstance(v, str):
            return [lang.strip().strip('"\'') for lang in v.split(",") if lang.strip()]
        # Handle list values
        elif isinstance(v, list):
            return v
        raise ValueError(f"Invalid TRANSLATION_SUPPORTED_LANGUAGES value: {v}")

    # =============================================================================
    # Computed Properties
    # =============================================================================

    @property
    def langfuse_is_configured(self) -> bool:
        """Check if Langfuse is properly configured."""
        return bool(
            self.LANGFUSE_ENABLED and
            self.LANGFUSE_SECRET_KEY and
            self.LANGFUSE_PUBLIC_KEY and
            self.LANGFUSE_HOST
        )

    @property
    def minio_shareable_urls_enabled(self) -> bool:
        """Check if MinIO shareable URLs are enabled."""
        return self.MINIO_ENABLE_PUBLIC_SHARING and self.MINIO_URL_TYPE == "shareable"

    @property
    def maileroo_is_configured(self) -> bool:
        """Check if Maileroo is properly configured."""
        return bool(self.MAILEROO_API_KEY and self.MAILEROO_FROM_EMAIL)

    @property
    def smtp_auth_enabled(self) -> bool:
        """Check if SMTP authentication is configured."""
        return bool(self.SMTP_USERNAME and self.SMTP_PASSWORD)

    @property
    def email_is_configured(self) -> bool:
        """Check if any email provider is configured."""
        return self.maileroo_is_configured or self.smtp_auth_enabled

    @property
    def stp_service_is_configured(self) -> bool:
        """Check if STP service is properly configured."""
        return bool(
            self.STP_SERVICE_ENABLED and
            self.STP_SERVICE_URL and
            self.STP_SERVICE_ENDPOINT
        )

    @property
    def stp_full_url(self) -> str:
        """Get full STP service URL."""
        return f"{self.STP_SERVICE_URL.rstrip('/')}{self.STP_SERVICE_ENDPOINT}"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"
