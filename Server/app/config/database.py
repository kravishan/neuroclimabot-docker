"""
Updated database configuration without web search functionality
"""

from typing import Any, Dict, List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class MilvusConfig(BaseSettings):
    """Milvus vector database configuration for new structure."""

    # Connection Settings (from .env - SECURITY: Never hardcode credentials!)
    HOST: str  # From .env (MILVUS_HOST)
    PORT: int  # From .env (MILVUS_PORT)
    USER: str  # From .env (MILVUS_USER)
    PASSWORD: str  # From .env (MILVUS_PASSWORD)
    TIMEOUT: int = 10
    SEARCH_TIMEOUT: int = 5
    
    # Database Configuration
    DB_CHUNKS: str = "mvp_chunks"
    DB_SUMMARIES: str = "mvp_summaries"
    
    # Collection Configuration (4 collections in each database)
    COLLECTION_NEWS: str = "News"
    COLLECTION_POLICY: str = "Policy"
    COLLECTION_RESEARCH_PAPERS: str = "Research_Papers"
    COLLECTION_SCIENTIFIC_DATA: str = "Scientific_Data"
    
    # Vector Settings
    EMBEDDING_MODEL: str = "nomic-ai/nomic-embed-text-v1"
    EMBEDDING_DIMENSION: int = 768  # nomic-embed-text produces 768D embeddings
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 150
    
    # Search Parameters for COSINE metric
    METRIC_TYPE: str = "COSINE"
    NLIST: int = 512  # Index parameter from your setup
    
    @property
    def uri(self) -> str:
        """Get Milvus connection URI."""
        return f"http://{self.USER}:{self.PASSWORD}@{self.HOST}:{self.PORT}"
    
    @property
    def connection_args(self) -> Dict[str, Any]:
        """Get connection arguments for Milvus client."""
        return {
            "host": self.HOST,
            "port": self.PORT,
            "user": self.USER,
            "password": self.PASSWORD,
            "timeout": self.TIMEOUT
        }
    
    @property
    def chunks_collections(self) -> List[str]:
        """Get all chunk collections."""
        return [
            self.COLLECTION_NEWS,
            self.COLLECTION_POLICY,
            self.COLLECTION_RESEARCH_PAPERS,
            self.COLLECTION_SCIENTIFIC_DATA
        ]
    
    @property
    def summaries_collections(self) -> List[str]:
        """Get all summary collections."""
        return [
            self.COLLECTION_NEWS,
            self.COLLECTION_POLICY,
            self.COLLECTION_RESEARCH_PAPERS,
            self.COLLECTION_SCIENTIFIC_DATA
        ]
    
    def get_chunks_field_map(self, collection_name: str) -> Dict[str, str]:
        """Get field mapping for chunks based on collection."""
        if collection_name == self.COLLECTION_NEWS:
            return {
                "doc_name_field": "source_url",  # News uses source_url instead of doc_name
                "content_field": "chunk_text",
                "embedding_field": "embedding",
                "bucket_field": "bucket_source"
            }
        else:
            return {
                "doc_name_field": "doc_name",
                "content_field": "chunk_text", 
                "embedding_field": "embedding",
                "bucket_field": "bucket_source"
            }
    
    def get_summaries_field_map(self, collection_name: str) -> Dict[str, str]:
        """Get field mapping for summaries based on collection."""
        if collection_name == self.COLLECTION_NEWS:
            return {
                "doc_name_field": "source_url",  # News uses source_url instead of doc_name
                "content_field": "abstractive_summary",
                "embedding_field": "embedding",
                "bucket_field": "bucket_source"
            }
        else:
            return {
                "doc_name_field": "doc_name",
                "content_field": "abstractive_summary",
                "embedding_field": "embedding", 
                "bucket_field": "bucket_source"
            }
    
    class Config:
        env_file = ".env"
        env_prefix = "MILVUS_"
        extra = "ignore"


class RedisConfig(BaseSettings):
    """Redis configuration for session management and caching."""

    # Connection Settings (from .env - SECURITY: Never hardcode credentials!)
    URL: str  # From .env (REDIS_URL)
    PASSWORD: Optional[str] = None  # Optional from .env (REDIS_PASSWORD)
    DB: int = 0
    MAX_CONNECTIONS: int = 20
    CONNECTION_TIMEOUT: int = 10
    SOCKET_TIMEOUT: int = 10
    
    # Session Configuration (from .env)
    SESSION_TIMEOUT_MINUTES: int = Field(default=10)  # From .env (REDIS_SESSION_TIMEOUT_MINUTES)
    SESSION_WARNING_MINUTES: int = Field(default=1)  # From .env (REDIS_SESSION_WARNING_MINUTES) - Warning appears when remaining time ≤ this value
    MAX_CONVERSATION_HISTORY: int = 30
    MEMORY_WINDOW_SIZE: int = 6
    
    # Cache Configuration
    CACHE_TTL_SECONDS: int = 300
    EMBEDDING_CACHE_SIZE: int = 1000
    QUERY_CACHE_SIZE: int = 500
    
    @property
    def connection_kwargs(self) -> Dict[str, Any]:
        """Get connection kwargs for Redis client."""
        kwargs = {
            "url": self.URL,
            "db": self.DB,
            "max_connections": self.MAX_CONNECTIONS,
            "socket_timeout": self.SOCKET_TIMEOUT,
            "socket_connect_timeout": self.CONNECTION_TIMEOUT,
            "decode_responses": True,
            "encoding": "utf-8"
        }
        
        if self.PASSWORD:
            kwargs["password"] = self.PASSWORD
            
        return kwargs
    
    class Config:
        env_file = ".env"
        env_prefix = "REDIS_"
        extra = "ignore"

