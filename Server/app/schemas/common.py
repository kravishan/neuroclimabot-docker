"""Common schemas used across the application."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field


class BaseResponse(BaseModel):
    """Base response model."""
    
    success: bool = True
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class ErrorResponse(BaseResponse):
    """Error response model."""
    
    success: bool = False
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class PaginationParams(BaseModel):
    """Pagination parameters."""
    
    page: int = Field(1, ge=1, description="Page number")
    size: int = Field(20, ge=1, le=100, description="Page size")
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


class PaginatedResponse(BaseResponse):
    """Paginated response model."""
    
    page: int
    size: int
    total: int
    pages: int
    data: List[Any]


class HealthCheck(BaseModel):
    """Health check response."""
    
    status: str
    version: str
    timestamp: datetime = Field(default_factory=datetime.now)
    services: Dict[str, str] = {}