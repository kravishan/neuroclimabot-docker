"""
API Middleware for error handling, validation, and response formatting
"""

import time
import logging
from typing import Callable, Dict, Any
from datetime import datetime

from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Unified error handling middleware"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            response.headers["X-Process-Time"] = str(process_time)
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unhandled error in {request.method} {request.url.path}: {e}")
            return JSONResponse(
                status_code=500,
                content=create_error_response(
                    "Internal server error",
                    str(e) if logger.level == logging.DEBUG else "An unexpected error occurred"
                )
            )


def create_error_response(message: str, detail: str = None) -> Dict[str, Any]:
    """Create standardized error response"""
    response = {
        "status": "error",
        "message": message,
        "timestamp": datetime.now().isoformat()
    }
    if detail:
        response["detail"] = detail
    return response


def create_success_response(data: Any = None, message: str = "Success") -> Dict[str, Any]:
    """Create standardized success response"""
    response = {
        "status": "success",
        "message": message,
        "timestamp": datetime.now().isoformat()
    }
    if data is not None:
        response["data"] = data
    return response


def validate_required_services(services, required: list):
    """Validate that required services are available"""
    missing = []
    for service_name in required:
        service = getattr(services, service_name, None)
        if not service:
            missing.append(service_name)
    
    if missing:
        raise HTTPException(
            status_code=503,
            detail=f"Required services unavailable: {', '.join(missing)}"
        )


def validate_bucket_access(bucket: str, allowed_buckets: list = None):
    """Validate bucket access"""
    if allowed_buckets and bucket not in allowed_buckets:
        raise HTTPException(
            status_code=403,
            detail=f"Access denied to bucket '{bucket}'"
        )


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """Request validation middleware"""
    
    def __init__(self, app, max_content_length: int = 100 * 1024 * 1024):  # 100MB
        super().__init__(app)
        self.max_content_length = max_content_length
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check content length
        content_length = request.headers.get('content-length')
        if content_length and int(content_length) > self.max_content_length:
            return JSONResponse(
                status_code=413,
                content=create_error_response(
                    "Request too large",
                    f"Maximum allowed size: {self.max_content_length} bytes"
                )
            )
        
        return await call_next(request)