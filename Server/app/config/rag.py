"""
RAG (Retrieval-Augmented Generation) configuration.
Settings for retrieval, reranking, and response generation.
"""

from typing import List, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class RAGConfig(BaseSettings):
    """RAG pipeline configuration."""

    # Retrieval Configuration
    MAX_RETRIEVED_DOCS: int = 15
    INITIAL_RETRIEVAL_LIMIT: int = 25
    SIMILARITY_THRESHOLD: float = Field(
        default=0.6,
        description="Minimum similarity score for Milvus results"
    )

    # Individual service timeouts
    RETRIEVAL_MILVUS_TIMEOUT: float = Field(
        default=15.0,
        description="Timeout for Milvus retrieval operations"
    )
    RETRIEVAL_GRAPHRAG_API_TIMEOUT: float = Field(
        default=15.0,
        description="Timeout for GraphRAG local-search API calls"
    )
    RETRIEVAL_TOTAL_TIMEOUT: float = Field(
        default=25.0,
        description="Total timeout for all retrieval operations"
    )
    EMBEDDING_GENERATION_TIMEOUT: float = 10.0
    EMBEDDING_TIMEOUT: float = 10.0

    # Enhanced retrieval limits
    CHUNKS_RETRIEVAL_LIMIT: int = Field(
        default=20,
        description="Maximum number of chunks to retrieve from Milvus"
    )
    SUMMARIES_RETRIEVAL_LIMIT: int = Field(
        default=12,
        description="Maximum number of summaries to retrieve from Milvus"
    )

    # Reranking Configuration
    RERANKING_ENABLED: bool = True
    RERANKER_ENABLED: bool = True
    RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    RERANKING_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    RERANKING_FACTOR: int = 2
    RERANKING_TIMEOUT: int = 5
    RERANKER_BATCH_SIZE: int = 16
    RERANKER_MAX_LENGTH: int = 400
    RERANKER_MIN_SCORE: float = 0.75
    TOP_K_RERANK: int = Field(
        default=15,
        description="Number of top items to keep after reranking"
    )

    # Ultra-fast reranker settings
    ULTRA_FAST_RERANKER_ENABLED: bool = True
    RERANKER_WORD_OVERLAP_WEIGHT: float = 0.2
    RERANKER_PHRASE_MATCH_WEIGHT: float = 0.1
    RERANKER_SOURCE_BOOST_WEIGHT: float = 0.03

    # Enhanced Response Generation
    MAX_RESPONSE_LENGTH: int = Field(
        default=4000,
        description="Maximum response length in characters"
    )
    INCLUDE_SOURCES: bool = True
    MAX_SOURCES: int = 4
    MAX_REFERENCES: int = Field(
        default=8,
        description="Maximum number of references to include in response"
    )
    RESPONSE_LANGUAGE: str = "en"
    SUPPORTED_LANGUAGES: Union[str, List[str]] = Field(
        default=["en"],
        description="Supported languages for responses"
    )

    # Validator for SUPPORTED_LANGUAGES to handle comma-separated string from .env
    @field_validator("SUPPORTED_LANGUAGES", mode="before")
    @classmethod
    def parse_supported_languages(cls, v: Union[str, List[str]]) -> List[str]:
        """Parse SUPPORTED_LANGUAGES from comma-separated string or list."""
        # Handle None or empty string
        if v is None or v == "":
            return ["en"]
        # Handle string values
        if isinstance(v, str):
            # Parse comma-separated string from .env
            return [item.strip() for item in v.split(",") if item.strip()]
        # Handle list values
        elif isinstance(v, list):
            return v
        raise ValueError(f"Invalid SUPPORTED_LANGUAGES value: {v}")

    # Enhanced Context Configuration
    MAX_CONTEXT_CHUNKS: int = Field(
        default=8,
        description="Maximum chunks to include in LLM context"
    )
    MAX_CONTEXT_SUMMARIES: int = Field(
        default=4,
        description="Maximum summaries to include in LLM context"
    )
    MAX_CONTEXT_GRAPH_ITEMS: int = Field(
        default=6,
        description="Maximum graph items from local-search to include in LLM context"
    )
    MAX_CONTEXT_LENGTH: int = Field(
        default=8000,
        description="Maximum total context length in characters"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"