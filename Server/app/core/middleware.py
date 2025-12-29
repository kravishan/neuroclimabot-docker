"""Custom middleware for the application with Prometheus metrics."""

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, PlainTextResponse

from app.core.exceptions import RateLimitError
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Prometheus metrics (with fallback if prometheus_client not available)
try:
    from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
    
    # Define metrics
    request_count = Counter(
        'neuroclima_requests_total', 
        'Total HTTP requests', 
        ['method', 'endpoint', 'status_code']
    )
    request_duration = Histogram(
        'neuroclima_request_duration_seconds', 
        'HTTP request duration in seconds',
        ['method', 'endpoint']
    )
    active_sessions = Gauge('neuroclima_active_sessions', 'Number of active sessions')
    cache_hit_rate = Gauge('neuroclima_cache_hit_rate', 'Cache hit rate')
    llm_duration = Histogram('neuroclima_llm_duration_seconds', 'LLM generation time in seconds')
    retrieval_duration = Histogram('neuroclima_retrieval_duration_seconds', 'Document retrieval time in seconds')
    active_requests = Gauge('neuroclima_active_requests', 'Number of requests currently being processed')
    
    PROMETHEUS_AVAILABLE = True
    logger.info("✅ Prometheus metrics enabled")
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("⚠️  Prometheus client not available - metrics disabled")


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware to collect Prometheus metrics."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not PROMETHEUS_AVAILABLE:
            return await call_next(request)
        
        # Skip metrics collection for the metrics endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)
        
        start_time = time.perf_counter()
        method = request.method
        endpoint = self._get_endpoint_label(request.url.path)
        
        # Increment active requests
        active_requests.inc()
        
        try:
            response = await call_next(request)
            status_code = str(response.status_code)
        except Exception as e:
            status_code = "500"
            # Re-raise the exception after recording metrics
            duration = time.perf_counter() - start_time
            request_count.labels(method=method, endpoint=endpoint, status_code=status_code).inc()
            request_duration.labels(method=method, endpoint=endpoint).observe(duration)
            active_requests.dec()
            raise
        
        # Record metrics
        duration = time.perf_counter() - start_time
        request_count.labels(method=method, endpoint=endpoint, status_code=status_code).inc()
        request_duration.labels(method=method, endpoint=endpoint).observe(duration)
        active_requests.dec()
        
        return response
    
    def _get_endpoint_label(self, path: str) -> str:
        """Convert path to a metrics-friendly endpoint label."""
        # Group similar endpoints to avoid metric explosion
        if path.startswith("/api/v1/chat/continue/"):
            return "/api/v1/chat/continue/{session_id}"
        elif path.startswith("/api/v1/chat/sessions/"):
            if path.endswith("/messages"):
                return "/api/v1/chat/sessions/{session_id}/messages"
            else:
                return "/api/v1/chat/sessions/{session_id}"
        elif path == "/":
            return "/"
        elif path == "/health":
            return "/health"
        elif path == "/docs":
            return "/docs"
        elif path == "/openapi.json":
            return "/openapi.json"
        elif path.startswith("/api/v1/"):
            # Keep the first 3 parts of API paths
            parts = path.split("/")[:4]  # ['', 'api', 'v1', 'endpoint']
            return "/".join(parts)
        else:
            return "other"


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
        
        # Skip logging for metrics endpoint to reduce noise
        if request.url.path != "/metrics":
            logger.info(
                f"Request started: {request.method} {request.url} from {client_ip} (ID: {request_id})"
            )
        
        response = await call_next(request)
        
        # Log response (skip metrics endpoint)
        if request.url.path != "/metrics":
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
        # Skip rate limiting for metrics endpoint
        if request.url.path == "/metrics":
            return await call_next(request)
        
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()
        
        # Clean old entries
        self._cleanup_old_entries(current_time)
        
        # Check rate limit
        if self._is_rate_limited(client_ip, current_time):
            # Record rate limit hit in metrics
            if PROMETHEUS_AVAILABLE:
                request_count.labels(
                    method=request.method, 
                    endpoint=request.url.path, 
                    status_code="429"
                ).inc()
            
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


# Helper functions to update metrics from other parts of the application
def update_active_sessions(count: int):
    """Update the active sessions metric."""
    if PROMETHEUS_AVAILABLE:
        active_sessions.set(count)


def update_cache_hit_rate(rate: float):
    """Update the cache hit rate metric."""
    if PROMETHEUS_AVAILABLE:
        cache_hit_rate.set(rate)


def record_llm_duration(duration: float):
    """Record LLM generation duration."""
    if PROMETHEUS_AVAILABLE:
        llm_duration.observe(duration)


def record_retrieval_duration(duration: float):
    """Record document retrieval duration."""
    if PROMETHEUS_AVAILABLE:
        retrieval_duration.observe(duration)


def get_metrics_response():
    """Generate Prometheus metrics response."""
    if not PROMETHEUS_AVAILABLE:
        return PlainTextResponse(
            "# Prometheus metrics not available\n# Install prometheus_client package\n",
            media_type="text/plain"
        )
    
    try:
        metrics_data = generate_latest()
        return PlainTextResponse(metrics_data, media_type=CONTENT_TYPE_LATEST)
    except Exception as e:
        logger.error(f"Error generating metrics: {e}")
        return PlainTextResponse(
            f"# Error generating metrics: {e}\n",
            media_type="text/plain",
            status_code=500
        )