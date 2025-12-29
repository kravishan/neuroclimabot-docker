"""Custom exceptions and exception handlers."""

import logging
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

logger = logging.getLogger(__name__)


class RAGException(Exception):
    """Base exception for RAG-related errors."""
    
    def __init__(self, message: str, details: Dict[str, Any] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class DocumentProcessingError(RAGException):
    """Document processing related errors."""
    pass


class VectorStoreError(RAGException):
    """Vector store related errors."""
    pass


class LLMError(RAGException):
    """LLM service related errors."""
    pass


class SessionError(RAGException):
    """Session management related errors."""
    pass


class RateLimitError(RAGException):
    """Rate limiting related errors."""
    pass


async def rag_exception_handler(request: Request, exc: RAGException) -> JSONResponse:
    """Handle RAG-specific exceptions."""
    logger.error(f"RAG error on {request.url}: {exc.message}", extra=exc.details)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": exc.message,
            "error_type": exc.__class__.__name__,
            "details": exc.details,
        }
    )


async def rate_limit_exception_handler(request: Request, exc: RateLimitError) -> JSONResponse:
    """Handle rate limit exceptions."""
    logger.warning(f"Rate limit exceeded for {request.client.host}: {exc.message}")
    
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "success": False,
            "message": "Rate limit exceeded. Please try again later.",
            "error_type": "RateLimitError",
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle request validation errors."""
    logger.warning(f"Validation error on {request.url}: {exc.errors()}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "message": "Validation error",
            "error_type": "ValidationError",
            "details": exc.errors(),
        }
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions."""
    logger.warning(f"HTTP error {exc.status_code} on {request.url}: {exc.detail}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "error_type": "HTTPError",
        }
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle general exceptions."""
    logger.error(f"Unexpected error on {request.url}: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "Internal server error",
            "error_type": "InternalError",
        }
    )


def setup_exception_handlers(app: FastAPI) -> None:
    """Setup exception handlers for the application."""
    app.add_exception_handler(RAGException, rag_exception_handler)
    app.add_exception_handler(RateLimitError, rate_limit_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)