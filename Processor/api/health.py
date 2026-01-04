"""
Health and Status API

Provides:
- Service health monitoring
- Processing statistics and tracking
- Webhook configuration (enable/disable)
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional
from datetime import datetime
import logging

from api.framework import APIResponse, api_response
from config import config

logger = logging.getLogger(__name__)

# Global webhook state
webhook_enabled = True

# Create router
router = APIRouter(tags=["health", "webhook"])


def get_simple_health_status(services) -> Dict[str, str]:
    """
    Get simplified health status for all services.
    Returns only service name and health state (healthy/unhealthy).
    """
    health = {}

    # Define all services to check
    service_names = [
        'minio',
        'vector_storage',
        'tracker',
        'embedder',
        'batch_processor',
        'processing_queue',
        'graphrag_processor',
        'lancedb_storage',
        'stp_processor'
    ]

    for service_name in service_names:
        service = services.services.get(service_name)

        if service is None:
            health[service_name] = "unhealthy"
        else:
            try:
                # Check if service has health_check method
                if hasattr(service, 'health_check'):
                    is_healthy = service.health_check()
                    health[service_name] = "healthy" if is_healthy else "unhealthy"
                elif hasattr(service, 'connected'):
                    # For services like MinIO that use 'connected' attribute
                    health[service_name] = "healthy" if service.connected else "unhealthy"
                else:
                    # If no health check method, consider it healthy if it exists
                    health[service_name] = "healthy"
            except Exception as e:
                logger.error(f"Health check failed for {service_name}: {e}")
                health[service_name] = "unhealthy"

    return health


@router.get("/services/health")
async def get_services_health():
    """
    Get simple health status of all services.

    Returns:
        {
            "services": {
                "minio": "healthy",
                "milvus": "healthy",
                "tracker": "healthy",
                ...
            },
            "timestamp": "2025-11-16T..."
        }
    """
    try:
        from main import get_services
        services = get_services()

        # Get simple health status
        service_health = get_simple_health_status(services)

        # Map internal names to user-friendly names
        friendly_names = {
            'minio': 'minio',
            'vector_storage': 'milvus',
            'tracker': 'tracker',
            'embedder': 'embedder',
            'batch_processor': 'batch_processor',
            'processing_queue': 'processing_queue',
            'graphrag_processor': 'graphrag_processor',
            'lancedb_storage': 'lancedb_storage',
            'stp_processor': 'stp_processor'
        }

        # Convert to friendly names
        friendly_health = {
            friendly_names.get(k, k): v
            for k, v in service_health.items()
        }

        return {
            "services": friendly_health,
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException as e:
        raise HTTPException(status_code=503, detail="Services not initialized")
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@router.get("/webhook/status")
async def get_webhook_status():
    """
    Get current webhook configuration status.

    Returns:
        {
            "enabled": true,
            "timestamp": "2025-11-16T..."
        }
    """
    global webhook_enabled

    return {
        "enabled": webhook_enabled,
        "timestamp": datetime.now().isoformat()
    }


@router.post("/webhook/enable")
async def enable_webhook():
    """
    Enable webhook processing.

    Returns:
        {
            "enabled": true,
            "message": "Webhook enabled successfully",
            "timestamp": "2025-11-16T..."
        }
    """
    global webhook_enabled

    webhook_enabled = True
    logger.info("✅ Webhook processing enabled")

    return {
        "enabled": webhook_enabled,
        "message": "Webhook enabled successfully",
        "timestamp": datetime.now().isoformat()
    }


@router.post("/webhook/disable")
async def disable_webhook():
    """
    Disable webhook processing.

    Returns:
        {
            "enabled": false,
            "message": "Webhook disabled successfully",
            "timestamp": "2025-11-16T..."
        }
    """
    global webhook_enabled

    webhook_enabled = False
    logger.info("⚠️ Webhook processing disabled")

    return {
        "enabled": webhook_enabled,
        "message": "Webhook disabled successfully",
        "timestamp": datetime.now().isoformat()
    }


@router.post("/webhook/toggle")
async def toggle_webhook():
    """
    Toggle webhook processing on/off.

    Returns:
        {
            "enabled": true/false,
            "message": "Webhook toggled to: enabled/disabled",
            "timestamp": "2025-11-16T..."
        }
    """
    global webhook_enabled

    webhook_enabled = not webhook_enabled
    status = "enabled" if webhook_enabled else "disabled"
    logger.info(f"🔄 Webhook processing toggled to: {status}")

    return {
        "enabled": webhook_enabled,
        "message": f"Webhook toggled to: {status}",
        "timestamp": datetime.now().isoformat()
    }


def is_webhook_enabled() -> bool:
    """
    Check if webhook processing is enabled.
    Used by other modules to check webhook status.
    """
    global webhook_enabled
    return webhook_enabled


# ============================================================================
# STATISTICS AND TRACKING ROUTES
# ============================================================================

def setup_stats_routes(app, get_services_func):
    """Setup statistics and tracking routes - called from main.py"""

    @app.get("/tracking/document/{doc_name}")
    @api_response
    async def get_document_status(doc_name: str, bucket: str):
        """Get processing status for specific document"""
        try:
            services = get_services_func()
            status = services.tracker.get_status(doc_name, bucket)
            return APIResponse.success(status, "Document status retrieved")
        except Exception as e:
            APIResponse.error(f"Document status failed: {str(e)}", 500)

    @app.get("/tracking/documents")
    @api_response
    async def get_all_documents(bucket: Optional[str] = Query(None)):
        """Get all documents with processing status"""
        try:
            services = get_services_func()
            documents = services.tracker.get_all_documents(bucket)
            return APIResponse.success({
                "documents": documents,
                "total_count": len(documents),
                "bucket_filter": bucket
            })
        except Exception as e:
            APIResponse.error(f"Documents retrieval failed: {str(e)}", 500)

    @app.get("/stats/processing")
    @api_response
    async def get_processing_stats():
        """Get processing statistics including STP stats"""
        try:
            services = get_services_func()
            stats = services.tracker.get_stats()
            return APIResponse.success(stats, "Processing statistics retrieved")
        except Exception as e:
            APIResponse.error(f"Stats retrieval failed: {str(e)}", 500)

    @app.get("/stats/stp")
    @api_response
    async def get_stp_stats():
        """Get STP processing statistics"""
        try:
            services = get_services_func()

            # Get overall stats from tracker
            overall_stats = services.tracker.get_stats()

            # Extract STP-specific stats
            stp_stats = overall_stats.get("stp_statistics", {})

            return APIResponse.success({
                "stp_processed_documents": overall_stats.get("stp_processed", 0),
                "total_stp_chunks": stp_stats.get("total_stp_chunks", 0),
                "total_non_stp_chunks": stp_stats.get("total_non_stp_chunks", 0),
                "stp_ratio": stp_stats.get("stp_ratio", "0%"),
                "stp_enabled": config.is_stp_enabled(),
                "stp_config": {
                    "classifier_model": config.get_stp_classifier_config()["model_path"],
                    "min_confidence": config.get_stp_classifier_config()["min_confidence"],
                    "rephrasing_enabled": config.get_stp_rephrasing_config()["enabled"],
                    "qf_enabled": config.get_stp_qf_config()["enabled"]
                }
            }, "STP statistics retrieved")

        except Exception as e:
            APIResponse.error(f"STP stats retrieval failed: {str(e)}", 500)

    @app.get("/health/stp")
    @api_response
    async def stp_health_check():
        """Check STP processor health"""
        try:
            from processors.stp_processor import stp_processor

            is_healthy = stp_processor.health_check()
            config_validation = config.validate_stp_config()
            dependencies = config.check_stp_dependencies()

            return APIResponse.success({
                "stp_enabled": config.is_stp_enabled(),
                "stp_healthy": is_healthy,
                "configuration_valid": config_validation["valid"],
                "configuration_errors": config_validation["errors"],
                "configuration_warnings": config_validation["warnings"],
                "dependencies": dependencies["dependencies"],
                "all_dependencies_available": dependencies["all_available"],
                "missing_dependencies": dependencies["missing"],
                "critical_missing": dependencies["critical_missing"],
                "milvus_config": config.get_stp_milvus_config(),
                "classifier_config": config.get_stp_classifier_config(),
                "environment_info": config.get_stp_environment_info()
            }, "STP health check completed")

        except Exception as e:
            APIResponse.error(f"STP health check failed: {str(e)}", 500)

    @app.get("/health/lancedb")
    @api_response
    async def lancedb_health_check():
        """Check LanceDB storage health and connectivity"""
        try:
            services = get_services_func()
            lancedb = services.lancedb_storage

            if lancedb is None:
                return APIResponse.success({
                    "lancedb_available": False,
                    "lancedb_healthy": False,
                    "message": "LanceDB storage not initialized",
                    "db_path": None,
                    "tables": []
                }, "LanceDB not available")

            # Check health
            is_healthy = lancedb.health_check()

            # Get database info
            db_info = {
                "lancedb_available": True,
                "lancedb_healthy": is_healthy,
                "db_path": str(lancedb.db_path),
                "tables": [],
                "table_count": 0
            }

            # Try to get table information
            if is_healthy:
                try:
                    table_names = lancedb.db.table_names()
                    db_info["tables"] = table_names
                    db_info["table_count"] = len(table_names)

                    # Get row counts for each table
                    table_stats = {}
                    for table_name in table_names:
                        try:
                            table = lancedb.db.open_table(table_name)
                            count = table.count_rows()
                            table_stats[table_name] = {"row_count": count}
                        except Exception as e:
                            table_stats[table_name] = {"error": str(e)}

                    db_info["table_stats"] = table_stats

                except Exception as e:
                    db_info["table_info_error"] = str(e)

            return APIResponse.success(db_info, "LanceDB health check completed")

        except Exception as e:
            APIResponse.error(f"LanceDB health check failed: {str(e)}", 500)
