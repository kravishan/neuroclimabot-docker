"""
GraphRAG Utility Functions
Helper functions for data loading, processing, and search operations
"""

import logging
import json
import os
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path
from graphrag import api

logger = logging.getLogger(__name__)


# ============================================================================
# DATA LOADING FROM MASTER GRAPHRAG OUTPUT
# ============================================================================

def load_graphrag_data_from_master() -> Dict[str, Any]:
    """
    Load GraphRAG data from master parquet files

    Returns:
        Dictionary containing config, entities, communities, community_reports,
        text_units, relationships, documents DataFrames
    """
    try:
        master_output = Path("./graphrag/output")

        if not master_output.exists():
            logger.warning(f"⚠️  Master GraphRAG output not found: {master_output}")
            logger.warning(f"⚠️  Creating empty directory - process a document first!")
            master_output.mkdir(parents=True, exist_ok=True)

        # Load parquet files
        entities_file = master_output / "entities.parquet"
        relationships_file = master_output / "relationships.parquet"
        communities_file = master_output / "communities.parquet"
        community_reports_file = master_output / "community_reports.parquet"
        text_units_file = master_output / "text_units.parquet"
        documents_file = master_output / "documents.parquet"

        # Read files with fallback to empty DataFrames
        entities_df = pd.read_parquet(entities_file) if entities_file.exists() else pd.DataFrame()
        relationships_df = pd.read_parquet(relationships_file) if relationships_file.exists() else pd.DataFrame()
        communities_df = pd.read_parquet(communities_file) if communities_file.exists() else pd.DataFrame()
        community_reports_df = pd.read_parquet(community_reports_file) if community_reports_file.exists() else pd.DataFrame()
        text_units_df = pd.read_parquet(text_units_file) if text_units_file.exists() else pd.DataFrame()
        documents_df = pd.read_parquet(documents_file) if documents_file.exists() else pd.DataFrame()

        logger.info(f"📊 Loaded GraphRAG data from master parquet files:")
        logger.info(f"  Entities: {len(entities_df)}")
        logger.info(f"  Relationships: {len(relationships_df)}")
        logger.info(f"  Communities: {len(communities_df)}")
        logger.info(f"  Text Units: {len(text_units_df)}")
        logger.info(f"  Documents: {len(documents_df)}")

        # Check for embeddings
        has_entity_embeddings = 'description_embedding' in entities_df.columns if not entities_df.empty else False
        has_text_embeddings = 'text_embedding' in text_units_df.columns if not text_units_df.empty else False

        if has_entity_embeddings:
            logger.info(f"✅ Entity embeddings present (description_embedding)")
        else:
            logger.warning(f"⚠️  No entity embeddings - add GRAPHRAG_EMBEDDING_MODEL_* to .env")

        if has_text_embeddings:
            logger.info(f"✅ Text embeddings present (text_embedding)")
        else:
            logger.warning(f"⚠️  No text embeddings - add GRAPHRAG_EMBEDDING_MODEL_* to .env")

        # Convert numpy arrays to lists
        if not text_units_df.empty and 'document_ids' in text_units_df.columns:
            text_units_df['document_ids'] = text_units_df['document_ids'].apply(
                lambda x: list(x) if hasattr(x, '__iter__') and not isinstance(x, str) else ([x] if pd.notna(x) else [])
            )

        if not text_units_df.empty:
            if 'entity_ids' in text_units_df.columns:
                text_units_df['entity_ids'] = text_units_df['entity_ids'].apply(
                    lambda x: list(x) if hasattr(x, '__iter__') and not isinstance(x, str) else []
                )
            if 'relationship_ids' in text_units_df.columns:
                text_units_df['relationship_ids'] = text_units_df['relationship_ids'].apply(
                    lambda x: list(x) if hasattr(x, '__iter__') and not isinstance(x, str) else []
                )
            if 'covariate_ids' in text_units_df.columns:
                text_units_df['covariate_ids'] = text_units_df['covariate_ids'].apply(
                    lambda x: list(x) if hasattr(x, '__iter__') and not isinstance(x, str) else []
                )

        # Ensure human_readable_id column exists in text_units
        if not text_units_df.empty and 'human_readable_id' not in text_units_df.columns:
            if 'id' in text_units_df.columns:
                text_units_df['human_readable_id'] = text_units_df['id']
                logger.info("✅ Added human_readable_id column to text_units (copied from id)")
            else:
                logger.warning("⚠️ text_units missing both 'id' and 'human_readable_id' columns")

        # Normalize documents schema
        if not documents_df.empty:
            if 'title' not in documents_df.columns:
                if 'filename' in documents_df.columns:
                    documents_df['title'] = documents_df['filename']
                    logger.info("✅ Added title column to documents (copied from filename)")
                elif 'id' in documents_df.columns:
                    documents_df['title'] = documents_df['id']
                    logger.info("✅ Added title column to documents (copied from id)")
                else:
                    logger.warning("⚠️ documents missing 'filename' and 'id' columns, cannot create title")

            if 'document_id' not in documents_df.columns and 'id' in documents_df.columns:
                documents_df['document_id'] = documents_df['id']
                logger.info("✅ Added document_id column to documents (copied from id)")

            if 'filename' not in documents_df.columns and 'title' in documents_df.columns:
                documents_df['filename'] = documents_df['title']
                logger.info("✅ Added filename column to documents (copied from title)")

            if 'source_url' not in documents_df.columns:
                documents_df['source_url'] = ""
                logger.info("✅ Added empty source_url column to documents")

            if 'bucket' not in documents_df.columns:
                documents_df['bucket'] = "default"
                logger.info("✅ Added bucket column to documents (default)")

        config = _create_mock_config()

        logger.info("✅ Master GraphRAG data loaded successfully")

        return {
            "config": config,
            "entities": entities_df,
            "communities": communities_df,
            "community_reports": community_reports_df,
            "text_units": text_units_df,
            "relationships": relationships_df,
            "documents": documents_df
        }

    except Exception as e:
        logger.error(f"❌ Failed to load GraphRAG data: {e}")
        raise


