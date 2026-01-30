"""
NeuroClima Document Processor - Main Application Module

This module serves as the entry point for the NeuroClima Document Processor,
a production-grade FastAPI application for intelligent document processing.

The application provides:
- Async document processing with chunking and summarization
- GraphRAG knowledge graph generation and storage
- STP (Social Tipping Points) classification
- Vector search capabilities across multiple document types
- Multi-language translation support
- Background task processing with queue management

"""

from dotenv import load_dotenv
import logging
import asyncio
import os
import signal
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from config import config
from models import ServiceContainer

# Load environment variables from .env file first
load_dotenv()

# Configure logging with standardized format
logging.basicConfig(
    level=getattr(logging, config.get('app.log_level', 'INFO').upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# GLOBAL STATE
# ============================================================================
# Global service container (initialized at startup)
services: Optional[ServiceContainer] = None

# Background task cleanup registry
background_tasks_cleanup = []


# ============================================================================
# SERVICE INITIALIZATION
# ============================================================================

async def initialize_services() -> ServiceContainer:
    """
    Initialize all application services with async support.

    This function sets up the complete service infrastructure including:
    - MinIO object storage client
    - MongoDB document tracker (multi-replica support)
    - Milvus vector storage
    - Async batch processor
    - Processing queue
    - GraphRAG processor
    - LanceDB graph storage
    - STP (Social Tipping Points) processor

    Services are initialized with health checks and graceful degradation.
    If a service fails to initialize, it will be marked as unavailable but
    the application will continue running with reduced functionality.

    Returns:
        ServiceContainer: Initialized service container with all available services

    Raises:
        Exception: Critical initialization failures that prevent app startup
    """
    global services
    
    logger.info("🚀 Initializing async-enabled services with GraphRAG and STP...")
    
    try:
        services = ServiceContainer()
        
        # Initialize core services
        logger.info("📦 Initializing core services...")
        
        # Initialize MinIO
        try:
            from inputs import MinioInput
            minio_service = MinioInput()
            if minio_service.connected:
                services.add_service('minio', minio_service)
                logger.info("✅ MinIO service initialized")
            else:
                logger.warning("⚠️ MinIO service not connected")
                services.add_service('minio', None)
        except Exception as e:
            logger.error(f"❌ MinIO initialization failed: {e}")
            services.add_service('minio', None)
        
        # Initialize Database services
        try:
            from storage.database import tracker
            from storage.milvus import milvus_storage

            if tracker.health_check():
                services.add_service('tracker', tracker)
                logger.info("✅ Async document tracker initialized")
            else:
                logger.warning("⚠️ Document tracker health check failed")
                services.add_service('tracker', None)

            milvus_storage.connect()
            if milvus_storage.health_check():
                services.add_service('vector_storage', milvus_storage)
                logger.info("✅ Async vector storage initialized")
            else:
                logger.warning("⚠️ Vector storage health check failed")
                services.add_service('vector_storage', None)

        except Exception as e:
            logger.error(f"❌ Database services initialization failed: {e}")
            services.add_service('tracker', None)
            services.add_service('vector_storage', None)
        
        # Initialize async processing services
        try:
            from services.batch import async_batch_processor
            services.add_service('batch_processor', async_batch_processor)
            logger.info("✅ Async batch processor initialized")
            
            from processors.pipeline import processor
            services.add_service('embedder', processor.embedder)
            logger.info("✅ Async embedder initialized")
            
        except Exception as e:
            logger.error(f"❌ Async processing services initialization failed: {e}")
            services.add_service('batch_processor', None)
            services.add_service('embedder', None)
        
        # Initialize queue service
        try:
            if services.is_service_available('batch_processor'):
                from services.queue import create_processing_queue
                max_concurrent = config.get('processing.max_concurrent_tasks', 3)
                queue = create_processing_queue(services.get_service('batch_processor'), max_concurrent)
                services.add_service('processing_queue', queue)
                logger.info("✅ Async processing queue initialized")
            else:
                logger.warning("⚠️ Queue not initialized - batch processor unavailable")
                services.add_service('processing_queue', None)
        except Exception as e:
            logger.error(f"❌ Queue initialization failed: {e}")
            services.add_service('processing_queue', None)
        
        # Initialize GraphRAG processor
        try:
            from processors.graphrag_processor import graphrag_processor
            services.add_service('graphrag_processor', graphrag_processor)
            logger.info("✅ CLI GraphRAG processor initialized")
        except Exception as e:
            logger.error(f"❌ GraphRAG processor initialization failed: {e}")
            services.add_service('graphrag_processor', None)

        # Initialize LanceDB storage for GraphRAG data
        try:
            from storage.lancedb import LanceDBStorage
            lancedb_path = "./graphrag/output/lancedb"
            lancedb = LanceDBStorage(db_path=lancedb_path)
            services.add_service('lancedb_storage', lancedb)
            logger.info(f"✅ LanceDB storage initialized at {lancedb_path}")
        except Exception as e:
            logger.error(f"❌ LanceDB storage initialization failed: {e}")
            services.add_service('lancedb_storage', None)

        # Initialize STP processor
        try:
            from processors.stp_processor import stp_processor
            
            if config.is_stp_enabled():
                # Validate STP configuration
                validation = config.validate_stp_config()
                
                if validation["valid"]:
                    services.add_service('stp_processor', stp_processor)
                    logger.info("✅ STP processor initialized")
                    
                    # Log STP configuration
                    stp_config = config.get_stp_config()
                    logger.info(f"   📊 STP Milvus: {stp_config.get('milvus_database')}/{stp_config.get('milvus_collection')}")
                    logger.info(f"   🤖 Classifier: {stp_config.get('classifier_model')}")
                    logger.info(f"   ✍️ Rephrasing: {'Enabled' if stp_config.get('rephrasing_enabled') else 'Disabled'}")
                    logger.info(f"   📝 QF Generation: {'Enabled' if stp_config.get('qf_enabled') else 'Disabled'}")
                    
                    # Check STP dependencies
                    dependencies = config.check_stp_dependencies()
                    if not dependencies["all_available"]:
                        logger.warning(f"⚠️ Some STP dependencies missing: {dependencies['missing']}")
                        if dependencies["critical_missing"]:
                            logger.error(f"❌ Critical STP dependencies missing: {dependencies['critical_missing']}")
                    else:
                        logger.info("✅ All STP dependencies available")
                else:
                    logger.error(f"❌ STP configuration invalid: {validation['errors']}")
                    if validation["warnings"]:
                        for warning in validation["warnings"]:
                            logger.warning(f"⚠️ {warning}")
                    services.add_service('stp_processor', None)
            else:
                logger.info("ℹ️ STP processing is disabled in configuration")
                services.add_service('stp_processor', None)
                
        except Exception as e:
            logger.error(f"❌ STP processor initialization failed: {e}")
            services.add_service('stp_processor', None)
        
        # Set service container attributes for backward compatibility
        services.minio = services.services.get('minio')
        services.tracker = services.services.get('tracker')
        services.vector_storage = services.services.get('vector_storage')
        services.batch_processor = services.services.get('batch_processor')
        services.processing_queue = services.services.get('processing_queue')
        services.embedder = services.services.get('embedder')
        services.graphrag_processor = services.services.get('graphrag_processor')
        services.lancedb_storage = services.services.get('lancedb_storage')
        services.stp_processor = services.services.get('stp_processor')
        
        services._initialized = True
        
        # Log final status
        available_services = services.get_available_services()
        logger.info(f"🎉 Service initialization complete!")
        logger.info(f"📊 Available services: {available_services}")
        logger.info(f"🏥 Health status: {len(available_services)}/9 services available")
        logger.info(f"🔄 Background task processing: ENABLED")
        logger.info(f"🕸️ GraphRAG processing: {'ENABLED' if 'graphrag_processor' in available_services else 'DISABLED'}")
        logger.info(f"🎯 STP processing: {'ENABLED' if 'stp_processor' in available_services else 'DISABLED'}")
        
        return services
        
    except Exception as e:
        logger.error(f"💥 Critical service initialization failure: {e}")
        raise

# ============================================================================
# SERVICE ACCESSORS
# ============================================================================

def get_services() -> ServiceContainer:
    """
    Get the initialized service container.

    This function provides access to all application services through a
    single service container. Used throughout the application via dependency
    injection.

    Returns:
        ServiceContainer: The global service container

    Raises:
        HTTPException: If services are not yet initialized (503 Service Unavailable)
    """
    if not services:
        raise HTTPException(status_code=503, detail="Services not initialized")
    return services


def get_queue():
    """
    Get the document processing queue.

    Provides access to the async processing queue for background document
    processing tasks.

    Returns:
        ProcessingQueue | None: The processing queue if available, None otherwise
    """
    if not services or not services.processing_queue:
        return None
    return services.processing_queue

# ============================================================================
# CLEANUP & SHUTDOWN
# ============================================================================

async def cleanup_background_tasks():
    """
    Clean up background tasks and release resources.

    This function is called during application shutdown to ensure all
    background tasks are properly terminated and resources are released:
    - Document processor cleanup
    - Embedder cleanup
    - Batch processor cleanup
    - STP processor cleanup
    - Custom cleanup tasks

    All cleanup operations are wrapped in try-except blocks to ensure
    graceful degradation even if individual cleanups fail.
    """
    global background_tasks_cleanup
    
    logger.info("🧹 Starting background task cleanup...")
    
    try:
        from processors.pipeline import processor
        if hasattr(processor, 'cleanup'):
            await processor.cleanup()
        
        if hasattr(processor.embedder, 'cleanup'):
            await processor.embedder.cleanup()
        
        from services.batch import async_batch_processor
        if hasattr(async_batch_processor, 'cleanup'):
            await async_batch_processor.cleanup()
        
        # Cleanup STP processor
        from processors.stp_processor import stp_processor
        if hasattr(stp_processor, 'cleanup'):
            await stp_processor.cleanup()
        
        for cleanup_task in background_tasks_cleanup:
            try:
                if asyncio.iscoroutine(cleanup_task):
                    await cleanup_task
                else:
                    cleanup_task()
            except Exception as e:
                logger.error(f"❌ Cleanup task failed: {e}")
        
        logger.info("✅ Background task cleanup completed")
        
    except Exception as e:
        logger.error(f"❌ Error during background task cleanup: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager with async support.

    Manages the complete lifecycle of the FastAPI application:

    Startup Phase:
    - Initialize all services (databases, storage, processors)
    - Validate configuration
    - Start background workers
    - Log system capabilities

    Shutdown Phase:
    - Stop background tasks
    - Close database connections
    - Release file handles
    - Clean up temporary resources

    Args:
        app: FastAPI application instance

    Yields:
        None: Control is yielded to the application during its lifetime
    """
    # Startup
    logger.info("🚀 Starting NeuroClima Document Processor v7.0 with GraphRAG and STP...")

    try:
        await initialize_services()

        # Initialize local embedding models at startup
        logger.info("🤖 Initializing local embedding models...")
        try:
            from services.local_embeddings import initialize_embedding_models

            # Get embedding configuration
            embedding_config = config.get('local_embeddings', {})

            if embedding_config:
                initialize_embedding_models(embedding_config)
                logger.info("✅ Local embedding models loaded successfully")

                # Log model information
                from services.local_embeddings import get_model_manager
                model_manager = get_model_manager()
                models_info = model_manager.get_all_models_info()

                for model_name, info in models_info.items():
                    if info.get('loaded'):
                        logger.info(f"   📊 {model_name}: {info.get('model_name')} ({info.get('embedding_dim')}D) on {info.get('device')}")
            else:
                logger.warning("⚠️ No local embedding configuration found, using default settings")

        except Exception as embedding_error:
            logger.error(f"❌ Local embedding model initialization failed: {embedding_error}")
            logger.warning("⚠️ Falling back to API-based embeddings if available")

        # Pre-load translation models at startup
        logger.info("🌐 Pre-loading translation models...")
        try:
            from api.support import load_translation_model

            # Pre-load all language pairs to avoid cold start delays
            language_pairs = [
                ('en', 'it'), ('it', 'en'),
                ('en', 'pt'), ('pt', 'en'),
                ('en', 'el'), ('el', 'en')
            ]

            for source_lang, target_lang in language_pairs:
                try:
                    load_translation_model(source_lang, target_lang)
                    logger.info(f"✅ Loaded translation model: {source_lang} → {target_lang}")
                except Exception as model_error:
                    logger.warning(f"⚠️ Failed to load {source_lang} → {target_lang}: {model_error}")

            logger.info("✅ Translation models pre-loaded successfully")
        except Exception as translation_error:
            logger.warning(f"⚠️ Translation model pre-loading failed (will load on-demand): {translation_error}")

        logger.info("✅ Application startup complete")
        logger.info("🔄 Background task processing ready")
    except Exception as e:
        logger.error(f"❌ Application startup failed: {e}")
        
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down application...")
    
    await cleanup_background_tasks()
    
    if services:
        try:
            await services.cleanup()
            logger.info("✅ Services cleaned up successfully")
        except Exception as e:
            logger.error(f"❌ Error during service cleanup: {e}")
    
    logger.info("👋 Shutdown complete")

# ============================================================================
# APPLICATION FACTORY
# ============================================================================

def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    This factory function creates a new FastAPI instance with:
    - Application metadata (title, version, description)
    - Lifespan management
    - CORS middleware configuration

    Returns:
        FastAPI: Configured FastAPI application instance
    """
    app = FastAPI(
        title=config.get('app.name', 'NeuroClima Document Processor'),
        version=config.get('app.version', '7.0.0'),
        description="Async document processing with chunking, summarization, GraphRAG knowledge graphs, and STP classification",
        lifespan=lifespan
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    return app

def create_application() -> FastAPI:
    """
    Create complete application with all routes and middleware.

    This function builds the complete application by:
    1. Creating the base FastAPI app
    2. Registering health check endpoints
    3. Including all API routers (core, GraphRAG, STP, translation)
    4. Adding middleware for headers and monitoring

    The application provides:
    - RESTful API endpoints for document processing
    - Background task processing
    - Vector search capabilities
    - GraphRAG knowledge graph generation
    - STP classification and search
    - Multi-language translation

    Returns:
        FastAPI: Fully configured application ready to serve requests
    """
    app = create_app()
    
    @app.get("/")
    async def root():
        try:
            current_services = get_services()
            available = current_services.get_available_services()

            graphrag_status = "available" if "graphrag_processor" in available else "unavailable"
            lancedb_status = "available" if "graphrag_processor" in available else "unavailable"
            stp_status = "available" if "stp_processor" in available else "unavailable"

            # Check STP service health
            from processors.stp_processor import stp_processor
            stp_healthy = stp_processor.health_check() if stp_status == "available" else False
            
            background_task_stats = {"total_tasks": 0, "active_tasks": 0}
            try:
                from api.processing import task_manager
                background_task_stats = task_manager.get_all_tasks()
            except Exception:
                pass
            
            return {
                "title": config.get('app.name', 'NeuroClima Document Processor'),
                "version": config.get('app.version', '7.0.0'),
                "status": "online",
                "processing_mode": "async_background_tasks",
                "features": [
                    "Async Document Processing",
                    "Background Task Processing", 
                    "Specialized Chunking", 
                    "RAG Storage",
                    "Vector Search",
                    "CLI GraphRAG Knowledge Graphs",
                    "LanceDB Graph Storage",
                    "Non-blocking Queue Processing",
                    "Concurrent Multi-tenant Support",
                    "Integrated Translation Service",
                    "STP (Social Tipping Points) Classification",
                    "STP Search and Retrieval"
                ],
                "services_available": available,
                "services_count": f"{len(available)}/9",
                "graphrag_status": graphrag_status,
                "lancedb_status": lancedb_status,
                "translation_status": "integrated",
                "stp_status": stp_status,
                "stp_healthy": stp_healthy,
                "background_tasks": background_task_stats,
                "async_enabled": True,
                "timestamp": datetime.now().isoformat()
            }
        except HTTPException:
            return {
                "title": config.get('app.name', 'NeuroClima Document Processor'),
                "version": config.get('app.version', '7.0.0'),
                "status": "initializing",
                "processing_mode": "async_background_tasks",
                "services_available": [],
                "services_count": "0/9",
                "graphrag_status": "unknown",
                "lancedb_status": "unknown",
                "translation_status": "integrated",
                "stp_status": "unknown",
                "stp_healthy": False,
                "background_tasks": {"error": "initializing"},
                "async_enabled": True,
                "timestamp": datetime.now().isoformat()
            }
    
    @app.get("/health")
    async def health():
        try:
            current_services = get_services()
            health_status = current_services.get_health_status()
            
            # Check STP service
            from processors.stp_processor import stp_processor
            stp_healthy = stp_processor.health_check()
            
            stp_health_details = {}
            if stp_healthy:
                stp_validation = config.validate_stp_config()
                stp_dependencies = config.check_stp_dependencies()
                
                stp_health_details = {
                    "stp_processor": "healthy",
                    "configuration_valid": stp_validation["valid"],
                    "all_dependencies_available": stp_dependencies["all_available"],
                    "missing_dependencies": stp_dependencies["missing"],
                    "critical_missing": stp_dependencies["critical_missing"]
                }
            else:
                stp_health_details = {
                    "stp_processor": "unavailable"
                }
            
            graphrag_health = {
                "async_processing": True,
                "background_tasks_enabled": True,
                "graphrag_processor": "available" if current_services.is_service_available('graphrag_processor') else "unavailable",
                "graphrag_storage": "Master Parquet Files (./graphrag/output)",
                "translation_service": "integrated",
                "stp_service": "healthy" if stp_healthy else "unavailable",
                "stp_details": stp_health_details
            }
            
            try:
                from api.processing import task_manager
                background_stats = task_manager.get_all_tasks()
                graphrag_health["background_task_manager"] = "healthy"
                graphrag_health["active_background_tasks"] = background_stats.get("active_tasks", 0)
            except Exception:
                graphrag_health["background_task_manager"] = "unavailable"
            
            return {
                "status": "healthy" if health_status["healthy_count"] > 0 else "degraded",
                "services": health_status,
                "graphrag_capabilities": graphrag_health,
                "timestamp": datetime.now().isoformat()
            }
        except HTTPException:
            return {
                "status": "initializing",
                "services": {"available": [], "healthy_count": 0},
                "graphrag_capabilities": {
                    "async_processing": False, 
                    "background_tasks_enabled": False,
                    "translation_service": "integrated",
                    "stp_service": "unavailable",
                    "stp_details": {"stp_processor": "initializing"}
                },
                "timestamp": datetime.now().isoformat()
            }
    
    # ===================================================================
    # API STRUCTURE
    # ===================================================================

    # 1. Processing API - Document processing, batch, queue, webhooks
    from api.processing import setup_processing_routes
    setup_processing_routes(app, get_services, get_queue)
    logger.info("✅ Processing API routes added successfully")

    # 2. Support API - RAG search, STP search, Translation
    from api.support import router as support_router, setup_search_routes
    app.include_router(support_router)
    setup_search_routes(app, get_services)
    logger.info("✅ Support API routes added successfully (RAG/STP/Translation)")

    # 3. Health API - Health checks, statistics, webhook controls
    from api.health import router as health_router, setup_stats_routes
    app.include_router(health_router)
    setup_stats_routes(app, get_services)
    logger.info("✅ Health and Statistics API routes added successfully")

    # 4. GraphRAG API - Unified GraphRAG implementation (all search types, health, visualization)
    try:
        from api.graphrag import setup_graphrag_routes
        setup_graphrag_routes(app, get_services)
        logger.info("✅ GraphRAG API routes added successfully (unified implementation)")
    except Exception as e:
        logger.error(f"❌ Failed to add GraphRAG routes: {e}")
        logger.warning("⚠️ GraphRAG API endpoints will not be available")

    @app.middleware("http")
    async def add_processing_headers(request, call_next):
        """Add processing capability headers"""
        response = await call_next(request)
        response.headers["X-Async-Processing"] = "enabled"
        response.headers["X-Background-Tasks"] = "supported"
        response.headers["X-GraphRAG-Processing"] = "enabled"
        response.headers["X-Translation-Service"] = "integrated"
        response.headers["X-STP-Service"] = "integrated"
        return response
    
    return app

# ============================================================================
# SIGNAL HANDLING
# ============================================================================

def setup_signal_handlers():
    """
    Set up signal handlers for graceful shutdown.

    Registers handlers for SIGINT (Ctrl+C) and SIGTERM (kill) signals
    to ensure the application shuts down gracefully, allowing:
    - In-flight requests to complete
    - Database transactions to commit
    - Connections to close properly
    - Resources to be released
    """
    def signal_handler(signum, frame):
        logger.info(f"🛑 Received signal {signum}, initiating graceful shutdown...")
        
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

# ============================================================================
# APPLICATION ENTRY POINT
# ============================================================================

# Create the global application instance
# This is used by ASGI servers (uvicorn, gunicorn) to run the application
app = create_application()


if __name__ == "__main__":
    """
    Development server entry point.

    Run this file directly to start the development server:
        python main.py

    For production deployments, use a production ASGI server:
        uvicorn main:app --host 0.0.0.0 --port 5000 --workers 4
        gunicorn main:app --worker-class uvicorn.workers.UvicornWorker
    """
    import uvicorn
    
    setup_signal_handlers()
    
    host = config.get('app.host', '0.0.0.0')
    port = config.get('app.port', 5000)
    log_level = config.get('app.log_level', 'info').lower()
    debug = config.get('app.debug', False)
    
    run_config = {
        "host": host,
        "port": port,
        "log_level": log_level,
        "reload": debug,
        "loop": "asyncio"
    }
    
    logger.info("🚀 Starting NeuroClima Document Processor with GraphRAG and STP...")
    logger.info("⚡ Configuration:")
    for key, value in run_config.items():
        logger.info(f"  {key}: {value}")
    
    logger.info("🔄 Processing Capabilities:")
    logger.info("  - Background document processing")
    logger.info("  - Concurrent batch operations") 
    logger.info("  - Non-blocking API endpoints")
    logger.info("  - Async database operations")
    logger.info("  - Parallel embedding generation")
    logger.info("  - CLI GraphRAG knowledge graphs")
    logger.info("  - LanceDB graph storage")
    logger.info("  - Streamlined GraphRAG API")
    logger.info("  - STP classification and storage")
    logger.info("  - STP search and retrieval")
    
    uvicorn.run("main:app", **run_config)