class AnalyticsConfig(BaseSettings):
    """TimescaleDB configuration for analytics"""
    
    # TimescaleDB connection
    TIMESCALE_HOST: str = "localhost"
    TIMESCALE_PORT: int = 5432
    TIMESCALE_DATABASE: str = "neuroclima_analytics"
    TIMESCALE_USER: str = "postgres"
    TIMESCALE_PASSWORD: str = "password"
    
    # Redis analytics configuration
    REDIS_ANALYTICS_DB: int = 2  # Separate Redis DB for analytics
    ANALYTICS_RETENTION_DAYS: int = 90
    
    # Batch processing
    BATCH_SIZE: int = 1000
    BATCH_INTERVAL_MINUTES: int = 5
    
    @property
    def timescale_url(self) -> str:
        return f"postgresql+asyncpg://{self.TIMESCALE_USER}:{self.TIMESCALE_PASSWORD}@{self.TIMESCALE_HOST}:{self.TIMESCALE_PORT}/{self.TIMESCALE_DATABASE}"
    
    class Config:
        env_file = ".env"
        extra = "ignore"     


class MinIOConfig(BaseSettings):
    """MinIO object storage configuration."""

    # Connection Settings (from .env - SECURITY: Never hardcode credentials!)
    ENDPOINT: str  # From .env (MINIO_ENDPOINT)
    ACCESS_KEY: str  # From .env (MINIO_ACCESS_KEY)
    SECRET_KEY: str  # From .env (MINIO_SECRET_KEY)
    SECURE: bool = False  # From .env (MINIO_SECURE)
    REGION: str = "us-east-1"
    TIMEOUT: int = 10
    
    # Bucket Configuration
    BUCKET_NAME: str = "pby-mvp-data"
    BUCKET_DOCUMENTS: str = "pby-mvp-data"
    BUCKET_TEMP: str = "pby-mvp-data"

    MINIO_PRESIGNED_URL_EXPIRY_MINUTES: int = 30
    
    @property
    def url(self) -> str:
        """Get MinIO URL."""
        protocol = "https" if self.SECURE else "http"
        return f"{protocol}://{self.ENDPOINT}"
    
    @property
    def connection_kwargs(self) -> Dict[str, Any]:
        """Get connection kwargs for MinIO client."""
        return {
            "endpoint": self.ENDPOINT,
            "access_key": self.ACCESS_KEY,
            "secret_key": self.SECRET_KEY,
            "secure": self.SECURE,
            "region": self.REGION
        }
    
    class Config:
        env_file = ".env"
        env_prefix = "MINIO_"
        extra = "ignore"


class DatabaseConfig:
    """Centralized database configuration container."""
    
    def __init__(self):
        self.milvus = MilvusConfig()
        self.redis = RedisConfig()
        self.minio = MinIOConfig()
    
    def get_all_configs(self) -> Dict[str, Any]:
        """Get all database configurations."""
        return {
            "milvus": {
                "host": self.milvus.HOST,
                "port": self.milvus.PORT,
                "chunks_database": self.milvus.DB_CHUNKS,
                "summaries_database": self.milvus.DB_SUMMARIES,
                "collections": {
                    "news": self.milvus.COLLECTION_NEWS,
                    "policy": self.milvus.COLLECTION_POLICY,
                    "research_papers": self.milvus.COLLECTION_RESEARCH_PAPERS,
                    "scientific_data": self.milvus.COLLECTION_SCIENTIFIC_DATA
                }
            },
            "redis": {
                "url": self.redis.URL,
                "db": self.redis.DB
            },
            "minio": {
                "endpoint": self.minio.ENDPOINT,
                "buckets": {
                    "main": self.minio.BUCKET_NAME,
                    "documents": self.minio.BUCKET_DOCUMENTS,
                    "temp": self.minio.BUCKET_TEMP
                }
            }
        }
    
    def health_check_info(self) -> Dict[str, str]:
        """Get health check information for all databases."""
        return {
            "milvus": self.milvus.uri,
            "redis": self.redis.URL,
            "minio": self.minio.url
        }


# Global database configuration instance
db_config = DatabaseConfig()


# Convenience functions for getting specific configurations
def get_database_config() -> DatabaseConfig:
    """Get the complete database configuration."""
    return db_config


def get_milvus_config() -> MilvusConfig:
    """Get Milvus configuration."""
    return db_config.milvus


def get_redis_config() -> RedisConfig:
    """Get Redis configuration."""
    return db_config.redis


def get_minio_config() -> MinIOConfig:
    """Get MinIO configuration."""
    return db_config.minio


# Backward compatibility helpers
def get_milvus_connection_args() -> Dict[str, Any]:
    """Get Milvus connection arguments (backward compatibility)."""
    return db_config.milvus.connection_args


def get_redis_connection_kwargs() -> Dict[str, Any]:
    """Get Redis connection kwargs (backward compatibility)."""
    return db_config.redis.connection_kwargs


def get_minio_connection_kwargs() -> Dict[str, Any]:
    """Get MinIO connection kwargs (backward compatibility)."""
    return db_config.minio.connection_kwargs