def _create_mock_config():
    """Create GraphRAG configuration from environment variables"""
    config = {
        "models": {
            "default_chat_model": {
                "type": "openai_chat",
                "api_base": os.getenv("GRAPHRAG_QUERY_CHAT_MODEL_API_BASE", "https://api.openai.com/v1"),
                "auth_type": "api_key",
                "api_key": os.getenv("GRAPHRAG_QUERY_CHAT_MODEL_API_KEY", os.getenv("OPENAI_API_KEY", "mock-key")),
                "model": os.getenv("GRAPHRAG_QUERY_CHAT_MODEL", "gpt-4"),
                "encoding_model": "cl100k_base",
                "max_tokens": 4000,
                "concurrent_requests": 1,
                "async_mode": "asyncio",
            },
            "query_chat_model": {
                "type": "openai_chat",
                "api_base": os.getenv("GRAPHRAG_QUERY_CHAT_MODEL_API_BASE", "https://api.openai.com/v1"),
                "auth_type": "api_key",
                "api_key": os.getenv("GRAPHRAG_QUERY_CHAT_MODEL_API_KEY", os.getenv("OPENAI_API_KEY", "mock-key")),
                "model": os.getenv("GRAPHRAG_QUERY_CHAT_MODEL", "gpt-4"),
                "encoding_model": "cl100k_base",
                "max_tokens": 4000,
                "concurrent_requests": 1,
                "async_mode": "asyncio",
            },
            "default_embedding_model": {
                "type": "openai_embedding",
                "api_base": os.getenv("GRAPHRAG_QUERY_EMBEDDING_MODEL_API_BASE", "https://api.openai.com/v1"),
                "auth_type": "api_key",
                "api_key": os.getenv("GRAPHRAG_QUERY_EMBEDDING_MODEL_API_KEY", os.getenv("OPENAI_API_KEY", "mock-key")),
                "model": os.getenv("GRAPHRAG_QUERY_EMBEDDING_MODEL", "text-embedding-3-small"),
                "encoding_model": "cl100k_base",
            }
        },
        "vector_store": {
            "default_vector_store": {
                "type": "lancedb",
                "db_uri": "./graphrag/output/lancedb",
                "container_name": "default",
                "overwrite": False
            }
        },
        "local_search": {
            "chat_model_id": "query_chat_model",
            "embedding_model_id": "default_embedding_model",
            "prompt": "prompts/local_search_system_prompt.txt",
        },
        "global_search": {
            "chat_model_id": "query_chat_model",
            "map_prompt": "prompts/global_search_map_system_prompt.txt",
            "reduce_prompt": "prompts/global_search_reduce_system_prompt.txt",
            "knowledge_prompt": "prompts/global_search_knowledge_system_prompt.txt",
        },
        "drift_search": {
            "chat_model_id": "query_chat_model",
            "embedding_model_id": "default_embedding_model",
            "prompt": "prompts/drift_search_system_prompt.txt",
            "reduce_prompt": "prompts/drift_search_reduce_prompt.txt",
        },
        "basic_search": {
            "chat_model_id": "query_chat_model",
            "embedding_model_id": "default_embedding_model",
            "prompt": "prompts/basic_search_system_prompt.txt",
        },
        "encoding_model": "cl100k_base",
    }

    logger.info("✅ Created GraphRAG config matching settings.yaml structure")
    logger.info(f"   Chat model: {config['models']['query_chat_model']['model']}")
    logger.info(f"   Chat API base: {config['models']['query_chat_model']['api_base']}")
    logger.info(f"   Embedding model: {config['models']['default_embedding_model']['model']}")
    logger.info(f"   Embedding API base: {config['models']['default_embedding_model']['api_base']}")
    logger.info(f"   Vector store: LanceDB at {config['vector_store']['default_vector_store']['db_uri']}")
    return config


