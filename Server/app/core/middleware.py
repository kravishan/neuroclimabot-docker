"""Custom middleware for the application."""

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, PlainTextResponse

from app.core.exceptions import RateLimitError
from app.utils.logger import get_logger

logger = get_logger(__name__)


class TimingMiddleware(BaseHTTPMiddleware):
    """Middleware to add timing information to responses."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.perf_counter()
        
        # Add request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.perf_counter() - start_time
        
        # Add headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(round(process_time, 4))
        
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request/response logging."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.perf_counter()
        
        # Get client IP safely
        client_ip = "unknown"
        if request.client:
            client_ip = request.client.host
        
        # Get request ID
        request_id = getattr(request.state, 'request_id', None)

        logger.info(
            f"Request started: {request.method} {request.url} from {client_ip} (ID: {request_id})"
        )
        
        response = await call_next(request)

        # Log response
        process_time = time.perf_counter() - start_time
        logger.info(
            f"Request completed: {request.method} {request.url} - {response.status_code} - {round(process_time, 4)}s (ID: {request_id})"
        )
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiting middleware."""
    
    def __init__(self, app, requests_per_minute: int = 100):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.clients = {}
        self.window_size = 60  # 1 minute
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()
        
        # Clean old entries
        self._cleanup_old_entries(current_time)
        
        # Check rate limit
        if self._is_rate_limited(client_ip, current_time):
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "message": "Rate limit exceeded. Please try again later.",
                    "error_type": "RateLimitError",
                }
            )
        
        # Record request
        self._record_request(client_ip, current_time)
        
        return await call_next(request)
    
    def _cleanup_old_entries(self, current_time: float):
        """Remove old entries from the rate limit tracker."""
        cutoff_time = current_time - self.window_size
        
        for client_ip in list(self.clients.keys()):
            self.clients[client_ip] = [
                timestamp for timestamp in self.clients[client_ip]
                if timestamp > cutoff_time
            ]
            
            if not self.clients[client_ip]:
                del self.clients[client_ip]
    
    def _is_rate_limited(self, client_ip: str, current_time: float) -> bool:
        """Check if the client is rate limited."""
        if client_ip not in self.clients:
            return False
        
        return len(self.clients[client_ip]) >= self.requests_per_minute
    
    def _record_request(self, client_ip: str, current_time: float):
        """Record a request for rate limiting."""
        if client_ip not in self.clients:
            self.clients[client_ip] = []
        
        self.clients[client_ip].append(current_time)