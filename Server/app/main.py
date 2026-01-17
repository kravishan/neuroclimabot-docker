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
from prometheus_client import start_http_server

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

# Global background task handles
cleanup_task = None


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
    global cleanup_task

    tasks = []
    
    # Initialize Langfuse service first (non-blocking)
    tasks.append(initialize_langfuse_service())
    
    # Initialize authentication service
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

    # Start metrics server
    if settings.ENABLE_METRICS:
        tasks.append(start_metrics_server())

    # Run all initialization tasks
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Log results
    task_names = ["langfuse", "auth", "milvus", "minio", "rag", "session_manager", "stats_database", "graphrag", "metrics"]
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            task_name = task_names[i] if i < len(task_names) else f"task_{i}"
            logger.warning(f"Service {task_name} initialization failed: {result}")
    
    # Start weekly cleanup task for auth tokens
    cleanup_task = asyncio.create_task(weekly_token_cleanup())


async def shutdown_event():
    """Application shutdown event with Langfuse cleanup and auth cleanup."""
    global cleanup_task

    logger.info("Shutting down services...")

    # Cancel cleanup tasks
    if cleanup_task and not cleanup_task.done():
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
    
    # Shutdown Langfuse service first to flush any pending traces
    try:
        from app.services.tracing.langfuse_service import get_langfuse_service
        langfuse_service = await get_langfuse_service()
        if langfuse_service:
            await langfuse_service.shutdown()
    except Exception as e:
        logger.warning(f"Error shutting down Langfuse service: {e}")
    
    # Close other connections
    if hasattr(milvus_client, 'close'):
        await milvus_client.close()

    if hasattr(session_manager, 'close'):
        await session_manager.close()

    if hasattr(stats_database, 'close'):
        await stats_database.close()


async def weekly_token_cleanup():
    """Background task to cleanup expired tokens weekly."""
    while True:
        try:
            # Wait 7 days (604800 seconds)
            await asyncio.sleep(7 * 24 * 60 * 60)

            # Cleanup expired tokens
            from app.services.auth.auth_service import get_auth_service
            auth_service = get_auth_service()
            deleted_count = await auth_service.cleanup_expired_tokens()
            logger.info(f"Weekly cleanup: removed {deleted_count} expired tokens")

        except asyncio.CancelledError:
            logger.info("Token cleanup task cancelled")
            break
        except Exception as e:
            logger.error(f"Error in weekly token cleanup: {e}")
            # Continue the loop even if cleanup fails


async def initialize_auth_service():
    """Initialize authentication service."""
    try:
        from app.services.auth.auth_service import get_auth_service
        auth_service = get_auth_service()
        logger.info("✅ Authentication service initialized")

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


async def start_metrics_server():
    """Start Prometheus metrics server."""
    try:
        start_http_server(settings.METRICS_PORT)
        logger.info(f"✅ Metrics server started on port {settings.METRICS_PORT}")
    except Exception as e:
        logger.warning(f"⚠️  Failed to start metrics server: {e}")


def create_application() -> FastAPI:
    """Create and configure FastAPI application."""
    
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Modern RAG system for climate policy Q&A with authentication, Langfuse tracing and Prometheus metrics",
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
    
    # Add metrics endpoint
    @app.get("/metrics", include_in_schema=False, tags=["Monitoring"])
    async def metrics():
        """Prometheus metrics endpoint."""
        from app.core.middleware import get_metrics_response
        return get_metrics_response()
    
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
            },
            "monitoring": {
                "prometheus_metrics": "/metrics",
                "health_check": "/health"
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
    # 1. Prometheus metrics (first to capture all requests)
    from app.core.middleware import PrometheusMiddleware
    app.add_middleware(PrometheusMiddleware)
    
    # 2. Timing middleware
    app.add_middleware(TimingMiddleware)
    
    # 3. Logging middleware
    app.add_middleware(LoggingMiddleware)
    
    # 4. Rate limiting middleware (last to apply limits)
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
    
    # Check Auth service
    try:
        from app.services.auth.auth_service import get_auth_service
        auth_service = get_auth_service()
        auth_stats = await auth_service.get_token_stats()
        services["auth"] = "healthy" if auth_stats["total"] >= 0 else "unhealthy"
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
            "database": "SQLite",
            "file": "auth_tokens.db"
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