# ============================================================================
# GRAPHRAG DATA CACHE
# ============================================================================

_graphrag_data_cache = None
_cache_timestamp = None
_cache_ttl_seconds = 300  # Cache for 5 minutes


def get_graphrag_data(force_reload: bool = False) -> Dict[str, Any]:
    """Get GraphRAG data with lazy loading and caching"""
    global _graphrag_data_cache, _cache_timestamp

    if not force_reload and _graphrag_data_cache is not None:
        if _cache_timestamp is not None:
            cache_age = (datetime.now() - _cache_timestamp).total_seconds()
            if cache_age < _cache_ttl_seconds:
                logger.debug(f"Using cached GraphRAG data (age: {cache_age:.1f}s)")
                return _graphrag_data_cache

    logger.info("📊 Loading GraphRAG data from master output...")
    try:
        data = load_graphrag_data_from_master()
        _graphrag_data_cache = data
        _cache_timestamp = datetime.now()
        logger.info("✅ GraphRAG data loaded and cached successfully")
        return data
    except Exception as e:
        logger.error(f"❌ Failed to load GraphRAG data: {e}")
        if _graphrag_data_cache is not None:
            logger.warning("⚠️ Using stale cached data as fallback")
            return _graphrag_data_cache
        raise


def clear_graphrag_cache():
    """Clear the GraphRAG data cache to force reload on next access"""
    global _graphrag_data_cache, _cache_timestamp
    _graphrag_data_cache = None
    _cache_timestamp = None
    logger.info("🗑️ GraphRAG data cache cleared")


def reload_graphrag_data():
    """Reload GraphRAG data from parquet files (clears cache and reloads)"""
    try:
        logger.info("🔄 Reloading GraphRAG data...")
        clear_graphrag_cache()
        data = get_graphrag_data(force_reload=True)
        logger.info("✅ GraphRAG data reloaded successfully")
        return data
    except Exception as e:
        logger.error(f"❌ Failed to reload GraphRAG data: {e}")
        raise


# ============================================================================
# SEARCH FUNCTIONS
# ============================================================================

