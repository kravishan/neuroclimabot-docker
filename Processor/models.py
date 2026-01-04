"""
Data models for API requests and responses including STP support
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ============================================
# EXISTING MODELS (Unchanged)
# ============================================

class ProcessRequest(BaseModel):
    """Basic document processing request"""
    bucket: str
    filename: str
    file_path: Optional[str] = None


class EnhancedProcessRequest(BaseModel):
    """Enhanced document processing request with granular control"""
    bucket: str
    filename: str
    include_chunking: bool = True
    include_summarization: bool = True
    include_graphrag: bool = False
    include_stp: bool = False  # NEW: STP processing option


class BatchProcessRequest(BaseModel):
    """Batch processing request for all buckets"""
    skip_processed: bool = True
    include_chunking: bool = True
    include_summarization: bool = True
    include_graphrag: bool = False
    include_stp: bool = False  # NEW: STP processing option
    max_documents_per_bucket: Optional[int] = None


class BucketProcessRequest(BaseModel):
    """Bucket-specific processing request"""
    bucket: str
    skip_processed: bool = True
    include_chunking: bool = True
    include_summarization: bool = True
    include_graphrag: bool = False
    include_stp: bool = False  # NEW: STP processing option
    max_documents: Optional[int] = None


class SearchRequest(BaseModel):
    """Vector search request"""
    query: str
    bucket: Optional[str] = None
    limit: int = Field(default=10, ge=1, le=100)


# ============================================
# NEW: STP-SPECIFIC MODELS
# ============================================

class STPProcessRequest(BaseModel):
    """STP-only processing request"""
    bucket: str
    filename: str
    file_path: Optional[str] = None


class STPBatchProcessRequest(BaseModel):
    """Batch STP processing request"""
    bucket: Optional[str] = None  # None means all buckets
    skip_processed: bool = True
    max_documents: Optional[int] = None


class STPChunkData(BaseModel):
    """STP chunk data structure"""
    chunk_id: str
    doc_name: str
    bucket_source: str
    original_content: str  # Original text
    rephrased_content: str  # Rephrased text (80 words max)
    stp_prediction: str  # "STP" or "Non-STP"
    stp_confidence: float
    qualifying_factors: str  # 5 qualifying factors
    chunk_index: int
    tokens: int
    processing_timestamp: str
    chunk_metadata: Optional[Dict[str, Any]] = None


class STPProcessingResult(BaseModel):
    """STP processing result"""
    status: str
    message: str
    total_chunks: int
    stp_chunks: int
    non_stp_chunks: int
    stored_chunks: int
    processing_time_seconds: float
    document_name: str
    bucket_source: str
    statistics: Optional[Dict[str, Any]] = None


class STPSearchRequest(BaseModel):
    """STP search request"""
    query: str
    top_k: int = Field(default=5, ge=1, le=100)
    include_metadata: bool = True
    min_similarity: float = Field(default=0.0, ge=0.0, le=1.0)


class STPSearchResult(BaseModel):
    """STP search result item"""
    id: int
    doc_name: str
    stp_confidence: float
    rephrased_content: str
    chunk_id: str
    tokens: int
    similarity_score: float
    original_content: Optional[str] = None
    qualifying_factors: Optional[str] = None


class STPHealthResponse(BaseModel):
    """STP service health check response - minimal version"""
    status: str  # Only "healthy" or "unhealthy"


class STPStatsResponse(BaseModel):
    """STP statistics response"""
    status: str
    statistics: Dict[str, Any]
    timestamp: str


# ============================================
# PROCESSING STATUS MODELS
# ============================================

class ProcessingStatus(str, Enum):
    """Processing task status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class ProcessingTask(BaseModel):
    """Processing task model"""
    task_id: str
    bucket: str
    filename: str
    file_path: str
    status: ProcessingStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    attempts: int = 0
    max_attempts: int = 3
    result: Optional[Dict[str, Any]] = None


# ============================================
# DOCUMENT DATA MODELS
# ============================================

class ChunkData(BaseModel):
    """Chunk data structure"""
    chunk_id: str
    doc_name: str
    bucket_source: str
    chunk_text: str
    chunk_index: int
    token_count: int
    processing_timestamp: str
    chunk_metadata: Optional[Dict[str, Any]] = None
    embedding: Optional[List[float]] = None


class SummaryData(BaseModel):
    """Summary data structure"""
    summary_id: Optional[str] = None
    doc_name: str
    bucket_source: str
    document_type: str
    abstractive_summary: str
    processing_timestamp: Optional[str] = None
    document_metadata: Dict[str, Any] = {}
    embedding: Optional[List[float]] = None


class DocumentMetadata(BaseModel):
    """Document metadata"""
    filename: str
    bucket: str
    file_type: str
    size_bytes: int
    upload_timestamp: Optional[str] = None
    processing_timestamp: Optional[str] = None


# ============================================
# SERVICE CONTAINER
# ============================================

