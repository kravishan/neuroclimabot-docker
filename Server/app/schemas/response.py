"""Response generation schemas."""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from .common import BaseResponse


class GenerationConfig(BaseModel):
    """Response generation configuration."""
    
    temperature: float = Field(0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(2000, ge=1, le=4000)
    top_p: float = Field(0.9, ge=0.0, le=1.0)
    frequency_penalty: float = Field(0.0, ge=-2.0, le=2.0)
    presence_penalty: float = Field(0.0, ge=-2.0, le=2.0)
    stop_sequences: List[str] = []


class RetrievalConfig(BaseModel):
    """Document retrieval configuration."""
    
    max_documents: int = Field(10, ge=1, le=50)
    similarity_threshold: float = Field(0.7, ge=0.0, le=1.0)
    enable_reranking: bool = True
    rerank_top_k: int = Field(5, ge=1, le=20)


class RAGRequest(BaseModel):
    """RAG request model."""
    
    query: str = Field(..., min_length=1, max_length=2000)
    language: str = "en"
    include_sources: bool = True
    generation_config: Optional[GenerationConfig] = None
    retrieval_config: Optional[RetrievalConfig] = None
    session_id: Optional[UUID] = None


class RAGResponse(BaseResponse):
    """RAG response model."""
    
    query: str
    response: str
    sources: List[Dict] = []
    language: str
    processing_time: float
    retrieval_time: float
    generation_time: float
    token_usage: Optional[Dict[str, int]] = None


class FeedbackRequest(BaseModel):
    """User feedback request."""
    
    message_id: UUID
    rating: int = Field(..., ge=1, le=5, description="Rating from 1-5")
    feedback_type: str = Field(..., description="Type of feedback")
    comment: Optional[str] = Field(None, max_length=1000)
    helpful: Optional[bool] = None


class FeedbackResponse(BaseResponse):
    """Feedback response."""
    
    message_id: UUID
    recorded: bool