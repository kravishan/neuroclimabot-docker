"""
GraphRAG API Routes
FastAPI endpoints for GraphRAG search and visualization
"""

import logging
import json
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException
from pydantic import BaseModel, Field

# Import all helper functions from graphrag_utils
from api.graphrag_utils import (
    get_graphrag_data,
    reload_graphrag_data,
    graphrag_local_search_with_response,
    graphrag_global_search,
    graphrag_drift_search,
    graphrag_basic_search,
    serialize_context,
    sanitize_float
)

logger = logging.getLogger(__name__)


# ============================================================================
# PYDANTIC MODELS (Request/Response)
# ============================================================================

class LocalSearchRequest(BaseModel):
    """Request model for local search"""
    question: str = Field(..., description="Search query")
    community_level: int = Field(default=2, description="Community hierarchy level")
    response_type: str = Field(default="Multiple Paragraphs", description="Response format")
    embedding: list[float] = Field(default=None, description="Pre-computed query embedding (768 or 384 dimensions)")


class GlobalSearchRequest(BaseModel):
    """Request model for global search"""
    question: str = Field(..., description="Search query")
    community_level: int = Field(default=2, description="Community hierarchy level")
    response_type: str = Field(default="Multiple Paragraphs", description="Response format")
    dynamic_community_selection: bool = Field(default=False, description="Use dynamic community selection")


class DriftSearchRequest(BaseModel):
    """Request model for drift search"""
    question: str = Field(..., description="Search query")
    community_level: int = Field(default=2, description="Community hierarchy level")
    response_type: str = Field(default="Multiple Paragraphs", description="Response format")


class BasicSearchRequest(BaseModel):
    """Request model for basic search"""
    question: str = Field(..., description="Search query")


class GraphVisualizationRequest(BaseModel):
    """Request model for graph visualization"""
    source: str = Field(..., description="Document filename or URL")
    max_nodes: int = Field(default=100, description="Maximum nodes to return")
    max_edges: int = Field(default=200, description="Maximum edges to return")


# ============================================================================
# HELPER FUNCTIONS FOR VISUALIZATION
# ============================================================================



# ============================================================================
# API ROUTES SETUP
# ============================================================================