async def graphrag_local_search_with_response(
    query: str,
    community_level: int = 2,
    response_type: str = "One Paragraphs",
    query_embedding: List[float] = None
) -> Tuple[str, Dict[str, Any], List[str]]:
    """
    Get GraphRAG local search with both LLM response and context
    Uses fast qwen2.5:0.5b model for response generation

    Args:
        query: Search query text
        community_level: Community hierarchy level
        response_type: Response format
        query_embedding: Optional pre-computed query embedding (saves API call)
    """
    try:
        logger.info(f"🔍 Local search query: {query}")

        graphrag_data = get_graphrag_data()
        logger.info(f"📊 Data loaded - Entities: {len(graphrag_data['entities'])}, "
                   f"Relationships: {len(graphrag_data['relationships'])}, "
                   f"Text units: {len(graphrag_data['text_units'])}")

        # Use fast, small model for response generation
        config = graphrag_data["config"].copy()
        if "models" in config and "query_chat_model" in config["models"]:
            config["models"]["query_chat_model"]["model"] = "qwen2.5:0.5b"
            config["models"]["query_chat_model"]["max_tokens"] = 2000

        if query_embedding:
            logger.info(f"✅ Pre-computed embedding provided ({len(query_embedding)} dims)")
            logger.warning("⚠️ Note: GraphRAG library doesn't support pre-computed embeddings yet - will generate embedding internally")

        logger.info("🔨 Building context from knowledge graph and generating LLM response...")
        llm_response, context = await api.local_search(
            config=config,
            entities=graphrag_data["entities"],
            communities=graphrag_data["communities"],
            community_reports=graphrag_data["community_reports"],
            text_units=graphrag_data["text_units"],
            relationships=graphrag_data["relationships"],
            covariates=graphrag_data.get("covariates"),
            community_level=community_level,
            response_type=response_type,
            query=query,
        )

        logger.info(f"✅ Context and LLM response retrieved")

        # Add document names to all items in the context
        context = add_document_names_to_context(
            context,
            graphrag_data["text_units"],
            graphrag_data["documents"]
        )

        # Filter context by query to remove irrelevant results
        context = filter_context_by_query(context, query)

        titles = extract_document_titles_from_context(
            context.get("sources", pd.DataFrame()),
            graphrag_data["text_units"],
            graphrag_data["documents"]
        )

        return llm_response, context, titles

    except Exception as e:
        logger.error(f"❌ Local search failed: {e}")
        logger.error(f"❌ Error type: {type(e).__name__}")
        import traceback
        logger.error(f"❌ Traceback:\n{traceback.format_exc()}")
        raise


async def graphrag_global_search(
    query: str,
    dynamic_community_selection: bool = False,
    community_level: int = 2,
    response_type: str = "Multiple Paragraphs"
) -> Tuple[str, Dict[str, Any]]:
    """Perform global search using Microsoft GraphRAG API"""
    try:
        logger.info(f"🌐 Global search query: {query}")

        graphrag_data = get_graphrag_data()

        response, context = await api.global_search(
            config=graphrag_data["config"],
            entities=graphrag_data["entities"],
            communities=graphrag_data["communities"],
            community_reports=graphrag_data["community_reports"],
            community_level=community_level,
            dynamic_community_selection=dynamic_community_selection,
            response_type=response_type,
            query=query,
        )

        logger.info(f"✅ Global search completed")
        return response, context

    except Exception as e:
        logger.error(f"❌ Global search failed: {e}")
        raise


async def graphrag_drift_search(
    query: str,
    community_level: int = 2,
    response_type: str = "Multiple Paragraphs"
) -> Tuple[str, Dict[str, Any]]:
    """Perform drift search using Microsoft GraphRAG API"""
    try:
        logger.info(f"🎯 Drift search query: {query}")

        graphrag_data = get_graphrag_data()

        response, context = await api.drift_search(
            config=graphrag_data["config"],
            entities=graphrag_data["entities"],
            communities=graphrag_data["communities"],
            community_reports=graphrag_data["community_reports"],
            text_units=graphrag_data["text_units"],
            relationships=graphrag_data["relationships"],
            community_level=community_level,
            response_type=response_type,
            query=query,
        )

        logger.info(f"✅ Drift search completed")
        return response, context

    except Exception as e:
        logger.error(f"❌ Drift search failed: {e}")
        raise


