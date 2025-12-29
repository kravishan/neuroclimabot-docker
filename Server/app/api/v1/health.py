"""Health check endpoints."""

from fastapi import APIRouter, Depends
from app.schemas.common import HealthCheck
from app.services.rag.chain import get_rag_service
from app.services.external.milvus import get_milvus_client
from app.services.external.minio import get_minio_client
from app.services.external.graphrag_api_client import graphrag_api_client
from app.services.memory.session import get_session_manager
from app.services.database.stats_database import get_stats_database

router = APIRouter()


@router.get("/", response_model=HealthCheck)
async def health_check():
    """Comprehensive health check for all bot services."""

    # Check all services
    rag_service = await get_rag_service()
    milvus_client = get_milvus_client()
    minio_client = get_minio_client()
    session_manager = get_session_manager()
    stats_db = await get_stats_database()

    services = {
        "rag": "healthy" if await rag_service.health_check() else "unhealthy",
        "milvus": "healthy" if await milvus_client.health_check() else "unhealthy",
        "minio": "healthy" if await minio_client.health_check() else "unhealthy",
        "redis": "healthy" if await session_manager.health_check() else "unhealthy",
        "database": "healthy" if await stats_db.health_check() else "unhealthy",
    }

    # Check auth service
    try:
        from app.services.auth.auth_service import get_auth_service
        auth_service = get_auth_service()
        auth_stats = await auth_service.get_token_stats()
        services["auth"] = "healthy" if auth_stats["total"] >= 0 else "unhealthy"
    except Exception:
        services["auth"] = "unhealthy"

    # Check Langfuse (optional)
    try:
        from app.services.tracing.langfuse_service import get_langfuse_service
        langfuse_service = await get_langfuse_service()
        if langfuse_service and langfuse_service.is_enabled:
            langfuse_health = await langfuse_service.health_check()
            services["langfuse"] = langfuse_health["status"]
        else:
            services["langfuse"] = "disabled"
    except Exception:
        services["langfuse"] = "disabled"

    # Check GraphRAG (optional)
    try:
        if graphrag_api_client.is_initialized:
            graphrag_healthy = await graphrag_api_client.health_check()
            services["graphrag"] = "healthy" if graphrag_healthy else "unhealthy"
        else:
            services["graphrag"] = "disabled"
    except Exception:
        services["graphrag"] = "disabled"

    # Determine overall status (only check required services)
    required_services = ["rag", "milvus", "minio", "redis", "database", "auth"]
    status = "healthy" if all(services[s] == "healthy" for s in required_services) else "degraded"

    return HealthCheck(
        status=status,
        version="0.1.0",
        services=services
    )