from typing import Any, Dict, List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel, Field

from app.services.external.graphrag_api_client import get_graphrag_api_client
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


class GraphVisualizationRequest(BaseModel):
    doc_name: Optional[str] = Field(None, description="Document name to generate graph for")
    bucket: Optional[str] = Field(None, description="Bucket name to filter by")

    # Legacy support
    tippingPointText: Optional[str] = Field(None, description="Legacy compatibility")
    references: list = Field(default_factory=list, description="Legacy references")
    sources: list = Field(default_factory=list, description="Legacy sources")


class LocalSearchRequest(BaseModel):
    question: str = Field(..., description="Question for local search")
    bucket: Optional[str] = Field(None, description="Bucket to filter by")
    max_entities: int = Field(default=20, description="Maximum entities to return")
    max_relationships: int = Field(default=30, description="Maximum relationships to return")
    max_communities: int = Field(default=10, description="Maximum communities to return")
    context_depth: int = Field(default=1, description="Context expansion depth")
    min_relevance_score: float = Field(default=0.1, description="Minimum relevance score")
    include_community_context: bool = Field(default=True, description="Include community context")
    use_llm_extraction: bool = Field(default=True, description="Use LLM entity extraction")


class ForceGraphResponse(BaseModel):
    success: bool
    nodes: List[Dict[str, Any]] = Field(default_factory=list, description="Graph nodes")
    links: List[Dict[str, Any]] = Field(default_factory=list, description="Graph links")
    communities: List[Dict[str, Any]] = Field(default_factory=list, description="Communities data")
    claims: List[Dict[str, Any]] = Field(default_factory=list, description="Claims data")
    community_reports: List[Dict[str, Any]] = Field(default_factory=list, description="Community reports data")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata with counts and timestamps")
    error: Optional[str] = Field(None, description="Error message if success is False")


class LocalSearchResponse(BaseModel):
    success: bool
    question: str
    search_results: Dict[str, Any] = Field(default_factory=dict)
    context_data: Dict[str, Any] = Field(default_factory=dict)
    answer_elements: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = Field(None, description="Error message if success is False")


@router.post("/local-search", response_model=LocalSearchResponse)
async def graphrag_local_search(request: LocalSearchRequest):
    """
    Perform GraphRAG local search using the /graphrag/local-search endpoint
    """
    try:
        logger.info(f"Local search request: {request.question[:100]}...")
        
        graphrag_client = await get_graphrag_api_client()
        
        # Call the local search endpoint
        result = await graphrag_client.local_search(
            question=request.question,
            bucket=request.bucket,
            max_entities=request.max_entities,
            max_relationships=request.max_relationships,
            max_communities=request.max_communities,
            context_depth=request.context_depth,
            min_relevance_score=request.min_relevance_score,
            include_community_context=request.include_community_context,
            use_llm_extraction=request.use_llm_extraction
        )
        
        if result.get("status") == "success":
            return LocalSearchResponse(
                success=True,
                question=request.question,
                search_results=result.get("search_results", {}),
                context_data=result.get("context_data", {}),
                answer_elements=result.get("answer_elements", {}),
                metadata={
                    **result.get("metadata", {}),
                    "processing_timestamp": datetime.now().isoformat(),
                    "endpoint_used": "graphrag_local_search"
                }
            )
        else:
            return LocalSearchResponse(
                success=False,
                question=request.question,
                error=result.get("error", "Local search failed"),
                metadata={
                    "processing_timestamp": datetime.now().isoformat(),
                    "endpoint_used": "graphrag_local_search"
                }
            )
            
    except Exception as e:
        logger.error(f"Error in local search endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Local search failed: {str(e)}"
        )


@router.post("/force-graph-visualization", response_model=ForceGraphResponse)
async def generate_force_graph_visualization(request: GraphVisualizationRequest):
    try:
        logger.info(f"Force graph visualization request received for doc: {request.doc_name}")
        
        graphrag_client = await get_graphrag_api_client()
        doc_name = _extract_doc_name_from_request(request)
        bucket = _extract_bucket_from_request(request)
        
        if not doc_name:
            return {
                "success": False,
                "error": "No document name provided",
                "nodes": [],
                "links": [],
                "communities": [],
                "claims": [],
                "community_reports": [],
                "metadata": {
                    "entities_count": 0,
                    "relationships_count": 0,
                    "communities_count": 0,
                    "claims_count": 0,
                    "community_reports_count": 0,
                    "processing_timestamp": datetime.now().isoformat(),
                    "doc_name": ""
                }
            }
        
        logger.info(f"Requesting visualization for doc: {doc_name}, bucket: {bucket}")

        result = await graphrag_client.get_visualization_data(
            doc_name=doc_name,
            bucket=bucket or "default"
        )

        # Log the final graph statistics
        if result.get("success"):
            nodes_count = len(result.get("nodes", []))
            links_count = len(result.get("links", []))
            logger.info(f"✅ Graph visualization prepared: {nodes_count} nodes, {links_count} links")

        # Return the simplified structure directly
        return result
            
    except Exception as e:
        logger.error(f"Error in force graph visualization endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Force graph visualization failed: {str(e)}"
        )