def setup_graphrag_routes(app, get_services_func=None):
    """Setup all GraphRAG API routes"""

    # ========================================================================
    # HEALTH ENDPOINT
    # ========================================================================

    @app.get("/graphrag/health")
    async def graphrag_health():
        """GraphRAG health check - returns master parquet stats"""
        try:
            master_output = Path("./graphrag/output")

            entities_count = 0
            relationships_count = 0
            communities_count = 0
            documents_count = 0

            if master_output.exists():
                if (master_output / "entities.parquet").exists():
                    entities_df = pd.read_parquet(master_output / "entities.parquet")
                    entities_count = len(entities_df)

                if (master_output / "relationships.parquet").exists():
                    relationships_df = pd.read_parquet(master_output / "relationships.parquet")
                    relationships_count = len(relationships_df)

                if (master_output / "communities.parquet").exists():
                    communities_df = pd.read_parquet(master_output / "communities.parquet")
                    communities_count = len(communities_df)

                if (master_output / "documents.parquet").exists():
                    documents_df = pd.read_parquet(master_output / "documents.parquet")
                    documents_count = len(documents_df)

            return {
                "status": "healthy",
                "storage": "Master Parquet Files",
                "path": str(master_output.absolute()),
                "stats": {
                    "total_documents": documents_count,
                    "total_entities": entities_count,
                    "total_relationships": relationships_count,
                    "total_communities": communities_count
                },
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    # ========================================================================
    # LOCAL SEARCH
    # ========================================================================

    @app.post("/graphrag/local-search")
    async def msft_local_search(request: LocalSearchRequest):
        """
        Microsoft GraphRAG local search
        Returns both LLM-generated response and raw context
        """
        try:
            logger.info(f"🔍 Local search: {request.question}")
            if request.embedding:
                logger.info(f"✅ Using pre-computed embedding ({len(request.embedding)} dimensions)")

            # Get both LLM response and context using fast qwen2.5:0.5b model
            llm_response, context, titles = await graphrag_local_search_with_response(
                query=request.question,
                community_level=request.community_level,
                response_type=request.response_type,
                query_embedding=request.embedding
            )

            serialized_context = serialize_context(context)

            return {
                "success": True,
                "result": llm_response,  # LLM-generated answer (using qwen2.5:0.5b)
                "context": serialized_context,  # Raw entities, relationships, text chunks, claims
                "titles": titles,  # Source document titles
                "query": request.question,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Local search error: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "success": False,
                    "error": "Internal server error",
                    "details": str(e)
                }
            )

    # ========================================================================
    # GLOBAL SEARCH
    # ========================================================================

    @app.post("/graphrag/global-search")
    async def msft_global_search(request: GlobalSearchRequest):
        """Microsoft GraphRAG global search - performs community-based global search"""
        try:
            logger.info(f"🌐 Global search: {request.question}")

            response, context = await graphrag_global_search(
                query=request.question,
                dynamic_community_selection=request.dynamic_community_selection,
                community_level=request.community_level,
                response_type=request.response_type
            )

            serialized_context = serialize_context(context)

            return {
                "success": True,
                "result": response,
                "context": serialized_context,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Global search error: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "success": False,
                    "error": "Internal server error",
                    "details": str(e)
                }
            )

    # ========================================================================
    # DRIFT SEARCH
    # ========================================================================

    @app.post("/graphrag/drift-search")
    async def msft_drift_search(request: DriftSearchRequest):
        """Microsoft GraphRAG drift search - hybrid search combining local and global"""
        try:
            logger.info(f"🎯 Drift search: {request.question}")

            response, context = await graphrag_drift_search(
                query=request.question,
                community_level=request.community_level,
                response_type=request.response_type
            )

            serialized_context = serialize_context(context)

            return {
                "success": True,
                "result": response,
                "context": serialized_context,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Drift search error: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "success": False,
                    "error": "Internal server error",
                    "details": str(e)
                }
            )

    # ========================================================================
    # BASIC SEARCH
    # ========================================================================

    @app.post("/graphrag/basic-search")
    async def msft_basic_search(request: BasicSearchRequest):
        """Microsoft GraphRAG basic search - simple text unit search without graph reasoning"""
        try:
            logger.info(f"📝 Basic search: {request.question}")

            response, context = await graphrag_basic_search(
                query=request.question
            )

            serialized_context = serialize_context(context)

            return {
                "success": True,
                "result": response,
                "context": serialized_context,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Basic search error: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "success": False,
                    "error": "Internal server error",
                    "details": str(e)
                }
            )

    # ========================================================================
    # VISUALIZATION ENDPOINT
    # ========================================================================

    @app.post("/graphrag/visualization")
    async def get_graph_visualization(request: GraphVisualizationRequest):
        """Get graph visualization data for a document"""
        try:
            master_output = Path("./graphrag/output")

            if not master_output.exists():
                raise HTTPException(status_code=404, detail="No GraphRAG data available. Process documents first.")

            # Find document by filename or URL
            documents_file = master_output / "documents.parquet"
            if not documents_file.exists():
                raise HTTPException(status_code=404, detail="No documents processed yet")

            docs_df = pd.read_parquet(documents_file)

            # Flexible filename matching
            if request.source.startswith("http://") or request.source.startswith("https://"):
                if "source_url" in docs_df.columns:
                    doc_match = docs_df[docs_df["source_url"] == request.source]
                else:
                    doc_match = pd.DataFrame()
                if doc_match.empty:
                    raise HTTPException(status_code=404, detail=f"Document with URL '{request.source}' not found")
            else:
                doc_match = pd.DataFrame()
                search_column = "title" if "title" in docs_df.columns else "filename" if "filename" in docs_df.columns else None

                if search_column:
                    # Try exact match, then startswith, then contains
                    doc_match = docs_df[docs_df[search_column] == request.source]
                    if doc_match.empty:
                        doc_match = docs_df[docs_df[search_column].str.startswith(request.source)]
                    if doc_match.empty:
                        doc_match = docs_df[docs_df[search_column].str.contains(request.source, case=False, na=False)]

                if doc_match.empty:
                    available_titles = docs_df[search_column].tolist() if search_column else []
                    raise HTTPException(
                        status_code=404,
                        detail=f"Document '{request.source}' not found. Available documents: {available_titles}"
                    )

            doc_record = doc_match.iloc[0]
            document_id = str(doc_record.get("document_id", doc_record.get("id", "")))
            bucket = str(doc_record.get("bucket", "default"))

            # Get text_units for this document
            text_units_file = master_output / "text_units.parquet"
            if not text_units_file.exists():
                raise HTTPException(status_code=404, detail="No text_units data available")

            text_units_df = pd.read_parquet(text_units_file)

            doc_text_units = text_units_df[
                text_units_df['document_ids'].apply(
                    lambda x: document_id in [str(did) for did in (x if isinstance(x, (list, np.ndarray)) else [])]
                )
            ]

            # Extract entity_ids and relationship_ids from text_units
            entity_ids_set = set()
            relationship_ids_set = set()

            for _, text_unit in doc_text_units.iterrows():
                entity_ids = text_unit.get('entity_ids', [])
                if isinstance(entity_ids, (list, np.ndarray)):
                    entity_ids_set.update([str(eid) for eid in entity_ids])

                relationship_ids = text_unit.get('relationship_ids', [])
                if isinstance(relationship_ids, (list, np.ndarray)):
                    relationship_ids_set.update([str(rid) for rid in relationship_ids])

            logger.info(f"📊 Found {len(entity_ids_set)} entities and {len(relationship_ids_set)} relationships for document {document_id[:20]}...")

            # Get all entities for this document first
            entities_file = master_output / "entities.parquet"
            if not entities_file.exists():
                raise HTTPException(status_code=404, detail="No entities data available")

            entities_df = pd.read_parquet(entities_file)
            entity_id_column = "id" if "id" in entities_df.columns else "entity_id"

            # Filter to entities for this document
            entities_for_doc = entities_df[entities_df[entity_id_column].astype(str).isin(entity_ids_set)]

            # Build name->ID mapping to resolve relationship references
            # In GraphRAG, relationships use entity names, not IDs
            entity_name_to_id = {}
            for _, entity in entities_for_doc.iterrows():
                eid = str(entity.get("id", entity.get("entity_id", "")))
                name = str(entity.get("name", entity.get("title", ""))).strip()
                # Store all IDs for this name (in case of duplicates)
                if name not in entity_name_to_id:
                    entity_name_to_id[name] = []
                entity_name_to_id[name].append(eid)

            # Get relationships to determine which entities to include
            relationships_file = master_output / "relationships.parquet"
            if not relationships_file.exists():
                raise HTTPException(status_code=404, detail="No relationships data available")

            relationships_df = pd.read_parquet(relationships_file)
            relationship_id_column = "id" if "id" in relationships_df.columns else "relationship_id"
            relationships_filtered = relationships_df[relationships_df[relationship_id_column].astype(str).isin(relationship_ids_set)]

            # Build relationships list and collect entity IDs that have relationships
            relationships = []
            connected_entity_ids = set()

            for _, row in relationships_filtered.head(request.max_edges).iterrows():
                # Relationships store entity NAMES in source/target fields
                source_name = str(row.get("source", row.get("source_entity", ""))).strip()
                target_name = str(row.get("target", row.get("target_entity", ""))).strip()

                # Resolve names to IDs for internal filtering
                source_ids = entity_name_to_id.get(source_name, [])
                target_ids = entity_name_to_id.get(target_name, [])

                # Use the first ID for each (or handle duplicates as needed)
                source_id = source_ids[0] if source_ids else None
                target_id = target_ids[0] if target_ids else None

                # Only add if both entities exist
                if source_id and target_id:
                    # Add entity IDs to the set of connected entities (for internal filtering)
                    connected_entity_ids.add(source_id)
                    connected_entity_ids.add(target_id)

                    # Send entity NAMES in the response (not IDs)
                    relationships.append({
                        "source_entity": source_name,
                        "target_entity": target_name,
                        "description": str(row.get("description", "")),
                        "strength": sanitize_float(row.get("weight", row.get("strength", 1.0)), default=1.0)
                    })

            logger.info(f"📊 Found {len(connected_entity_ids)} unique entities with relationships from {len(relationships)} relationships")

            # Filter to only entities that appear in relationships (using IDs)
            entities_filtered = entities_for_doc[entities_for_doc[entity_id_column].astype(str).isin(connected_entity_ids)]

            # Build entity ID to name mapping for resolving community members
            entity_id_to_name = {}
            for _, row in entities_filtered.iterrows():
                eid = str(row.get("id", row.get("entity_id", "")))
                name = str(row.get("name", row.get("title", "")))
                entity_id_to_name[eid] = name

            # Send entity data without IDs - just the text fields
            entities = []
            for _, row in entities_filtered.head(request.max_nodes).iterrows():
                entities.append({
                    "name": str(row.get("name", row.get("title", ""))),
                    "type": str(row.get("type", "")),
                    "description": str(row.get("description", "")),
                    "degree": int(row.get("degree", 0))
                })

            # Get community reports first to get summaries
            community_reports_file = master_output / "community_reports.parquet"
            community_summaries = {}

            if community_reports_file.exists():
                community_reports_df = pd.read_parquet(community_reports_file)
                for _, report_row in community_reports_df.iterrows():
                    comm_num = int(report_row.get("community", -1))
                    summary = str(report_row.get("summary", ""))
                    if comm_num >= 0 and summary:
                        community_summaries[comm_num] = summary

            # Get communities
            communities_file = master_output / "communities.parquet"
            communities = []

            if communities_file.exists():
                communities_df = pd.read_parquet(communities_file)

                for _, row in communities_df.iterrows():
                    try:
                        member_entities_raw = row.get("entity_ids", "[]")
                        if isinstance(member_entities_raw, str):
                            member_entities = json.loads(member_entities_raw) if len(member_entities_raw) > 0 else []
                        elif isinstance(member_entities_raw, (list, np.ndarray)):
                            member_entities = list(member_entities_raw)
                        else:
                            member_entities = []

                        if len(member_entities) > 0 and any(str(entity) in entity_ids_set for entity in member_entities):
                            # Resolve entity IDs to names
                            entity_names = []
                            for entity_id in member_entities:
                                entity_name = entity_id_to_name.get(str(entity_id))
                                if entity_name:
                                    entity_names.append(entity_name)

                            # Get summary for this community
                            comm_num = int(row.get("community", 0))
                            summary = community_summaries.get(comm_num, "")

                            communities.append({
                                "community": comm_num,
                                "level": int(row.get("level", 0)),
                                "title": str(row.get("title", "")),
                                "summary": summary,
                                "entity_names": entity_names,
                                "size": len(entity_names)
                            })
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to parse community: {e}")
                        continue

            # Get claims (covariates)
            claims = []
            covariates_file = master_output / "covariates.parquet"

            if covariates_file.exists():
                covariates_df = pd.read_parquet(covariates_file)
                text_unit_ids_set = set(doc_text_units['id'].astype(str).tolist()) if 'id' in doc_text_units.columns else set()

                for _, row in covariates_df.iterrows():
                    text_unit_id = str(row.get("text_unit_id", ""))
                    if text_unit_id in text_unit_ids_set:
                        claims.append({
                            "type": str(row.get("type", row.get("covariate_type", ""))),
                            "description": str(row.get("description", "")),
                            "status": str(row.get("status", "")),
                            "source_text": str(row.get("source_text", ""))
                        })

            # Get detailed community reports with findings
            community_reports = []

            if community_reports_file.exists() and len(communities) > 0:
                community_numbers_set = set(c["community"] for c in communities)

                for _, row in community_reports_df.iterrows():
                    community_num = int(row.get("community", -1))
                    if community_num in community_numbers_set:
                        findings_raw = row.get("findings", [])
                        if isinstance(findings_raw, str):
                            try:
                                findings = json.loads(findings_raw) if len(findings_raw) > 0 else []
                            except:
                                findings = []
                        elif isinstance(findings_raw, (list, np.ndarray)):
                            findings = list(findings_raw)
                        else:
                            findings = []

                        # Only include if there are findings
                        if findings:
                            community_reports.append({
                                "community": community_num,
                                "title": str(row.get("title", "")),
                                "findings": findings
                            })

            logger.info(f"📊 Visualization data: {len(entities)} entities (filtered to those with relationships), "
                       f"{len(relationships)} relationships, {len(communities)} communities, "
                       f"{len(claims)} claims, {len(community_reports)} reports")

            return {
                "status": "success",
                "source": request.source,
                "bucket": bucket,
                "document_id": document_id,
                "all_data": {
                    "entities": entities,
                    "relationships": relationships,
                    "communities": communities,
                    "claims": claims,
                    "community_reports": community_reports
                },
                "metadata": {
                    "entities_count": len(entities),
                    "relationships_count": len(relationships),
                    "communities_count": len(communities),
                    "claims_count": len(claims),
                    "community_reports_count": len(community_reports)
                },
                "timestamp": datetime.now().isoformat()
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Visualization error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # ========================================================================
    # RELOAD ENDPOINT
    # ========================================================================

    @app.post("/graphrag/reload")
    async def reload_graphrag_data_endpoint():
        """Force refresh GraphRAG data cache"""
        try:
            logger.info("🔄 GraphRAG data reload requested")

            reload_graphrag_data()

            master_output = Path("./graphrag/output")
            entities_count = 0
            relationships_count = 0
            communities_count = 0
            documents_count = 0

            if master_output.exists():
                if (master_output / "entities.parquet").exists():
                    entities_count = len(pd.read_parquet(master_output / "entities.parquet"))
                if (master_output / "relationships.parquet").exists():
                    relationships_count = len(pd.read_parquet(master_output / "relationships.parquet"))
                if (master_output / "communities.parquet").exists():
                    communities_count = len(pd.read_parquet(master_output / "communities.parquet"))
                if (master_output / "documents.parquet").exists():
                    documents_count = len(pd.read_parquet(master_output / "documents.parquet"))

            return {
                "status": "success",
                "message": "GraphRAG data reloaded successfully",
                "stats": {
                    "total_documents": documents_count,
                    "total_entities": entities_count,
                    "total_relationships": relationships_count,
                    "total_communities": communities_count
                },
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Reload failed: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "status": "failed",
                    "error": "Failed to reload GraphRAG data",
                    "details": str(e)
                }
            )

    logger.info("✅ GraphRAG routes registered successfully")