async def graphrag_basic_search(query: str) -> Tuple[str, Dict[str, Any]]:
    """Perform basic search using Microsoft GraphRAG API"""
    try:
        logger.info(f"📝 Basic search query: {query}")

        graphrag_data = get_graphrag_data()

        response, context = await api.basic_search(
            config=graphrag_data["config"],
            text_units=graphrag_data["text_units"],
            query=query,
        )

        logger.info(f"✅ Basic search completed")
        return response, context

    except Exception as e:
        logger.error(f"❌ Basic search failed: {e}")
        raise


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def add_document_names_to_context(
    context: Dict[str, Any],
    text_units_df: pd.DataFrame,
    documents_df: pd.DataFrame
) -> Dict[str, Any]:
    """
    Add document names to entities, relationships, sources, and claims in the context
    This helps identify which document each item came from
    """
    try:
        if text_units_df.empty or documents_df.empty:
            logger.warning("⚠️ Cannot add document names: text_units or documents are empty")
            return context

        # Create document lookup: document_id -> document_name
        # For news articles with URLs, use the source_url instead of title/filename
        doc_id_to_name = {}
        doc_id_column = 'document_id' if 'document_id' in documents_df.columns else 'id'
        has_source_url = 'source_url' in documents_df.columns

        for _, doc in documents_df.iterrows():
            doc_id = str(doc.get(doc_id_column, ''))

            # Check if this is a news article with a URL
            if has_source_url:
                source_url = str(doc.get('source_url', '')).strip()
                # If source_url exists and is a valid URL, use it
                if source_url and (source_url.startswith('http://') or source_url.startswith('https://')):
                    doc_id_to_name[doc_id] = source_url
                    continue

            # Otherwise, use title/filename (for PDFs and other documents)
            doc_name = str(doc.get('title', doc.get('filename', '')))
            # Remove file extension (e.g., .txt, .pdf, .p, etc.)
            doc_name = os.path.splitext(doc_name)[0]
            # Replace underscores with spaces for better readability
            doc_name = doc_name.replace('_', ' ')
            doc_id_to_name[doc_id] = doc_name

        # Build comprehensive mappings from text_units
        # Map: text_unit_id -> document_names
        text_unit_to_docs = {}
        # Map: entity_id -> document_names
        entity_id_to_docs = {}
        # Map: relationship_id -> document_names
        relationship_id_to_docs = {}

        for _, text_unit in text_units_df.iterrows():
            tu_id = str(text_unit.get('id', ''))
            doc_ids = text_unit.get('document_ids', [])

            # Get document names for this text unit
            if isinstance(doc_ids, (list, np.ndarray)) and len(doc_ids) > 0:
                doc_names = [doc_id_to_name.get(str(did), '') for did in doc_ids]
                doc_names = [name for name in doc_names if name]  # Filter out empty names

                if doc_names:
                    text_unit_to_docs[tu_id] = doc_names

                    # Map entity IDs to documents
                    entity_ids = text_unit.get('entity_ids', [])
                    if isinstance(entity_ids, (list, np.ndarray)):
                        for eid in entity_ids:
                            eid_str = str(eid)
                            if eid_str not in entity_id_to_docs:
                                entity_id_to_docs[eid_str] = set()
                            entity_id_to_docs[eid_str].update(doc_names)

                    # Map relationship IDs to documents
                    rel_ids = text_unit.get('relationship_ids', [])
                    if isinstance(rel_ids, (list, np.ndarray)):
                        for rid in rel_ids:
                            rid_str = str(rid)
                            if rid_str not in relationship_id_to_docs:
                                relationship_id_to_docs[rid_str] = set()
                            relationship_id_to_docs[rid_str].update(doc_names)

        logger.info(f"📊 Built mappings: {len(entity_id_to_docs)} entities, {len(relationship_id_to_docs)} relationships, {len(text_unit_to_docs)} text units")

        # Add document names to entities
        entities_df = context.get("entities", pd.DataFrame())
        if isinstance(entities_df, pd.DataFrame) and not entities_df.empty:
            entities_df = entities_df.copy()

            def get_entity_docs(row):
                """Get document names for an entity"""
                # Try to match by ID first
                entity_id = str(row.get('id', ''))
                if entity_id in entity_id_to_docs:
                    return list(entity_id_to_docs[entity_id])

                # If no match by ID, try to infer from text units by checking all text units
                # This is a fallback for cases where IDs don't match
                entity_name = str(row.get('entity', row.get('name', ''))).upper()
                if entity_name:
                    # Search through text_units to find which documents mention this entity
                    docs_set = set()
                    for _, tu in text_units_df.iterrows():
                        tu_text = str(tu.get('text', '')).upper()
                        if entity_name in tu_text:
                            tu_id = str(tu.get('id', ''))
                            if tu_id in text_unit_to_docs:
                                docs_set.update(text_unit_to_docs[tu_id])
                    if docs_set:
                        return list(docs_set)

                return []

            entities_df['document_names'] = entities_df.apply(get_entity_docs, axis=1)
            context["entities"] = entities_df
            entities_with_docs = entities_df['document_names'].apply(lambda x: len(x) > 0).sum()
            logger.info(f"✅ Added document names to entities ({entities_with_docs}/{len(entities_df)} have documents)")

        # Add document names to relationships
        relationships_df = context.get("relationships", pd.DataFrame())
        if isinstance(relationships_df, pd.DataFrame) and not relationships_df.empty:
            relationships_df = relationships_df.copy()

            def get_relationship_docs(row):
                """Get document names for a relationship"""
                # Try to match by ID first
                rel_id = str(row.get('id', ''))
                if rel_id in relationship_id_to_docs:
                    return list(relationship_id_to_docs[rel_id])

                # Fallback: infer from source and target entities
                source = str(row.get('source', '')).upper()
                target = str(row.get('target', '')).upper()
                if source and target:
                    docs_set = set()
                    for _, tu in text_units_df.iterrows():
                        tu_text = str(tu.get('text', '')).upper()
                        # If both source and target are mentioned in the text unit
                        if source in tu_text and target in tu_text:
                            tu_id = str(tu.get('id', ''))
                            if tu_id in text_unit_to_docs:
                                docs_set.update(text_unit_to_docs[tu_id])
                    if docs_set:
                        return list(docs_set)

                return []

            relationships_df['document_names'] = relationships_df.apply(get_relationship_docs, axis=1)
            context["relationships"] = relationships_df
            rels_with_docs = relationships_df['document_names'].apply(lambda x: len(x) > 0).sum()
            logger.info(f"✅ Added document names to relationships ({rels_with_docs}/{len(relationships_df)} have documents)")

        # Add document names to sources
        sources_df = context.get("sources", pd.DataFrame())
        if isinstance(sources_df, pd.DataFrame) and not sources_df.empty:
            sources_df = sources_df.copy()
            # Match sources with text_units by text content
            if 'text' in sources_df.columns and 'text' in text_units_df.columns:
                text_units_copy = text_units_df.copy()
                sources_df['text_normalized'] = sources_df['text'].str.strip()
                text_units_copy['text_normalized'] = text_units_copy['text'].str.strip()

                # Create text -> document_names mapping
                text_to_docs = {}
                for _, tu in text_units_copy.iterrows():
                    text_norm = tu.get('text_normalized', '')
                    tu_id = str(tu.get('id', ''))
                    if text_norm and tu_id in text_unit_to_docs:
                        text_to_docs[text_norm] = text_unit_to_docs[tu_id]

                sources_df['document_names'] = sources_df['text_normalized'].apply(
                    lambda text: text_to_docs.get(text, [])
                )
                sources_df = sources_df.drop(columns=['text_normalized'])
            else:
                sources_df['document_names'] = [[] for _ in range(len(sources_df))]

            context["sources"] = sources_df
            sources_with_docs = sources_df['document_names'].apply(lambda x: len(x) > 0).sum()
            logger.info(f"✅ Added document names to sources ({sources_with_docs}/{len(sources_df)} have documents)")

        # Add document names to claims
        claims_df = context.get("claims", pd.DataFrame())
        if isinstance(claims_df, pd.DataFrame) and not claims_df.empty:
            claims_df = claims_df.copy()
            if 'text_unit_id' in claims_df.columns:
                claims_df['document_names'] = claims_df['text_unit_id'].apply(
                    lambda tu_id: text_unit_to_docs.get(str(tu_id), [])
                )
            else:
                claims_df['document_names'] = [[] for _ in range(len(claims_df))]
            context["claims"] = claims_df
            claims_with_docs = claims_df['document_names'].apply(lambda x: len(x) > 0).sum() if len(claims_df) > 0 else 0
            logger.info(f"✅ Added document names to claims ({claims_with_docs}/{len(claims_df)} have documents)")

        # Add document names to reports (community reports)
        reports_df = context.get("reports", pd.DataFrame())
        if isinstance(reports_df, pd.DataFrame) and not reports_df.empty:
            reports_df = reports_df.copy()
            if not entities_df.empty and 'document_names' in entities_df.columns:
                # For each report, find which documents are mentioned in its entities
                def get_report_documents(report_content):
                    """Extract document names from entities mentioned in report"""
                    if not isinstance(report_content, str):
                        return []
                    # Find entities mentioned in the report content
                    mentioned_docs = set()
                    for _, entity in entities_df.iterrows():
                        entity_name = str(entity.get('entity', ''))
                        if entity_name and entity_name.upper() in report_content.upper():
                            doc_names = entity.get('document_names', [])
                            if isinstance(doc_names, list):
                                mentioned_docs.update(doc_names)
                    return list(mentioned_docs)

                reports_df['document_names'] = reports_df['content'].apply(get_report_documents)
            else:
                reports_df['document_names'] = [[] for _ in range(len(reports_df))]
            context["reports"] = reports_df
            reports_with_docs = reports_df['document_names'].apply(lambda x: len(x) > 0).sum() if len(reports_df) > 0 else 0
            logger.info(f"✅ Added document names to reports ({reports_with_docs}/{len(reports_df)} have documents)")

        return context

    except Exception as e:
        logger.error(f"❌ Error adding document names to context: {e}")
        import traceback
        logger.error(f"❌ Traceback:\n{traceback.format_exc()}")
        return context


