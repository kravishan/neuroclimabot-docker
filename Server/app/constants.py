"""
Application-wide constants.
Centralizes magic numbers and configuration constants used throughout the codebase.
"""

# =============================================================================
# Trace & Logging Constants
# =============================================================================

MAX_TRACE_OUTPUT_LENGTH = 200  # Maximum characters to include in trace output
MAX_LOG_OUTPUT_LENGTH = 500    # Maximum characters to include in log messages


# =============================================================================
# Memory & Conversation Constants
# =============================================================================

DEFAULT_MEMORY_WINDOW_SIZE = 6         # Number of recent exchanges to keep in memory
MAX_CONVERSATION_HISTORY = 30          # Maximum messages to retain in conversation
SESSION_LIST_DEFAULT_LIMIT = 50        # Default number of sessions to return in list


# =============================================================================
# Time Constants (seconds)
# =============================================================================

WEEKLY_CLEANUP_INTERVAL = 7 * 24 * 60 * 60   # 7 days in seconds (604800)
HOURLY_CLEANUP_INTERVAL = 60 * 60             # 1 hour in seconds (3600)


# =============================================================================
# Authentication Constants
# =============================================================================

TOKEN_LENGTH = 6                    # Length of authentication tokens
AUTH_TOKEN_MIN = 100000             # Minimum 6-digit token value
AUTH_TOKEN_MAX = 999999             # Maximum 6-digit token value
DEFAULT_TOKEN_EXPIRY_DAYS = 7       # Default token validity period


# =============================================================================
# Summary Constants
# =============================================================================

SUMMARY_MESSAGE_THRESHOLD = 10      # Summarize conversation every N messages
SUMMARY_MIN_MESSAGES = 8            # Minimum messages before summarization
SUMMARY_MAX_LENGTH = 500            # Maximum summary length in words
SUMMARY_TIMEOUT = 15                # Maximum time for summary generation (seconds)


# =============================================================================
# Retrieval Constants
# =============================================================================

DEFAULT_CHUNKS_RETRIEVAL_LIMIT = 20     # Default number of chunks to retrieve
DEFAULT_SUMMARIES_RETRIEVAL_LIMIT = 12  # Default number of summaries to retrieve
DEFAULT_TOP_K_RERANK = 15               # Default number of items to keep after reranking


# =============================================================================
# Response Constants
# =============================================================================

MAX_RESPONSE_LENGTH = 4000          # Maximum response length in characters
MAX_SOURCES = 4                     # Maximum sources to include in response
MAX_REFERENCES = 8                  # Maximum references to include
DEFAULT_MAX_CONTEXT_CHUNKS = 8      # Default max chunks in LLM context
DEFAULT_MAX_CONTEXT_SUMMARIES = 4   # Default max summaries in LLM context
DEFAULT_MAX_CONTEXT_GRAPH_ITEMS = 6 # Default max graph items in LLM context
MAX_CONTEXT_LENGTH = 8000           # Maximum total context length in characters


# =============================================================================
# Performance Constants
# =============================================================================

DEFAULT_CACHE_TTL_SECONDS = 300         # 5 minutes default cache TTL
EMBEDDING_CACHE_SIZE = 1000             # Maximum embedding cache entries
QUERY_CACHE_SIZE = 500                  # Maximum query cache entries
TARGET_RESPONSE_TIME_SECONDS = 20.0     # Target response time
MAX_RESPONSE_TIME_SECONDS = 45.0        # Maximum acceptable response time


# =============================================================================
# Timeout Constants (seconds)
# =============================================================================

DEFAULT_REQUEST_TIMEOUT = 30            # Default API request timeout
MILVUS_SEARCH_TIMEOUT = 10               # Milvus search operation timeout
RETRIEVAL_MILVUS_TIMEOUT = 30.0         # Retrieval operation timeout
RETRIEVAL_GRAPHRAG_API_TIMEOUT = 25.0   # GraphRAG API timeout
RETRIEVAL_TOTAL_TIMEOUT = 30.0          # Total retrieval timeout
EMBEDDING_GENERATION_TIMEOUT = 10.0     # Embedding generation timeout
RERANKING_TIMEOUT = 10                   # Reranking operation timeout


# =============================================================================
# MinIO Constants
# =============================================================================

MINIO_PRESIGNED_URL_EXPIRY_MINUTES = 30     # Presigned URL validity period
MINIO_MAX_CONCURRENT_OPERATIONS = 8         # Max concurrent MinIO operations
MINIO_PATH_CACHE_DURATION_HOURS = 1         # Cache file paths for 1 hour


# =============================================================================
# Rate Limiting Constants
# =============================================================================

DEFAULT_RATE_LIMIT_REQUESTS = 100       # Default requests per window
RATE_LIMIT_WINDOW_SECONDS = 60          # Rate limit time window
CHAT_RATE_LIMIT = 20                    # Chat endpoint specific limit
UPLOAD_RATE_LIMIT = 5                   # Upload endpoint limit
ADMIN_RATE_LIMIT = 50                   # Admin endpoint limit


# =============================================================================
# Document Processing Constants
# =============================================================================

MAX_FILE_SIZE_MB = 50                   # Maximum upload file size
PROCESSING_TIMEOUT_SECONDS = 120        # Document processing timeout
PROCESSING_BATCH_SIZE = 5               # Batch size for document processing


# =============================================================================
# Vector Search Constants
# =============================================================================

DEFAULT_SIMILARITY_THRESHOLD = 0.1      # Minimum similarity score for results
DEFAULT_GRAPH_MIN_RELEVANCE_SCORE = 0.1 # Minimum relevance for graph data
EMBEDDING_DIMENSION = 1024              # Qwen3-Embedding-0.6B dimension
CHUNK_SIZE = 800                        # Text chunk size
CHUNK_OVERLAP = 150                     # Overlap between chunks
NLIST = 512                             # Milvus index parameter


