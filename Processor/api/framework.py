import logging
from functools import wraps
from typing import Dict, Any, List, Callable, Optional
from datetime import datetime
from fastapi import HTTPException
from models import ProcessingStatus


logger = logging.getLogger(__name__)


class APIResponse:
    """Standardized API response builder"""
    
    @staticmethod
    def success(data: Any = None, message: str = "Operation completed successfully", **kwargs) -> Dict[str, Any]:
        """Build success response"""
        response = {
            "status": "success",
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        
        if data is not None:
            response["data"] = data
        
        response.update(kwargs)
        return response
    
    @staticmethod
    def error(message: str, status_code: int = 500, details: Any = None) -> None:
        """Build error response and raise HTTPException"""
        error_data = {
            "status": "error",
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        
        if details:
            error_data["details"] = details
        
        raise HTTPException(status_code=status_code, detail=error_data)
    
    @staticmethod
    def partial_success(data: Any, message: str, issues: List[str] = None) -> Dict[str, Any]:
        """Build partial success response"""
        response = APIResponse.success(data, message)
        response["status"] = "partial_success"
        
        if issues:
            response["issues"] = issues
        
        return response
    
    @staticmethod
    def processing_result(result: Dict[str, Any], doc_name: str, bucket: str) -> Dict[str, Any]:
        """Build processing result response"""
        overall_status = result.get("overall_status", "unknown")
        
        response = {
            "status": "success" if overall_status == "success" else "partial_success",
            "message": result.get("message", "Processing completed"),
            "doc_name": doc_name,
            "bucket_source": bucket,
            "processing_result": result,
            "timestamp": datetime.now().isoformat()
        }
        
        return response


class ServiceValidator:
    """Service availability validation"""
    
    def __init__(self, services: Dict[str, Any]):
        self.services = services
    
    def check_services(self, required: List[str]) -> None:
        """Check if required services are available"""
        missing = [s for s in required if not self.services.get(s)]
        if missing:
            APIResponse.error(f"Services unavailable: {missing}", 503)
    
    def check_queue(self, queue) -> None:
        """Check if processing queue is available"""
        if not queue:
            APIResponse.error("Processing queue unavailable", 503)


def require_services(services: List[str]):
    """Decorator to check service availability"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get services from global context or dependency injection
            service_validator = kwargs.get('validator')
            if service_validator:
                service_validator.check_services(services)
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def handle_errors(func: Callable):
    """Decorator for standardized error handling"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            result = await func(*args, **kwargs)
            
            # Auto-wrap simple responses
            if isinstance(result, dict) and "status" not in result:
                return APIResponse.success(result)
            
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}")
            APIResponse.error(f"Operation failed: {str(e)}")
    
    return wrapper


def api_response(func: Callable):
    """Combined decorator for API endpoints"""
    return handle_errors(func)


class ProcessingResultBuilder:
    """Helper for building processing results"""
    
    @staticmethod
    def build_component_result(status: str, enabled: bool, **kwargs) -> Dict[str, Any]:
        """Build individual component result"""
        if not enabled:
            return {"status": "skipped", "message": "Component disabled", "enabled": False}
        
        result = {"status": status, "enabled": True}
        result.update(kwargs)
        return result
    
    @staticmethod
    def build_processing_summary(results: Dict[str, Dict], enabled_processes: List[str]) -> Dict[str, Any]:
        """Build processing summary"""
        successful = [name for name, result in results.items() 
                     if name in enabled_processes and result.get("status") == "success"]
        
        total_enabled = len(enabled_processes)
        total_successful = len(successful)
        
        return {
            "enabled_processes": enabled_processes,
            "successful_processes": successful,
            "total_enabled": total_enabled,
            "total_successful": total_successful,
            "success_rate": f"{(total_successful/total_enabled)*100:.1f}%" if total_enabled > 0 else "0%"
        }
    
    @staticmethod
    def determine_overall_status(results: Dict[str, Dict], enabled_processes: List[str]) -> str:
        """Determine overall processing status"""
        if not enabled_processes:
            return "failed"
        
        successful = [name for name, result in results.items() 
                     if name in enabled_processes and result.get("status") == "success"]
        
        if len(successful) == len(enabled_processes):
            return "success"
        elif len(successful) > 0:
            return "partial_success"
        else:
            return "failed"


class BatchResultBuilder:
    """Helper for building batch processing results"""
    
    @staticmethod
    def build_bucket_result(documents_processed: int, successful: int, failed: int, **kwargs) -> Dict[str, Any]:
        """Build bucket processing result"""
        return {
            "documents_processed": documents_processed,
            "successful_documents": successful,
            "failed_documents": failed,
            "success_rate": f"{(successful/documents_processed)*100:.1f}%" if documents_processed > 0 else "0%",
            **kwargs
        }
    
    @staticmethod
    def build_final_stats(bucket_results: Dict[str, Any]) -> Dict[str, Any]:
        """Build final batch statistics"""
        total_docs = sum(r["documents_processed"] for r in bucket_results.values())
        successful_docs = sum(r["successful_documents"] for r in bucket_results.values())
        failed_docs = sum(r["failed_documents"] for r in bucket_results.values())
        
        return {
            "total_documents": total_docs,
            "successful_documents": successful_docs,
            "failed_documents": failed_docs,
            "success_rate": f"{(successful_docs/total_docs)*100:.1f}%" if total_docs > 0 else "0%",
            "buckets_processed": len(bucket_results)
        }


class QueueResponseBuilder:
    """Helper for building queue-related responses"""
    
    @staticmethod
    def build_queue_status(queue) -> Dict[str, Any]:
        """Build queue status response"""
        if not queue:
            return {"status": "unavailable", "message": "Queue not initialized"}
        
        status = queue.get_queue_status()
        return {
            "status": "running" if status["is_processing"] else "stopped",
            "queue_info": status
        }
    
    @staticmethod
    def build_task_response(task_id: str, queue) -> Dict[str, Any]:
        """Build task status response"""
        if not queue:
            APIResponse.error("Processing queue unavailable", 503)
        
        task_status = queue.get_task_status(task_id)
        if not task_status:
            APIResponse.error(f"Task {task_id} not found", 404)
        
        return APIResponse.success(task_status, "Task status retrieved")