def filter_context_by_query(context: Dict[str, Any], query: str) -> Dict[str, Any]:
    """
    Filter context to only include results relevant to the query
    This helps when embeddings are missing and all communities are returned
    """
    try:
        # Extract query keywords (lowercase, remove common words)
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been', 'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'about', 'what', 'which', 'who', 'when', 'where', 'why', 'how'}
        query_keywords = set(word.lower() for word in query.split() if word.lower() not in stop_words and len(word) > 2)

        if not query_keywords:
            logger.info("⚠️ No meaningful keywords in query, returning unfiltered results")
            return context

        logger.info(f"🔍 Filtering results by query keywords: {query_keywords}")

        # Filter reports
        reports_df = context.get("reports", pd.DataFrame())
        if isinstance(reports_df, pd.DataFrame) and not reports_df.empty:
            def is_relevant_report(row):
                text = f"{row.get('title', '')} {row.get('content', '')}".lower()
                # A report is relevant if it mentions any query keyword
                return any(keyword in text for keyword in query_keywords)

            mask = reports_df.apply(is_relevant_report, axis=1)
            relevant_count = mask.sum()
            total_count = len(reports_df)

            if relevant_count < total_count:
                context["reports"] = reports_df[mask].copy()
                logger.info(f"🔍 Filtered reports: {relevant_count}/{total_count} relevant to query")

        # Filter entities
        entities_df = context.get("entities", pd.DataFrame())
        if isinstance(entities_df, pd.DataFrame) and not entities_df.empty:
            def is_relevant_entity(row):
                text = f"{row.get('entity', '')} {row.get('description', '')}".lower()
                return any(keyword in text for keyword in query_keywords)

            mask = entities_df.apply(is_relevant_entity, axis=1)
            relevant_entity_ids = set(entities_df[mask]['id'].astype(str).tolist()) if 'id' in entities_df.columns else set()

            relevant_count = mask.sum()
            total_count = len(entities_df)

            if relevant_count < total_count and relevant_count > 0:
                context["entities"] = entities_df[mask].copy()
                logger.info(f"🔍 Filtered entities: {relevant_count}/{total_count} relevant to query")
            else:
                relevant_entity_ids = set(entities_df['id'].astype(str).tolist()) if 'id' in entities_df.columns else set()
        else:
            relevant_entity_ids = set()

        # Filter relationships (only keep those connecting relevant entities)
        relationships_df = context.get("relationships", pd.DataFrame())
        if isinstance(relationships_df, pd.DataFrame) and not relationships_df.empty and relevant_entity_ids:
            # Get entity names from relevant entities
            entities_df = context.get("entities", pd.DataFrame())
            if isinstance(entities_df, pd.DataFrame) and not entities_df.empty and 'entity' in entities_df.columns:
                relevant_entity_names = set(entities_df['entity'].str.upper().tolist())

                def is_relevant_relationship(row):
                    source = str(row.get('source', '')).upper()
                    target = str(row.get('target', '')).upper()
                    # Keep relationship if either source or target is a relevant entity
                    return source in relevant_entity_names or target in relevant_entity_names

                mask = relationships_df.apply(is_relevant_relationship, axis=1)
                relevant_count = mask.sum()
                total_count = len(relationships_df)

                if relevant_count < total_count and relevant_count > 0:
                    context["relationships"] = relationships_df[mask].copy()
                    logger.info(f"🔍 Filtered relationships: {relevant_count}/{total_count} relevant to query")

        # Filter sources (text chunks)
        sources_df = context.get("sources", pd.DataFrame())
        if isinstance(sources_df, pd.DataFrame) and not sources_df.empty:
            def is_relevant_source(row):
                text = str(row.get('text', '')).lower()
                return any(keyword in text for keyword in query_keywords)

            mask = sources_df.apply(is_relevant_source, axis=1)
            relevant_count = mask.sum()
            total_count = len(sources_df)

            if relevant_count < total_count and relevant_count > 0:
                context["sources"] = sources_df[mask].copy()
                logger.info(f"🔍 Filtered sources: {relevant_count}/{total_count} relevant to query")

        return context

    except Exception as e:
        logger.error(f"❌ Error filtering context: {e}")
        import traceback
        logger.error(f"❌ Traceback:\n{traceback.format_exc()}")
        return context


