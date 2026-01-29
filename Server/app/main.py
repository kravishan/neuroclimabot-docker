"""
NeuroClima RAG System - FastAPI Application with Authentication and Langfuse tracing integration.

"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.config import get_settings
from app.config.database import get_database_config, get_milvus_config, get_redis_config, get_minio_config
from app.core.exceptions import setup_exception_handlers
from app.core.middleware import (
    LoggingMiddleware,
    RateLimitMiddleware,
    TimingMiddleware,
)
# Import the corrected setup_logging function
from app.utils.logger import setup_logging, get_logger
from app.services.rag.chain import clean_rag_service
from app.services.external.milvus import milvus_client
from app.services.external.minio import minio_client
from app.services.external.graphrag_api_client import graphrag_api_client
from app.services.memory.session import session_manager
from app.services.database.stats_database import stats_database

# Initialize settings and database config
settings = get_settings()
db_config = get_database_config()

# Setup logging with the corrected function
logger = setup_logging(settings)

# Auth service reference for proper shutdown
_auth_service_instance = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager with Langfuse integration and auth cleanup."""
    logger.info("🚀 Starting NeuroClima RAG System")
    
    # Startup
    try:
        # Initialize services
        await startup_event()
        logger.info("✅ All services initialized successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ Failed to start application: {e}")
        raise
    finally:
        # Shutdown
        await shutdown_event()
        logger.info("🛑 NeuroClima RAG System stopped")


async def startup_event():
    """Application startup event with Langfuse, authentication, and parallel processing setup."""
    global _auth_service_instance

    tasks = []

    # Initialize Langfuse service first (non-blocking)
    tasks.append(initialize_langfuse_service())

    # Initialize authentication service (Redis-based with auto-expiration)
    tasks.append(initialize_auth_service())

    # Initialize vector database
    milvus_config = get_milvus_config()
    if milvus_config.HOST:
        tasks.append(initialize_milvus())

    # Initialize object storage
    minio_config = get_minio_config()
    if minio_config.ENDPOINT:
        tasks.append(initialize_minio())

    # Initialize RAG service
    tasks.append(initialize_rag_service())

    # Initialize session manager
    redis_config = get_redis_config()
    if redis_config.URL:
        tasks.append(initialize_session_manager())

    # Initialize stats database
    tasks.append(initialize_stats_database())

    # Initialize GraphRAG (optional)
    tasks.append(initialize_graphrag())

    # Run all initialization tasks
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Log results
    task_names = ["langfuse", "auth", "milvus", "minio", "rag", "session_manager", "stats_database", "graphrag"]
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            task_name = task_names[i] if i < len(task_names) else f"task_{i}"
            logger.warning(f"Service {task_name} initialization failed: {result}")


async def shutdown_event():
    """Application shutdown event with Langfuse cleanup and auth cleanup."""
    logger.info("Shutting down services...")

    # Shutdown Langfuse service first to flush any pending traces
    try:
        from app.services.tracing.langfuse_service import get_langfuse_service
        langfuse_service = await get_langfuse_service()
        if langfuse_service:
            await langfuse_service.shutdown()
    except Exception as e:
        logger.warning(f"Error shutting down Langfuse service: {e}")

    # Close auth service Redis connection
    try:
        from app.services.auth.auth_service import get_auth_service
        auth_service = get_auth_service()
        await auth_service.close()
    except Exception as e:
        logger.warning(f"Error shutting down auth service: {e}")

    # Close other connections
    if hasattr(milvus_client, 'close'):
        await milvus_client.close()

    if hasattr(session_manager, 'close'):
        await session_manager.close()

    if hasattr(stats_database, 'close'):
        await stats_database.close()


async def initialize_auth_service():
    """Initialize authentication service with Redis backend."""
    try:
        from app.services.auth.auth_service import initialize_auth_service as init_auth
        await init_auth()
        logger.info("✅ Authentication service initialized (Redis with auto-expiration)")

    except Exception as e:
        logger.error(f"❌ Failed to initialize authentication service: {e}")
        raise


async def initialize_langfuse_service():
    """Initialize Langfuse tracing service."""
    try:
        from app.services.tracing.langfuse_service import get_langfuse_service
        langfuse_service = await get_langfuse_service()
        
        if langfuse_service and langfuse_service.is_enabled:
            logger.info("✅ Langfuse tracing service initialized")
        else:
            logger.info("ℹ️  Langfuse tracing disabled or not configured")
            
    except Exception as e:
        logger.warning(f"⚠️  Langfuse initialization failed (non-critical): {e}")
        # Don't raise - Langfuse is optional for core functionality


async def initialize_milvus():
    """Initialize Milvus vector database."""
    try:
        await milvus_client.initialize()
        logger.info("✅ Milvus initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Milvus: {e}")
        raise


async def initialize_minio():
    """Initialize MinIO object storage."""
    try:
        await minio_client.initialize()
        logger.info("✅ MinIO initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize MinIO: {e}")
        raise


async def initialize_rag_service():
    """Initialize RAG service."""
    try:
        await clean_rag_service.initialize()
        logger.info("✅ RAG service initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize RAG service: {e}")
        raise


async def initialize_session_manager():
    """Initialize session manager."""
    try:
        await session_manager.initialize()
        logger.info("✅ Session manager initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize session manager: {e}")
        raise


async def initialize_stats_database():
    """Initialize stats database."""
    try:
        await stats_database.initialize()
        logger.info("✅ Stats database initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize stats database: {e}")
        raise