class ServiceContainer:
    """Container for all services with STP support"""
    
    def __init__(self):
        self.services = {}
        self._initialized = False
    
    def add_service(self, name: str, service):
        """Add a service to the container"""
        self.services[name] = service
    
    def get_service(self, name: str):
        """Get a service from the container"""
        return self.services.get(name)
    
    def is_service_available(self, name: str) -> bool:
        """Check if service is available"""
        return name in self.services and self.services[name] is not None
    
    def get_available_services(self) -> List[str]:
        """Get list of available services"""
        return [name for name, service in self.services.items() if service is not None]
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of all services"""
        available = self.get_available_services()
        
        health_status = {
            "available": available,
            "healthy_count": len(available),
            "services": {}
        }
        
        for name, service in self.services.items():
            if service is not None:
                try:
                    if hasattr(service, 'health_check'):
                        is_healthy = service.health_check()
                        health_status["services"][name] = "healthy" if is_healthy else "unhealthy"
                    else:
                        health_status["services"][name] = "available"
                except Exception as e:
                    health_status["services"][name] = f"error: {str(e)}"
            else:
                health_status["services"][name] = "unavailable"
        
        return health_status
    
    async def cleanup(self):
        """Cleanup all services"""
        import asyncio
        for name, service in self.services.items():
            if service is not None:
                try:
                    if hasattr(service, 'disconnect'):
                        if asyncio.iscoroutinefunction(service.disconnect):
                            await service.disconnect()
                        else:
                            service.disconnect()
                    elif hasattr(service, 'cleanup'):
                        if asyncio.iscoroutinefunction(service.cleanup):
                            await service.cleanup()
                        else:
                            service.cleanup()
                    elif hasattr(service, 'close'):
                        if asyncio.iscoroutinefunction(service.close):
                            await service.close()
                        else:
                            service.close()
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).error(f"Error cleaning up service {name}: {e}")


# ============================================
# RESPONSE BUILDERS
# ============================================

class APIResponse:
    """Standard API response builder"""
    
    @staticmethod
    def success(data: Any = None, message: str = "Success") -> Dict[str, Any]:
        """Create success response"""
        response = {
            "status": "success",
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        if data is not None:
            response["data"] = data
        return response
    
    @staticmethod
    def error(message: str, status_code: int = 500, detail: str = None) -> Dict[str, Any]:
        """Create error response"""
        from fastapi import HTTPException
        response = {
            "status": "error",
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        if detail:
            response["detail"] = detail
        raise HTTPException(status_code=status_code, detail=response)


class QueueResponseBuilder:
    """Queue response builder"""
    
    @staticmethod
    def build_queue_status(queue) -> Dict[str, Any]:
        """Build queue status response"""
        if not queue:
            return APIResponse.error("Processing queue unavailable", 503)
        
        status = queue.get_queue_status()
        return APIResponse.success(status, "Queue status retrieved")
    
    @staticmethod
    def build_task_response(task_id: str, queue) -> Dict[str, Any]:
        """Build task status response"""
        if not queue:
            return APIResponse.error("Processing queue unavailable", 503)
        
        task_status = queue.get_task_status(task_id)
        
        if not task_status:
            return APIResponse.error(f"Task {task_id} not found", 404)
        
        return APIResponse.success(task_status, "Task status retrieved")


# ============================================
# STP-SPECIFIC RESPONSE BUILDERS
# ============================================

class STPResponseBuilder:
    """STP response builder"""
    
    @staticmethod
    def build_processing_result(result: Dict[str, Any]) -> STPProcessingResult:
        """Build STP processing result"""
        return STPProcessingResult(
            status=result.get("status", "unknown"),
            message=result.get("message", ""),
            total_chunks=result.get("total_chunks", 0),
            stp_chunks=result.get("stp_chunks", 0),
            non_stp_chunks=result.get("non_stp_chunks", 0),
            stored_chunks=result.get("stored_chunks", 0),
            processing_time_seconds=result.get("processing_time_seconds", 0.0),
            document_name=result.get("document_name", ""),
            bucket_source=result.get("bucket_source", ""),
            statistics=result.get("statistics", {})
        )
    
    @staticmethod
    def build_search_result(results: List[Dict[str, Any]]) -> List[STPSearchResult]:
        """Build STP search results"""
        return [
            STPSearchResult(
                id=result.get("id", 0),
                doc_name=result.get("doc_name", ""),
                stp_confidence=result.get("stp_confidence", 0.0),
                rephrased_content=result.get("rephrased_content", ""),
                chunk_id=result.get("chunk_id", ""),
                tokens=result.get("tokens", 0),
                similarity_score=result.get("similarity_score", 0.0),
                original_content=result.get("original_content"),
                qualifying_factors=result.get("qualifying_factors")
            )
            for result in results
        ]
    
    @staticmethod
    def build_health_response(is_healthy: bool) -> STPHealthResponse:
        """Build minimal STP health response"""
        return STPHealthResponse(
            status="healthy" if is_healthy else "unhealthy"
        )
    
    @staticmethod
    def build_stats_response(stats_data: Dict[str, Any]) -> STPStatsResponse:
        """Build STP stats response"""
        return STPStatsResponse(
            status="success",
            statistics=stats_data,
            timestamp=datetime.now().isoformat()
        )