class GraphDataExportRequest(BaseModel):
    doc_name: str = Field(..., description="Document name")
    bucket: Optional[str] = Field(None, description="Bucket filter")
    export_format: str = Field(default="react-force-graph", description="Export format")



class GraphSearchRequest(BaseModel):
    query: str = Field(..., description="Search query")
    bucket: Optional[str] = Field(None, description="Bucket to filter by")
    limit: int = Field(default=15, description="Maximum results to return")
    search_type: str = Field(default="local", description="Search type")


@router.post("/search-graph-data")
async def search_graph_data_endpoint(request: GraphSearchRequest):
    try:
        graphrag_client = await get_graphrag_api_client()
        
        graph_items = await graphrag_client.search_graph_data(
            query=request.query,
            search_type=request.search_type,
            limit=request.limit,
            bucket=request.bucket
        )
        
        return {
            "success": True,
            "query": request.query,
            "results": graph_items,
            "count": len(graph_items),
            "search_type": request.search_type,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Graph data search failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "results": []
        }


@router.get("/health")
async def graph_visualization_health_check():
    try:
        graphrag_client = await get_graphrag_api_client()
        is_healthy = await graphrag_client.health_check()
        
        if is_healthy:
            stats = await graphrag_client.get_stats()
            return {
                "status": "healthy",
                "graphrag_api_connected": True,
                "endpoints": {
                    "local_search": "available",
                    "visualization": "available",
                    "search_graph_data": "available"
                },
                "visualization_optimization": {
                    "react_force_graph_compatible": True,
                    "communities_excluded_by_default": True,
                    "intelligent_link_generation": True,
                    "semantic_relationship_detection": True
                },
                "supported_libraries": ["react-force-graph-2d", "react-force-graph-3d"],
                "configuration": stats.get("local_search_config", {}),
                "visualization_config": stats.get("visualization_config", {}),
                "performance_stats": stats.get("performance", {})
            }
        else:
            return {
                "status": "unhealthy",
                "graphrag_api_connected": False,
                "error": "GraphRAG API connection failed"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }




def _transform_to_cytoscape(graph_data: Dict[str, Any]) -> Dict[str, Any]:
    """Transform graph data to Cytoscape.js format"""
    elements = []
    
    for node in graph_data.get("nodes", []):
        elements.append({
            "data": {
                "id": node.get("id"),
                "label": node.get("name"),
                "type": node.get("type"),
                "description": node.get("description", "")
            },
            "style": {
                "background-color": node.get("color", "#999"),
                "width": node.get("val", 20),
                "height": node.get("val", 20)
            }
        })
    
    for link in graph_data.get("links", []):
        elements.append({
            "data": {
                "id": f"{link.get('source')}-{link.get('target')}",
                "source": link.get("source"),
                "target": link.get("target"),
                "label": link.get("type", ""),
                "description": link.get("description", "")
            },
            "style": {
                "line-color": link.get("color", "#999")
            }
        })
    
    return {"elements": elements}


def _transform_to_vis_network(graph_data: Dict[str, Any]) -> Dict[str, Any]:
    """Transform graph data to vis-network format"""
    nodes = []
    edges = []
    
    for node in graph_data.get("nodes", []):
        nodes.append({
            "id": node.get("id"),
            "label": node.get("name"),
            "title": node.get("description", ""),
            "color": node.get("color", "#999"),
            "size": node.get("val", 20),
            "group": node.get("type", "default")
        })
    
    for i, link in enumerate(graph_data.get("links", [])):
        edges.append({
            "id": i,
            "from": link.get("source"),
            "to": link.get("target"),
            "label": link.get("type", ""),
            "title": link.get("description", ""),
            "color": link.get("color", "#999"),
            "arrows": "to"
        })
    
    return {"nodes": nodes, "edges": edges}


def _transform_to_d3(graph_data: Dict[str, Any]) -> Dict[str, Any]:
    """Transform graph data to D3.js format"""
    return {
        "nodes": graph_data.get("nodes", []),
        "links": graph_data.get("links", []),
        "metadata": graph_data.get("stats", {})
    }


def _extract_doc_name_from_request(request: GraphVisualizationRequest) -> Optional[str]:
    if request.doc_name:
        return request.doc_name.strip()
    
    if request.sources:
        first_source = request.sources[0]
        if isinstance(first_source, dict):
            doc_name = first_source.get("doc_name")
            if doc_name:
                return doc_name.strip()
    
    if request.references:
        if isinstance(request.references, list) and request.references:
            first_ref = request.references[0]
            if isinstance(first_ref, dict):
                doc_name = first_ref.get("doc_name")
                if doc_name:
                    return doc_name.strip()
    
    if request.tippingPointText:
        mock_doc_name = request.tippingPointText[:50].strip()
        return f"legacy_{mock_doc_name}"
    
    return None


def _extract_bucket_from_request(request: GraphVisualizationRequest) -> Optional[str]:
    if request.bucket:
        return request.bucket.strip()
    
    if request.sources:
        first_source = request.sources[0]
        if isinstance(first_source, dict):
            bucket = first_source.get("bucket")
            if bucket:
                return bucket.strip()
    
    return None