async def initialize_graphrag():
    """Initialize GraphRAG API client (optional)."""
    try:
        await graphrag_api_client.initialize()
        if graphrag_api_client.is_initialized:
            logger.info("✅ GraphRAG API client initialized")
        else:
            logger.info("ℹ️  GraphRAG API client not available (optional)")
    except Exception as e:
        logger.warning(f"⚠️  GraphRAG initialization failed (non-critical): {e}")
        # Don't raise - GraphRAG is optional


def create_application() -> FastAPI:
    """Create and configure FastAPI application."""
    
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Modern RAG system for climate policy Q&A with authentication and Langfuse tracing",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_url="/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan,
    )
    
    # Add middleware
    setup_middleware(app)
    
    # Setup exception handlers
    setup_exception_handlers(app)
    
    # Include routers
    app.include_router(api_router, prefix="/api/v1")

    # Add root endpoint
    @app.get("/", include_in_schema=False)
    async def root():
        """Root endpoint with clean API design information."""
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "status": "running",
            "docs": "/docs" if settings.DEBUG else None,
            "authentication": {
                "enabled": True,
                "type": "token_based_email"
            },
            "api_design": {
                "response_style": "clean_business_data_only",
                "performance_benefit": "faster_json_serialization"
            },
            "tracing": {
                "langfuse_enabled": settings.LANGFUSE_ENABLED,
                "langfuse_configured": settings.langfuse_is_configured
            }
        }
    

    return app


def setup_middleware(app: FastAPI):
    """Setup application middleware."""
    
    # CORS middleware
    if settings.ALLOWED_ORIGINS:
        # In development, allow all origins
        if settings.is_development:
            app.add_middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_credentials=False,
                allow_methods=["*"],
                allow_headers=["*"],
            )
        else:
            app.add_middleware(
                CORSMiddleware,
                allow_origins=settings.ALLOWED_ORIGINS,
                allow_credentials=settings.ALLOW_CREDENTIALS,
                allow_methods=settings.ALLOWED_METHODS,
                allow_headers=settings.ALLOWED_HEADERS,
            )
    
    # Compression middleware
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # Custom middleware (ORDER MATTERS!)
    # 1. Timing middleware
    app.add_middleware(TimingMiddleware)

    # 2. Logging middleware
    app.add_middleware(LoggingMiddleware)

    # 3. Rate limiting middleware (last to apply limits)
    if settings.RATE_LIMIT_ENABLED:
        app.add_middleware(
            RateLimitMiddleware,
            requests_per_minute=settings.RATE_LIMIT_REQUESTS,
        )


async def perform_health_check() -> Dict:
    """Perform comprehensive health check using database configuration."""
    status = "healthy"
    services = {}
    
    # Check Milvus
    try:
        milvus_status = await milvus_client.health_check()
        services["milvus"] = "healthy" if milvus_status else "unhealthy"
    except Exception:
        services["milvus"] = "unhealthy"
        status = "degraded"
    
    # Check MinIO
    try:
        minio_status = await minio_client.health_check()
        services["minio"] = "healthy" if minio_status else "unhealthy"
    except Exception:
        services["minio"] = "unhealthy"
        status = "degraded"
    
    # Check RAG service
    try:
        rag_status = await clean_rag_service.health_check()
        services["rag"] = "healthy" if rag_status else "unhealthy"
    except Exception:
        services["rag"] = "unhealthy"
        status = "degraded"
    
    # Check Redis (session manager)
    try:
        redis_status = await session_manager.health_check()
        services["redis"] = "healthy" if redis_status else "unhealthy"
    except Exception:
        services["redis"] = "unhealthy"
        status = "degraded"
    
    # Check Auth service (Redis-based)
    try:
        from app.services.auth.auth_service import get_auth_service
        auth_service = get_auth_service()
        auth_healthy = await auth_service.health_check()
        services["auth"] = "healthy" if auth_healthy else "unhealthy"
    except Exception:
        services["auth"] = "unhealthy"
        status = "degraded"
    
    # Check Langfuse (optional)
    try:
        from app.services.tracing.langfuse_service import get_langfuse_service
        langfuse_service = await get_langfuse_service()
        if langfuse_service:
            langfuse_health = await langfuse_service.health_check()
            services["langfuse"] = langfuse_health["status"]
        else:
            services["langfuse"] = "disabled"
    except Exception as e:
        services["langfuse"] = "error"
        logger.debug(f"Langfuse health check failed: {e}")
    
    # Add database configuration info
    db_info = {
        "milvus": {
            "host": get_milvus_config().HOST,
            "port": get_milvus_config().PORT,
            "databases": [get_milvus_config().DB_CHUNKS, get_milvus_config().DB_SUMMARIES]
        },
        "redis": {
            "url": get_redis_config().URL,
            "db": get_redis_config().DB
        },
        "minio": {
            "endpoint": get_minio_config().ENDPOINT,
            "secure": get_minio_config().SECURE
        },
        "auth": {
            "database": "Redis",
            "db": get_redis_config().AUTH_DB,
            "auto_expiration": True
        }
    }
    
    return {
        "status": status,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "services": services,
        "database_config": db_info,
        "authentication": {
            "enabled": True,
            "type": "token_based_email"
        },
        "tracing": {
            "langfuse_enabled": settings.LANGFUSE_ENABLED,
            "langfuse_configured": settings.langfuse_is_configured
        }
    }


# Create the FastAPI application
app = create_application()


if __name__ == "__main__":
    """Run the application."""
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        workers=settings.WORKERS if not settings.RELOAD else 1,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=settings.DEBUG,
    )