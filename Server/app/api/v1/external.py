"""External API endpoints for document retrieval."""

from typing import List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.external.milvus import get_milvus_client
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


class DocumentSummaryRequest(BaseModel):
    """Request model for document summary."""
    filename: str = Field(..., description="Document filename to retrieve")


class DocumentSummaryResponse(BaseModel):
    """Response model for document summary."""
    collection: str = Field(..., description="Source collection name")
    doc_name: str = Field(..., description="Document name")
    summary: str = Field(..., description="Document summary")


class DocumentListResponse(BaseModel):
    """Response model for document list."""
    documents: List[str] = Field(..., description="List of all document names")


@router.get(
    "/documents",
    response_model=DocumentListResponse,
    summary="Get all document names",
    description="Retrieve list of all document names from all collections"
)
async def get_all_documents() -> DocumentListResponse:
    """
    Get list of all document names from all collections.
    
    Returns:
        DocumentListResponse with list of all document names
    """
    try:
        milvus_client = get_milvus_client()
        
        if not milvus_client.is_connected:
            raise HTTPException(status_code=503, detail="Vector database not available")
        
        logger.info("🔍 External API: Retrieving all document names")
        
        # Get all document names from summary collections
        all_documents = await _get_all_document_names(milvus_client)
        
        logger.info(f"✅ External API: Found {len(all_documents)} documents")
        
        return DocumentListResponse(documents=all_documents)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ External API error getting document list: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post(
    "/summary",
    response_model=DocumentSummaryResponse,
    summary="Get document summary",
    description="Retrieve document summary by filename"
)
async def get_document_summary(request: DocumentSummaryRequest) -> DocumentSummaryResponse:
    """
    Get document summary by filename.
    
    Args:
        request: Request containing filename
        
    Returns:
        DocumentSummaryResponse with collection, doc_name, and summary
    """
    try:
        milvus_client = get_milvus_client()
        
        if not milvus_client.is_connected:
            raise HTTPException(status_code=503, detail="Vector database not available")
        
        logger.info(f"🔍 External API: Getting summary for '{request.filename}'")
        
        # Search for document summary
        summary_data = await _get_document_summary(milvus_client, request.filename)
        
        if not summary_data:
            raise HTTPException(status_code=404, detail=f"Document '{request.filename}' not found")
        
        logger.info(f"✅ External API: Found summary for '{request.filename}'")
        
        return DocumentSummaryResponse(**summary_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ External API error getting summary for '{request.filename}': {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get(
    "/health",
    summary="External API health check",
    description="Check the health of the external API service"
)
async def external_health_check():
    """Health check for external API."""
    try:
        milvus_client = get_milvus_client()
        
        return {
            "status": "healthy",
            "service": "external_api",
            "milvus_connected": milvus_client.is_connected
        }
        
    except Exception as e:
        logger.error(f"External API health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")


async def _get_all_document_names(milvus_client) -> List[str]:
    """Get all document names from all summary collections."""
    all_documents = set()  # Use set to avoid duplicates
    
    try:
        # Get documents from all summary collections
        for collection_name in milvus_client.config.summaries_collections:
            collection_documents = await _get_documents_from_collection(milvus_client, collection_name)
            all_documents.update(collection_documents)
        
        return sorted(list(all_documents))
        
    except Exception as e:
        logger.error(f"Error getting all document names: {e}")
        return []


async def _get_documents_from_collection(milvus_client, collection_name: str) -> List[str]:
    """Get all document names from a specific collection."""
    try:
        from pymilvus import Collection, utility
        
        # Check if collection exists
        if not utility.has_collection(collection_name, using=milvus_client.summaries_connection):
            return []
        
        # Get collection
        collection = Collection(name=collection_name, using=milvus_client.summaries_connection)
        collection.load()
        
        # Get field mapping for this collection
        field_map = milvus_client.config.get_summaries_field_map(collection_name)
        
        # Query all documents
        results = collection.query(
            expr="",  # Empty expression to get all
            output_fields=[field_map["doc_name_field"]],
            limit=10000  # Large limit to get all documents
        )
        
        # Extract document names
        documents = []
        for result in results:
            doc_name = result.get(field_map["doc_name_field"], "")
            if doc_name:
                documents.append(doc_name)
        
        collection.release()
        return documents
        
    except Exception as e:
        logger.error(f"Error getting documents from {collection_name}: {e}")
        return []


async def _get_document_summary(milvus_client, filename: str):
    """Get document summary by filename."""
    try:
        # Search in all summary collections
        for collection_name in milvus_client.config.summaries_collections:
            summary_data = await _get_summary_from_collection(milvus_client, collection_name, filename)
            if summary_data:
                return summary_data
        
        return None
        
    except Exception as e:
        logger.error(f"Error getting document summary: {e}")
        return None


async def _get_summary_from_collection(milvus_client, collection_name: str, filename: str):
    """Get summary from a specific collection."""
    try:
        from pymilvus import Collection, utility
        
        # Check if collection exists
        if not utility.has_collection(collection_name, using=milvus_client.summaries_connection):
            return None
        
        # Get collection
        collection = Collection(name=collection_name, using=milvus_client.summaries_connection)
        collection.load()
        
        # Get field mapping for this collection
        field_map = milvus_client.config.get_summaries_field_map(collection_name)
        
        # Create filter expression for exact match
        filter_expr = f'{field_map["doc_name_field"]} == "{filename}"'
        
        # Define output fields
        output_fields = [
            field_map["doc_name_field"],  # doc_name or source_url
            field_map["content_field"]    # abstractive_summary
        ]
        
        # Query the collection
        results = collection.query(
            expr=filter_expr,
            output_fields=output_fields,
            limit=1
        )
        
        # Process result
        if results:
            result = results[0]
            doc_name = result.get(field_map["doc_name_field"], "")
            summary = result.get(field_map["content_field"], "")
            
            collection.release()
            return {
                "collection": collection_name,
                "doc_name": doc_name,
                "summary": summary
            }
        
        collection.release()
        return None
        
    except Exception as e:
        logger.error(f"Error getting summary from {collection_name}: {e}")
        return None