def extract_document_titles_from_context(
    sources_df: pd.DataFrame,
    text_units_df: pd.DataFrame,
    documents_df: pd.DataFrame
) -> List[str]:
    """Extract unique document titles from search context (only relevant sources)"""
    if sources_df.empty or text_units_df.empty or documents_df.empty:
        return []

    try:
        sources_df = sources_df.copy()
        text_units = text_units_df.copy()
        documents = documents_df.copy()

        # Match sources with text_units by text content
        if 'text' in sources_df.columns and 'text' in text_units.columns:
            sources_df['text_normalized'] = sources_df['text'].str.strip()
            text_units['text_normalized'] = text_units['text'].str.strip()

            merged = sources_df.merge(
                text_units[['text_normalized', 'document_ids']],
                on='text_normalized',
                how='inner'
            )

            all_doc_ids = set()
            for doc_ids_list in merged['document_ids'].values:
                if isinstance(doc_ids_list, (list, np.ndarray)) and len(doc_ids_list) > 0:
                    all_doc_ids.update([str(did) for did in doc_ids_list])

            if all_doc_ids:
                doc_id_column = 'document_id' if 'document_id' in documents.columns else 'id'
                matching_docs = documents[documents[doc_id_column].astype(str).isin(all_doc_ids)]
                if not matching_docs.empty:
                    titles = []
                    has_source_url = 'source_url' in matching_docs.columns

                    for _, doc in matching_docs.iterrows():
                        # For news articles with URLs, use source_url
                        if has_source_url:
                            source_url = str(doc.get('source_url', '')).strip()
                            if source_url and (source_url.startswith('http://') or source_url.startswith('https://')):
                                titles.append(source_url)
                                continue

                        # For PDFs and other documents, use title/filename
                        if 'title' in matching_docs.columns:
                            title = str(doc.get('title', ''))
                            # Remove file extension and clean up
                            title = os.path.splitext(title)[0].replace('_', ' ')
                            if title:
                                titles.append(title)

                    logger.info(f"✅ Extracted {len(titles)} document identifiers from {len(sources_df)} sources")
                    return list(set(titles))

        # Fallback: if matching failed but we have very few sources, don't return all titles
        if len(sources_df) < len(text_units) / 2:
            logger.warning(f"⚠️ Could not match sources with text_units, but only {len(sources_df)} sources present (filtered)")
            return []

        logger.warning("⚠️ Could not match sources with text_units by text content, returning all document identifiers")
        titles = []
        has_source_url = 'source_url' in documents.columns

        for _, doc in documents.iterrows():
            # For news articles with URLs, use source_url
            if has_source_url:
                source_url = str(doc.get('source_url', '')).strip()
                if source_url and (source_url.startswith('http://') or source_url.startswith('https://')):
                    titles.append(source_url)
                    continue

            # For PDFs and other documents, use title/filename
            if 'title' in documents.columns:
                title = str(doc.get('title', ''))
                title = os.path.splitext(title)[0].replace('_', ' ')
                if title:
                    titles.append(title)

        return list(set(titles))

        return []

    except Exception as e:
        logger.error(f"❌ Failed to extract document titles: {e}")
        import traceback
        logger.error(f"❌ Traceback:\n{traceback.format_exc()}")
        return []


def serialize_context(context: Any) -> Any:
    """Serialize context for JSON response (converts DataFrames to dicts)"""
    if isinstance(context, str):
        return context
    elif isinstance(context, list):
        return [df.to_dict(orient="records") if isinstance(df, pd.DataFrame) else df for df in context]
    elif isinstance(context, dict):
        return {
            key: df.to_dict(orient="records") if isinstance(df, pd.DataFrame) else df
            for key, df in context.items()
        }
    else:
        return context


def sanitize_float(value, default=0.0):
    """Sanitize float values for JSON serialization"""
    try:
        if pd.isna(value) or value is None or not isinstance(value, (int, float)):
            return default
        if np.isinf(value) or np.isnan(value):
            return default
        return float(value)
    except:
        return default