# =============================================================================
# LLM Constants
# =============================================================================

DEFAULT_OLLAMA_TEMPERATURE = 0.2        # Ollama temperature setting
DEFAULT_OLLAMA_MAX_TOKENS = 1500        # Ollama max tokens
DEFAULT_OPENAI_TEMPERATURE = 0.2        # OpenAI temperature setting
DEFAULT_OPENAI_MAX_TOKENS = 1500        # OpenAI max tokens


# =============================================================================
# GraphRAG Constants
# =============================================================================

GRAPHRAG_LOCAL_SEARCH_MAX_ENTITIES = 20         # Max entities from local-search
GRAPHRAG_LOCAL_SEARCH_MAX_RELATIONSHIPS = 30    # Max relationships from local-search
GRAPHRAG_LOCAL_SEARCH_MAX_COMMUNITIES = 10      # Max communities from local-search
GRAPHRAG_LOCAL_SEARCH_CONTEXT_DEPTH = 1         # Context depth for expansion
GRAPHRAG_VISUALIZATION_MAX_NODES = 200          # Max nodes for visualization
GRAPHRAG_VISUALIZATION_MAX_EDGES = 400          # Max edges for visualization
GRAPH_RETRIEVAL_LIMIT = 15                      # Max graph items to retrieve


# =============================================================================
# STP Service Constants
# =============================================================================

STP_CONFIDENCE_THRESHOLD = 0.1          # Minimum STP confidence score
STP_SIMILARITY_THRESHOLD = 0.3          # Minimum STP similarity score
STP_TOP_K = 1                           # Number of top STP results
STP_MAX_RETRIES = 2                     # Maximum retry attempts
STP_RETRY_DELAY_SECONDS = 1.0           # Delay between retries
STP_SERVICE_TIMEOUT_SECONDS = 30.0      # STP service timeout
STP_EXPECTED_QUALIFYING_FACTORS = 5     # Expected number of qualifying factors in response


# =============================================================================
# Langfuse Constants
# =============================================================================

LANGFUSE_FLUSH_AT = 15                  # Flush after N traces
LANGFUSE_FLUSH_INTERVAL = 10            # Flush interval in seconds
LANGFUSE_SAMPLE_RATE = 1.0              # Sample rate (1.0 = 100%)
LANGFUSE_MAX_RETRIES = 3                # Maximum retry attempts
LANGFUSE_TIMEOUT_SECONDS = 20           # Langfuse API timeout


# =============================================================================
# HTTP Connection Constants
# =============================================================================

HTTP_CONNECTION_POOL_SIZE = 20          # Connection pool size
HTTP_CONNECTION_TIMEOUT = 5             # Connection establishment timeout
HTTP_READ_TIMEOUT = 10                  # Read timeout
MAX_CONCURRENT_REQUESTS = 10            # Max concurrent HTTP requests


# =============================================================================
# Email Constants
# =============================================================================

EMAIL_TIMEOUT_SECONDS = 30              # Email API timeout
EMAIL_RETRY_ATTEMPTS = 3                # Email retry attempts
EMAIL_RETRY_DELAY_SECONDS = 1.0         # Delay between email retries


# =============================================================================
# Reranking Constants
# =============================================================================

RERANKER_BATCH_SIZE = 16                # Batch size for reranking
RERANKER_MAX_LENGTH = 400               # Max text length for reranker
RERANKER_MIN_SCORE = 0.75               # Minimum reranker score
RERANKER_WORD_OVERLAP_WEIGHT = 0.2      # Word overlap weight
RERANKER_PHRASE_MATCH_WEIGHT = 0.1      # Phrase match weight
RERANKER_SOURCE_BOOST_WEIGHT = 0.03     # Source boost weight

# Boost values for reranking (from reranker.py)
TITLE_EXACT_MATCH_BOOST = 0.15          # Boost for exact title match
TITLE_PARTIAL_MATCH_BOOST = 0.10        # Boost for partial title match
SOURCE_EXACT_MATCH_BOOST = 0.05         # Boost for exact source match
QUERY_TERM_MATCH_BOOST = 0.02           # Boost for query term in content
COLLECTION_PRIORITY_BOOST = 0.03        # Boost for priority collections


# =============================================================================
# Translation Service Constants
# =============================================================================

# Supported Languages
SUPPORTED_TRANSLATION_LANGUAGES = ["en", "it", "pt", "el"]
DEFAULT_LANGUAGE = "en"

# Translation Endpoints
TRANSLATION_DETECT_ENDPOINT = "/detect"
TRANSLATION_TRANSLATE_ENDPOINT = "/translate"
TRANSLATION_BATCH_ENDPOINT = "/translate/batch"


# =============================================================================
# Content Limits (for response generation)
# =============================================================================

CONTENT_LIMIT_CHUNK = 400              # Max chars per chunk in response
CONTENT_LIMIT_SUMMARY = 300            # Max chars per summary in response
CONTENT_LIMIT_GRAPH = 200              # Max chars per graph item in response
CHUNK_CONTENT_PREVIEW_LENGTH = 500     # Chars for chunk content preview


# =============================================================================
# MinIO Bucket Mapping
# =============================================================================

# Bucket name mapping (lowercase keys for consistency)
BUCKET_NAME_MAPPING = {
    "news": "news",
    "policy": "policy",
    "research_papers": "researchpapers",
    "researchpapers": "researchpapers",
    "scientific_data": "scientificdata",
    "scientificdata": "scientificdata"
}
