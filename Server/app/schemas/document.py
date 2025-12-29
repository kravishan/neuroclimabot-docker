"""Document-related schemas."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .common import BaseResponse


class DocumentStatus(str, Enum):
    """Document processing status."""
    
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    DELETED = "deleted"


class DocumentType(str, Enum):
    """Document type."""
    
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    MD = "md"
    HTML = "html"


class DocumentMetadata(BaseModel):
    """Document metadata."""
    
    id: UUID = Field(default_factory=uuid4)
    filename: str
    original_filename: str
    file_type: DocumentType
    file_size: int = Field(..., description="File size in bytes")
    upload_date: datetime = Field(default_factory=datetime.now)
    status: DocumentStatus = DocumentStatus.UPLOADED
    processing_error: Optional[str] = None
    
    # Content metadata
    page_count: Optional[int] = None
    word_count: Optional[int] = None
    chunk_count: Optional[int] = None
    language: Optional[str] = None
    
    # Custom metadata
    tags: List[str] = []
    category: Optional[str] = None
    source: Optional[str] = None
    custom_fields: Dict = {}


class DocumentChunk(BaseModel):
    """Document chunk for vector storage."""
    
    id: UUID = Field(default_factory=uuid4)
    document_id: UUID
    content: str
    chunk_index: int
    token_count: int
    embedding: Optional[List[float]] = None
    metadata: Dict = {}


class DocumentUploadRequest(BaseModel):
    """Document upload request."""
    
    tags: List[str] = []
    category: Optional[str] = None
    source: Optional[str] = None
    language: Optional[str] = None
    custom_fields: Dict = {}


class DocumentUploadResponse(BaseResponse):
    """Document upload response."""
    
    document: DocumentMetadata


class DocumentListResponse(BaseResponse):
    """Document list response."""
    
    documents: List[DocumentMetadata]
    total: int


class DocumentDeleteResponse(BaseResponse):
    """Document deletion response."""
    
    document_id: UUID
    deleted: bool


class ProcessingStats(BaseModel):
    """Document processing statistics."""
    
    total_documents: int
    processed_documents: int
    failed_documents: int
    total_chunks: int
    processing_queue_size: int