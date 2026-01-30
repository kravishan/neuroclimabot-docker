import asyncio
import aiohttp
import time
import numpy as np
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from app.config import get_settings
from app.core.exceptions import RAGException
from app.core.dependencies import get_semaphore_manager
from app.utils.logger import get_logger
from app.services.rag.embeddings import get_embeddings

logger = get_logger(__name__)
settings = get_settings()


@dataclass
class GraphRAGResult:
    entities: List[Dict[str, Any]]
    relationships: List[Dict[str, Any]]
    communities: List[Dict[str, Any]]
    total_results: int
    response_time: float


class GraphRAGAPIClient:
    def __init__(self):
        self.graphrag_base_url = settings.GRAPHRAG_SERVER_URL.rstrip('/')
        self.timeout = settings.GRAPHRAG_API_TIMEOUT
        self.is_initialized = False
        self.min_relevance_threshold = settings.GRAPH_MIN_RELEVANCE_SCORE
        
        # Local search configuration from settings
        self.local_search_config = {
            "max_entities": settings.GRAPHRAG_LOCAL_SEARCH_MAX_ENTITIES,
            "max_relationships": settings.GRAPHRAG_LOCAL_SEARCH_MAX_RELATIONSHIPS,
            "max_communities": settings.GRAPHRAG_LOCAL_SEARCH_MAX_COMMUNITIES,
            "context_depth": settings.GRAPHRAG_LOCAL_SEARCH_CONTEXT_DEPTH,
            "min_relevance_score": settings.GRAPHRAG_LOCAL_SEARCH_MIN_RELEVANCE_SCORE,
            "include_community_context": settings.GRAPHRAG_LOCAL_SEARCH_INCLUDE_COMMUNITY_CONTEXT,
            "use_llm_extraction": settings.GRAPHRAG_LOCAL_SEARCH_USE_LLM_EXTRACTION
        }
        
        # Visualization configuration from settings
        self.visualization_config = {
            "max_nodes": settings.GRAPHRAG_VISUALIZATION_MAX_NODES,
            "max_edges": settings.GRAPHRAG_VISUALIZATION_MAX_EDGES,
            "include_summary": settings.GRAPHRAG_VISUALIZATION_INCLUDE_SUMMARY
        }
        
        self.performance_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "avg_response_time": 0.0,
            "timeout_count": 0,
            "connection_errors": 0,
            "local_search_requests": 0,
            "visualization_requests": 0,
            "entities_processed": 0,
            "relationships_processed": 0,
            "communities_processed": 0,
            "relevance_filtered": 0,
            "links_generated": 0,
            "nodes_processed": 0
        }

        # Initialize embedding service for semantic similarity
        self.embedding_service = get_embeddings()
    
    async def initialize(self):
        try:
            await self._test_connection()
            self.is_initialized = True
            logger.info(f"✅ GraphRAG API client initialized - server: {self.graphrag_base_url}")
        except Exception as e:
            logger.warning(f"⚠️  GraphRAG API client initialization failed (non-critical): {e}")
            logger.info("ℹ️  Application will continue without GraphRAG functionality")
            self.is_initialized = False
            # Don't raise - GraphRAG is optional
    
    async def local_search(
        self,
        question: str,
        bucket: Optional[str] = None,
        embedding: Optional[List[float]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Perform local search using the GraphRAG /graphrag/local-search endpoint.
        Updated for new API format with community_level and response_type.
        Uses semaphore to limit concurrent GraphRAG API calls.
        """
        semaphore_manager = get_semaphore_manager()

        if not self.is_initialized:
            await self.initialize()

        logger.debug("🔒 Waiting for GraphRAG semaphore...")
        async with semaphore_manager.graphrag_semaphore:
            logger.debug("✅ GraphRAG semaphore acquired")

            start_time = time.perf_counter()
            self.performance_stats["total_requests"] += 1
            self.performance_stats["local_search_requests"] += 1

            try:
                # Build payload for new GraphRAG API format
                payload = {
                    "question": question,
                    "community_level": kwargs.get("community_level", 2),
                    "response_type": kwargs.get("response_type", "One Paragraphs")
                }

                logger.info(f"🔍 GraphRAG local search: '{question[:100]}...' (bucket: {bucket or 'all'})")

                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.graphrag_base_url}/graphrag/local-search",
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=self.timeout)
                    ) as response:

                        if response.status != 200:
                            error_text = await response.text()
                            raise Exception(f"GraphRAG local-search API error {response.status}: {error_text}")

                        try:
                            api_response = await response.json()
                            logger.debug(f"📥 GraphRAG raw response type: {type(api_response).__name__}")
                            if isinstance(api_response, list):
                                logger.debug(f"📥 GraphRAG response is array with {len(api_response)} elements")
                            elif isinstance(api_response, dict):
                                logger.debug(f"📥 GraphRAG response is dict with keys: {list(api_response.keys())}")
                        except Exception as json_err:
                            logger.error(f"Failed to parse GraphRAG JSON response: {json_err}")
                            raise Exception(f"Invalid JSON response from GraphRAG service: {json_err}")

                # NEW API returns a list, extract first element
                if isinstance(api_response, list) and len(api_response) > 0:
                    logger.debug(f"🔓 Unwrapping array: taking first element of {len(api_response)} items")
                    api_response = api_response[0]
                    logger.debug(f"✅ After unwrapping, response type: {type(api_response).__name__}, keys: {list(api_response.keys()) if isinstance(api_response, dict) else 'N/A'}")
                elif isinstance(api_response, list):
                    logger.warning("⚠️ GraphRAG API returned empty list")
                    return self._create_empty_local_search_response(question)

                response_time = time.perf_counter() - start_time
                self._update_performance_stats(response_time, success=True)

                # Process the response from new API format - data is in "context" not "data"
                logger.debug(f"📦 Extracting context from response...")
                context = api_response.get("context", {})
                if not context:
                    logger.warning(f"⚠️ No 'context' field in response. Available keys: {list(api_response.keys())}")

                entities = context.get("entities", [])
                relationships = context.get("relationships", [])
                reports = context.get("reports", [])
                claims = context.get("claims", [])
                sources = context.get("sources", [])

                logger.debug(f"📊 Extracted from context: {len(entities)} entities, {len(relationships)} relationships, {len(reports)} reports, {len(sources)} sources")

                # Update processing stats
                self.performance_stats["entities_processed"] += len(entities)
                self.performance_stats["relationships_processed"] += len(relationships)
                self.performance_stats["communities_processed"] += len(reports)

                logger.info(f"✅ GraphRAG local search completed: {len(entities)} entities, {len(relationships)} relationships, {len(reports)} reports, {len(sources)} sources in {response_time:.3f}s")
                logger.debug("🔓 GraphRAG semaphore released")

                return api_response

            except asyncio.TimeoutError:
                self.performance_stats["timeout_count"] += 1
                self.performance_stats["failed_requests"] += 1
                logger.warning(f"GraphRAG local-search API timeout after {self.timeout}s")
                return self._create_empty_local_search_response(question)
            except aiohttp.ClientError as e:
                self.performance_stats["connection_errors"] += 1
                self.performance_stats["failed_requests"] += 1
                logger.error(f"GraphRAG local-search API connection error: {e}")
                return self._create_empty_local_search_response(question)
            except Exception as e:
                self.performance_stats["failed_requests"] += 1
                logger.error(f"GraphRAG local-search API error: {e}")
                return self._create_empty_local_search_response(question)
    
    async def search_graph_data(
        self,
        query: str,
        embedding: Optional[List[float]] = None,  # Accept pre-generated embedding
        search_type: str = "local",
        limit: int = 10,
        include_communities: bool = True,
        include_relationships: bool = True,
        bucket: Optional[str] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Search graph data using local-search and convert to graph items format.
        Now includes semantic similarity calculation for filtering.
        """
        try:
            # Use local_search for actual data retrieval
            local_search_response = await self.local_search(
                question=query,
                embedding=embedding,  # Pass pre-generated embedding if available
                bucket=bucket,
                **kwargs
            )

            # Generate query embedding if not provided (for semantic similarity)
            query_embedding = embedding
            if query_embedding is None:
                logger.debug("Generating query embedding for graph data semantic similarity...")
                query_embedding = await self._get_text_embedding(query)

            # Convert local search response to graph items with semantic similarity
            graph_items = await self._convert_local_search_to_graph_items(
                local_search_response, query, query_embedding, limit
            )

            return graph_items

        except Exception as e:
            logger.error(f"Error in search_graph_data: {e}")
            return []
    
    async def get_visualization_data(
        self,
        doc_name: str,
        bucket: str = "default"
    ) -> Dict[str, Any]:
        """
        Get visualization data using the GraphRAG /graphrag/visualization endpoint
        Updated for new API format - simplified to only send doc_name
        """
        if not self.is_initialized:
            await self.initialize()

        start_time = time.perf_counter()
        self.performance_stats["total_requests"] += 1
        self.performance_stats["visualization_requests"] += 1

        try:
            # Simplified payload - only send source (doc_name)
            payload = {
                "source": doc_name  # Can be filename or URL
            }

            logger.info(f"📊 GraphRAG visualization: '{doc_name}'")

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.graphrag_base_url}/graphrag/visualization",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:

                    if response.status == 404:
                        logger.info(f"No graph data found for {doc_name}")
                        return self._create_empty_visualization_response(doc_name)

                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"GraphRAG visualization API error {response.status}: {error_text}")

                    api_response = await response.json()

            # CRITICAL FIX: External service returns array, extract first element
            if isinstance(api_response, list) and len(api_response) > 0:
                api_response = api_response[0]

            response_time = time.perf_counter() - start_time
            self._update_performance_stats(response_time, success=True)

            # Transform data for react-force-graph if needed
            if api_response.get("status") == "success":
                # NEW API FORMAT: Extract all_data and transform to graph_data
                all_data = api_response.get("all_data", {})

                # Transform entities to nodes and relationships to links
                graph_data = self._transform_all_data_to_graph_format(all_data)

                # Critical fix: Ensure links are properly processed and generated
                transformed_data = self._transform_for_force_graph_with_links(graph_data)

                # Log the transformation results
                nodes_count = len(transformed_data.get("nodes", []))
                links_count = len(transformed_data.get("links", []))

                logger.info(f"📊 Graph data transformed: {nodes_count} nodes, {links_count} links")

                self.performance_stats["nodes_processed"] += nodes_count
                self.performance_stats["links_generated"] += links_count

                # Restructure all_data to include entities/relationships from transformed graph_data
                # This ensures consistency - visualization uses graph_data, tabs use all_data
                # Both come from the same transformed source

                # Simplified response structure - flatten to top level
                return {
                    "success": True,
                    "nodes": transformed_data.get("nodes", []),
                    "links": transformed_data.get("links", []),
                    "communities": all_data.get("communities", []),
                    "claims": all_data.get("claims", []),
                    "community_reports": all_data.get("community_reports", []),
                    "metadata": {
                        "entities_count": nodes_count,
                        "relationships_count": links_count,
                        "communities_count": len(all_data.get("communities", [])),
                        "claims_count": len(all_data.get("claims", [])),
                        "community_reports_count": len(all_data.get("community_reports", [])),
                        "processing_timestamp": api_response.get("timestamp") or time.strftime("%Y-%m-%dT%H:%M:%S"),
                        "doc_name": doc_name
                    }
                }
            else:
                return api_response

        except asyncio.TimeoutError:
            self.performance_stats["timeout_count"] += 1
            self.performance_stats["failed_requests"] += 1
            return self._create_error_visualization_response(doc_name, "API timeout")
        except aiohttp.ClientError as e:
            self.performance_stats["connection_errors"] += 1
            self.performance_stats["failed_requests"] += 1
            return self._create_error_visualization_response(doc_name, f"Connection error: {str(e)}")
        except Exception as e:
            self.performance_stats["failed_requests"] += 1
            return self._create_error_visualization_response(doc_name, str(e))
    
    def _transform_all_data_to_graph_format(self, all_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform the new API format (all_data with entities/relationships) to graph format (nodes/links)
        """
        try:
            entities = all_data.get("entities", [])
            relationships = all_data.get("relationships", [])
            communities = all_data.get("communities", [])

            logger.info(f"Transforming all_data: {len(entities)} entities, {len(relationships)} relationships, {len(communities)} communities")

            # Transform entities to nodes
            nodes = []
            for entity in entities:
                node = {
                    "id": entity.get("name", ""),  # Use entity name as ID
                    "name": entity.get("name", ""),
                    "type": entity.get("type", ""),
                    "description": entity.get("description", ""),
                    "degree": entity.get("degree", 0),
                    "val": entity.get("degree", 10),  # Use degree as node size
                    "size": entity.get("degree", 10),
                    "color": self._get_node_color(entity.get("type", "UNKNOWN"))
                }
                nodes.append(node)

            # Transform relationships to links
            links = []
            for relationship in relationships:
                link = {
                    "source": relationship.get("source_entity", ""),
                    "target": relationship.get("target_entity", ""),
                    "type": relationship.get("description", "RELATED"),
                    "description": relationship.get("description", ""),
                    "value": relationship.get("strength", 1.0),
                    "strength": relationship.get("strength", 1.0)
                }
                links.append(link)

            graph_data = {
                "nodes": nodes,
                "links": links,
                "communities": communities
            }

            logger.info(f"Transformed graph_data: {len(nodes)} nodes, {len(links)} links")

            return graph_data

        except Exception as e:
            logger.error(f"Error transforming all_data to graph format: {e}")
            return {"nodes": [], "links": [], "communities": []}

    def _transform_for_force_graph_with_links(
        self,
        graph_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Transform graph data for react-force-graph compatibility with proper link generation
        No limits on nodes or edges - return all data
        """
        try:
            nodes = graph_data.get("nodes", [])
            links = graph_data.get("links", [])

            logger.info(f"Original data: {len(nodes)} nodes, {len(links)} links")

            # Ensure nodes have required properties for force graph
            processed_nodes = []
            node_id_mapping = {}

            for i, node in enumerate(nodes):
                # Clean node name by removing quotes
                node_name = str(node.get("name", f"Node {i}")).strip('"')
                node_id = str(node.get("id", f"node_{i}"))
                
                force_node = {
                    "id": node_id,
                    "name": node_name,
                    "type": node.get("type", "UNKNOWN"),
                    "description": node.get("description", ""),
                    "val": node.get("val", 12),
                    "color": node.get("color", self._get_node_color(node.get("type", "UNKNOWN"))),
                    "group": node.get("group", 0)
                }
                processed_nodes.append(force_node)
                
                # Create mapping for link generation
                node_id_mapping[node_id] = node_name
                node_id_mapping[node_name] = node_id
                node_id_mapping[node_name.upper()] = node_id
            
            # Process existing links first
            processed_links = []
            valid_node_ids = {node["id"] for node in processed_nodes}

            for link in links:
                source_id = self._resolve_node_id(link.get("source"), node_id_mapping, valid_node_ids)
                target_id = self._resolve_node_id(link.get("target"), node_id_mapping, valid_node_ids)

                if source_id and target_id and source_id != target_id:
                    force_link = {
                        "source": source_id,
                        "target": target_id,
                        "type": link.get("type", "RELATED"),
                        "description": link.get("description", ""),
                        "value": link.get("value", 1.0),
                        "color": link.get("color", "#999999")
                    }
                    processed_links.append(force_link)

            # If no links exist, generate intelligent links based on node types and names
            if len(processed_links) == 0:
                logger.info("No existing links found. Generating intelligent links based on node relationships...")
                generated_links = self._generate_intelligent_links(processed_nodes)
                processed_links.extend(generated_links)

            # If still no links, create basic connections for visualization
            if len(processed_links) == 0 and len(processed_nodes) > 1:
                logger.info("Generating basic connectivity for visualization...")
                basic_links = self._generate_basic_connectivity(processed_nodes)
                processed_links.extend(basic_links)
            
            result = {
                "nodes": processed_nodes,
                "links": processed_links,
                "stats": {
                    "total_nodes": len(processed_nodes),
                    "total_links": len(processed_links),
                    "original_nodes": len(nodes),
                    "original_links": len(links),
                    "links_generated": len(processed_links) - len([l for l in links if l.get("source") and l.get("target")])
                }
            }
            
            logger.info(f"Final result: {len(processed_nodes)} nodes, {len(processed_links)} links")
            
            return result
            
        except Exception as e:
            logger.error(f"Error transforming graph data: {e}")
            return {"nodes": [], "links": [], "stats": {"total_nodes": 0, "total_links": 0}}
    
    def _resolve_node_id(self, identifier: str, node_id_mapping: Dict[str, str], valid_node_ids: set) -> Optional[str]:
        """Resolve node identifier to a valid node ID"""
        if not identifier:
            return None
            
        # Try direct lookup
        if identifier in valid_node_ids:
            return identifier
            
        # Try mapping lookup
        if identifier in node_id_mapping:
            mapped_id = node_id_mapping[identifier]
            if mapped_id in valid_node_ids:
                return mapped_id
        
        # Try case-insensitive lookup
        identifier_upper = identifier.upper()
        if identifier_upper in node_id_mapping:
            mapped_id = node_id_mapping[identifier_upper]
            if mapped_id in valid_node_ids:
                return mapped_id
        
        return None
    
    def _generate_intelligent_links(self, nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate intelligent links based on node types, names, and descriptions
        No limit on links - generate all reasonable connections
        """
        links = []

        try:
            # Group nodes by type
            nodes_by_type = {}
            for node in nodes:
                node_type = node.get("type", "UNKNOWN")
                if node_type not in nodes_by_type:
                    nodes_by_type[node_type] = []
                nodes_by_type[node_type].append(node)

            # Define relationship rules
            relationship_rules = [
                # System-User relationships
                ("SYSTEM", "PERSON", "USED_BY", "#4ECDC4"),
                ("SYSTEM", "TECHNOLOGY", "USES", "#FF9F43"),

                # Research relationships
                ("RESEARCH_TOPIC", "TECHNOLOGY", "IMPLEMENTS", "#F7DC6F"),
                ("RESEARCH_TOPIC", "ORGANIZATION", "STUDIED_BY", "#4ECDC4"),

                # Platform relationships
                ("REVIEW PLATFORM", "RESEARCH_TOPIC", "HOSTS", "#BDC3C7"),
                ("ORGANIZATION", "REVIEW PLATFORM", "OPERATES", "#4ECDC4"),

                # Decision relationships
                ("PERSON", "DECISION_MAKING", "MAKES", "#FF6B6B"),
                ("RESEARCH_TOPIC", "DECISION_MAKING", "INFLUENCES", "#F7DC6F"),

                # Reputation relationships
                ("RESEARCH_TOPIC", "REPUTATION", "AFFECTS", "#F7DC6F"),
                ("ORGANIZATION", "REPUTATION", "HAS", "#4ECDC4"),
            ]

            # Apply relationship rules
            for source_type, target_type, relation_type, color in relationship_rules:
                source_nodes = nodes_by_type.get(source_type, [])
                target_nodes = nodes_by_type.get(target_type, [])

                for source_node in source_nodes:
                    for target_node in target_nodes:
                        link = {
                            "source": source_node["id"],
                            "target": target_node["id"],
                            "type": relation_type,
                            "description": f"{source_node['name']} {relation_type.lower().replace('_', ' ')} {target_node['name']}",
                            "value": 1.0,
                            "color": color
                        }
                        links.append(link)

            # Add semantic similarity links
            similarity_links = self._generate_semantic_links(nodes)
            links.extend(similarity_links)
            
            logger.info(f"Generated {len(links)} intelligent links")
            return links
            
        except Exception as e:
            logger.error(f"Error generating intelligent links: {e}")
            return []
    
    def _generate_semantic_links(self, nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate links based on semantic similarity of node names and descriptions
        No limit on links - generate all reasonable semantic connections
        """
        links = []

        try:
            # Keywords that suggest relationships
            relationship_keywords = {
                "review": ["platform", "user", "restaurant", "decision"],
                "user": ["system", "platform", "decision"],
                "restaurant": ["review", "reputation", "decision"],
                "platform": ["review", "user", "organization"],
                "technology": ["system", "user", "llm"],
                "decision": ["user", "review", "restaurant"],
                "reputation": ["restaurant", "review", "organization"]
            }

            for i, node1 in enumerate(nodes):
                node1_name = node1.get("name", "").lower()
                node1_desc = node1.get("description", "").lower()
                node1_text = f"{node1_name} {node1_desc}"

                for j, node2 in enumerate(nodes[i+1:], i+1):
                    node2_name = node2.get("name", "").lower()
                    node2_desc = node2.get("description", "").lower()
                    node2_text = f"{node2_name} {node2_desc}"

                    # Check for keyword relationships
                    for keyword, related_words in relationship_keywords.items():
                        if keyword in node1_text:
                            for related_word in related_words:
                                if related_word in node2_text:
                                    link = {
                                        "source": node1["id"],
                                        "target": node2["id"],
                                        "type": "SEMANTIC_RELATED",
                                        "description": f"Related through {keyword}-{related_word}",
                                        "value": 0.8,
                                        "color": "#95A5A6"
                                    }
                                    links.append(link)
                                    break
            
            return links
            
        except Exception as e:
            logger.error(f"Error generating semantic links: {e}")
            return []
    
    def _generate_basic_connectivity(self, nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate basic connectivity to ensure the graph is connected
        Creates connections for all nodes without limits
        """
        links = []

        try:
            if len(nodes) < 2:
                return links

            # Create a simple chain or star pattern
            if len(nodes) <= 6:
                # Chain pattern for small graphs
                for i in range(len(nodes) - 1):
                    link = {
                        "source": nodes[i]["id"],
                        "target": nodes[i+1]["id"],
                        "type": "CONNECTED",
                        "description": "Basic connectivity",
                        "value": 0.5,
                        "color": "#BDC3C7"
                    }
                    links.append(link)
            else:
                # Star pattern with central node
                central_node = nodes[0]
                for i in range(1, len(nodes)):
                    link = {
                        "source": central_node["id"],
                        "target": nodes[i]["id"],
                        "type": "CONNECTED",
                        "description": "Basic connectivity",
                        "value": 0.5,
                        "color": "#BDC3C7"
                    }
                    links.append(link)
            
            logger.info(f"Generated {len(links)} basic connectivity links")
            return links
            
        except Exception as e:
            logger.error(f"Error generating basic connectivity: {e}")
            return []
    
    async def _convert_local_search_to_graph_items(
        self,
        local_search_response: Dict[str, Any],
        original_query: str,
        query_embedding: Optional[List[float]],
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        Convert local search response to graph items format for compatibility.
        Updated for new GraphRAG API format with context structure and new field names.
        Now includes semantic similarity calculation using embeddings.
        """
        logger.debug(f"🔄 _convert_local_search_to_graph_items called with response type: {type(local_search_response).__name__}")

        graph_items = []

        try:
            # New API format: data is in "context" not "data"
            context = local_search_response.get("context", {})
            if not context:
                logger.error(f"❌ No context found in response! Response keys: {list(local_search_response.keys())}")
                return []

            entities = context.get("entities", [])
            relationships = context.get("relationships", [])
            reports = context.get("reports", [])
            claims = context.get("claims", [])
            sources = context.get("sources", [])

            # Enhanced logging to debug filtering issues
            logger.info(f"🔍 STARTING FILTERING: Query='{original_query[:50]}', Entities={len(entities)}, Relationships={len(relationships)}, Reports={len(reports)}, Sources={len(sources)}")

            # Get titles from top level
            titles = local_search_response.get("titles", [])

            logger.debug(f"📊 Processing: {len(entities)} entities, {len(relationships)} relationships, {len(reports)} reports, {len(sources)} sources")
            logger.info(f"🎯 RELEVANCE THRESHOLD: {self.min_relevance_threshold} (items with score < {self.min_relevance_threshold} will be filtered out)")

            # Generate query embedding if not provided
            if query_embedding is None:
                logger.debug("🔢 Generating query embedding for semantic similarity...")
                query_embedding = await self._get_text_embedding(original_query)
                if query_embedding:
                    logger.debug(f"✅ Query embedding generated: dimension={len(query_embedding)}")
                else:
                    logger.warning("⚠️ Failed to generate query embedding, falling back to heuristic scoring")

            # Process entities - NEW FIELD NAMES: entity (not name), id (not entity_id)
            entities_passed = 0
            entities_filtered = 0
            for i, entity in enumerate(entities):
                entity_name = entity.get("entity", "Unknown")
                entity_id = entity.get("id", str(i))
                num_relationships = entity.get("number of relationships", "0")
                in_context = entity.get("in_context", True)

                # NEW: Extract document_names from each entity
                entity_document_names = entity.get("document_names", [])

                # Build entity content for embedding
                entity_content = self._build_entity_content(entity)

                # Calculate semantic similarity if embeddings are available
                if query_embedding is not None:
                    entity_embedding = await self._get_text_embedding(entity_content)
                    if entity_embedding is not None:
                        relevance_score = self._calculate_cosine_similarity(query_embedding, entity_embedding)
                        logger.info(f"🔢 Entity '{entity_name[:30]}': semantic_sim={relevance_score:.3f}")
                    else:
                        # Fallback to heuristic scoring
                        try:
                            rel_count = int(num_relationships)
                            relevance_score = min(rel_count / 20.0, 1.0) if rel_count > 0 else 0.5
                        except:
                            relevance_score = 0.5
                        logger.info(f"🔢 Entity '{entity_name[:30]}': heuristic={relevance_score:.3f} (embedding failed)")
                else:
                    # Fallback to heuristic scoring
                    try:
                        rel_count = int(num_relationships)
                        relevance_score = min(rel_count / 20.0, 1.0) if rel_count > 0 else 0.5
                    except:
                        relevance_score = 0.5
                    logger.info(f"🔢 Entity '{entity_name[:30]}': heuristic={relevance_score:.3f} (no query embedding)")

                # Small boost if in_context (but don't override semantic similarity completely)
                original_score = relevance_score
                if in_context:
                    relevance_score = min(relevance_score * 1.1, 1.0)
                    if original_score != relevance_score:
                        logger.info(f"  ↗️ Boosted by 10% (in_context): {original_score:.3f} → {relevance_score:.3f}")

                if relevance_score >= self.min_relevance_threshold:
                    entities_passed += 1
                    logger.info(f"  ✅ PASSED (score={relevance_score:.3f} >= {self.min_relevance_threshold})")
                    graph_item = {
                        "doc_name": f"Graph Entity: {entity_name}",
                        "content": entity_content,
                        "entities": [entity_name],
                        "score": relevance_score,
                        "similarity_score": relevance_score,
                        "source": "graph",
                        "graph_id": f"entity_{entity_id}",
                        "document_name": ", ".join(entity_document_names) if entity_document_names else "",
                        "bucket": "",
                        "metadata": {
                            "search_type": "graphrag_local_search_entity",
                            "entity_type": entity.get("type", "unknown"),
                            "entity_id": entity_id,
                            "data_source": "graphrag_local_search_api",
                            "in_context": in_context,
                            "number_of_relationships": num_relationships,
                            "document_names": entity_document_names
                        }
                    }
                    graph_items.append(graph_item)
                else:
                    entities_filtered += 1
                    logger.info(f"  ❌ FILTERED (score={relevance_score:.3f} < {self.min_relevance_threshold})")
                    self.performance_stats["relevance_filtered"] += 1

            # Process relationships - NEW FIELD NAMES: source (not source_entity), target (not target_entity), id (not relationship_id)
            logger.debug(f"🔗 Processing {len(relationships)} relationships...")
            relationships_passed = 0
            relationships_filtered = 0
            for i, relationship in enumerate(relationships):
                source_entity = relationship.get("source", "Unknown")
                target_entity = relationship.get("target", "Unknown")
                relationship_id = relationship.get("id", str(i))
                weight = relationship.get("weight", "1.0")
                in_context = relationship.get("in_context", True)

                # NEW: Extract document_names from each relationship
                relationship_document_names = relationship.get("document_names", [])

                # Build relationship content for embedding
                relationship_content = self._build_relationship_content(relationship)

                # Calculate semantic similarity if embeddings are available
                if query_embedding is not None:
                    relationship_embedding = await self._get_text_embedding(relationship_content)
                    if relationship_embedding is not None:
                        relevance_score = self._calculate_cosine_similarity(query_embedding, relationship_embedding)
                    else:
                        # Fallback to weight-based scoring
                        try:
                            relevance_score = float(weight) / 10.0
                            relevance_score = min(max(relevance_score, 0.0), 1.0)
                        except:
                            relevance_score = 0.5
                else:
                    # Fallback to weight-based scoring
                    try:
                        relevance_score = float(weight) / 10.0
                        relevance_score = min(max(relevance_score, 0.0), 1.0)
                    except:
                        relevance_score = 0.5

                # Small boost if in_context (but don't override semantic similarity completely)
                if in_context:
                    relevance_score = min(relevance_score * 1.1, 1.0)

                if relevance_score >= self.min_relevance_threshold:
                    relationships_passed += 1
                    graph_item = {
                        "doc_name": f"Graph Relationship: {source_entity} - {target_entity}",
                        "content": relationship_content,
                        "entities": [source_entity, target_entity],
                        "score": relevance_score,
                        "similarity_score": relevance_score,
                        "source": "graph",
                        "graph_id": f"relationship_{relationship_id}",
                        "document_name": ", ".join(relationship_document_names) if relationship_document_names else "",
                        "bucket": "",
                        "metadata": {
                            "search_type": "graphrag_local_search_relationship",
                            "relationship_id": relationship_id,
                            "data_source": "graphrag_local_search_api",
                            "weight": weight,
                            "in_context": in_context,
                            "links": relationship.get("links", ""),
                            "document_names": relationship_document_names
                        }
                    }
                    graph_items.append(graph_item)
                else:
                    relationships_filtered += 1
                    self.performance_stats["relevance_filtered"] += 1

            # Process reports (replaces communities) - NEW STRUCTURE
            logger.debug(f"📋 Processing {len(reports)} reports...")
            reports_passed = 0
            reports_filtered = 0
            for i, report in enumerate(reports):
                report_id = report.get("id", str(i))
                report_title = report.get("title", "Unknown Report")
                report_raw_content = report.get("content", "")

                # NEW: Extract document_names from each report
                report_document_names = report.get("document_names", [])

                # Build full report content for embedding
                report_content_for_embedding = self._build_report_content(report)

                # Calculate semantic similarity if embeddings are available
                if query_embedding is not None:
                    report_embedding = await self._get_text_embedding(report_content_for_embedding)
                    if report_embedding is not None:
                        relevance_score = self._calculate_cosine_similarity(query_embedding, report_embedding)
                        logger.debug(f"📄 Report '{report_title[:40]}': semantic_sim={relevance_score:.3f}")
                    else:
                        # Fallback to default score
                        relevance_score = 0.5
                        logger.debug(f"📄 Report '{report_title[:40]}': fallback={relevance_score:.3f} (embedding failed)")
                else:
                    # Fallback to default score
                    relevance_score = 0.5
                    logger.debug(f"📄 Report '{report_title[:40]}': fallback={relevance_score:.3f} (no query embedding)")

                if relevance_score >= self.min_relevance_threshold:
                    reports_passed += 1
                    logger.debug(f"  ✅ PASSED (score={relevance_score:.3f} >= {self.min_relevance_threshold})")
                    graph_item = {
                        "doc_name": f"Graph Report: {report_title}",
                        "content": report_content_for_embedding,
                        "entities": [],
                        "score": relevance_score,
                        "similarity_score": relevance_score,
                        "source": "graph",
                        "graph_id": f"report_{report_id}",
                        "document_name": ", ".join(report_document_names) if report_document_names else "",
                        "bucket": "",
                        "metadata": {
                            "search_type": "graphrag_local_search_report",
                            "report_id": report_id,
                            "data_source": "graphrag_local_search_api",
                            "document_names": report_document_names
                        }
                    }
                    graph_items.append(graph_item)
                else:
                    reports_filtered += 1
                    logger.debug(f"  ❌ FILTERED (score={relevance_score:.3f} < {self.min_relevance_threshold})")
                    self.performance_stats["relevance_filtered"] += 1

            # Process sources (new section)
            for i, source in enumerate(sources):
                source_id = source.get("id", str(i))
                source_text = source.get("text", "")

                # NEW: Extract document_names from each source
                source_document_names = source.get("document_names", [])

                if source_text:
                    # Truncate source text for embedding (it can be very long)
                    source_content = source_text[:500]

                    # Calculate semantic similarity if embeddings are available
                    if query_embedding is not None:
                        source_embedding = await self._get_text_embedding(source_content)
                        if source_embedding is not None:
                            relevance_score = self._calculate_cosine_similarity(query_embedding, source_embedding)
                        else:
                            # Fallback to default score
                            relevance_score = 0.5
                    else:
                        # Fallback to default score
                        relevance_score = 0.5

                    if relevance_score >= self.min_relevance_threshold:
                        graph_item = {
                            "doc_name": f"Graph Source: {source_id}",
                            "content": source_content,
                            "entities": [],
                            "score": relevance_score,
                            "similarity_score": relevance_score,
                            "source": "graph",
                            "graph_id": f"source_{source_id}",
                            "document_name": ", ".join(source_document_names) if source_document_names else "",
                            "bucket": "",
                            "metadata": {
                                "search_type": "graphrag_local_search_source",
                                "source_id": source_id,
                                "data_source": "graphrag_local_search_api",
                                "document_names": source_document_names
                            }
                        }
                        graph_items.append(graph_item)

            # Log summary statistics
            logger.info(f"📊 GraphRAG Filtering Summary:")
            logger.info(f"  Entities: {entities_passed} passed, {entities_filtered} filtered (total: {len(entities)})")
            logger.info(f"  Relationships: {relationships_passed} passed, {relationships_filtered} filtered (total: {len(relationships)})")
            logger.info(f"  Reports: {reports_passed} passed, {reports_filtered} filtered (total: {len(reports)})")
            logger.info(f"  Total graph items before limit: {len(graph_items)}")

            # Sort by relevance score and limit results
            graph_items.sort(key=lambda x: x.get("score", 0.0), reverse=True)
            limited_items = graph_items[:limit]

            if len(graph_items) > limit:
                logger.info(f"  ✂️ Limited to top {limit} items (cut {len(graph_items) - limit} items)")

            logger.info(f"  ✅ Final result: {len(limited_items)} graph items returned")

            return limited_items

        except Exception as e:
            logger.error(f"❌ Error converting local search response to graph items: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []

    def _calculate_cosine_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine similarity between two embeddings."""
        try:
            if not embedding1 or not embedding2:
                return 0.0

            # Convert to numpy arrays
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)

            # Calculate cosine similarity
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            similarity = dot_product / (norm1 * norm2)

            # Clamp to [0, 1] range (cosine similarity is in [-1, 1])
            return max(0.0, min(1.0, (similarity + 1.0) / 2.0))

        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {e}")
            return 0.0

    async def _get_text_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for a text string."""
        try:
            if not text or len(text.strip()) == 0:
                return None

            # Truncate very long texts to avoid embedding issues
            max_length = 2000
            truncated_text = text[:max_length] if len(text) > max_length else text

            embedding = await self.embedding_service.aembed_query(truncated_text)
            return embedding

        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None

    def _build_entity_content(self, entity: Dict[str, Any]) -> str:
        """Build content string for entity - updated for new API field names"""
        try:
            # NEW: entity field instead of name
            name = entity.get('entity', 'Unknown Entity')
            entity_type = entity.get('type', 'Unknown')
            description = entity.get('description', '')
            num_relationships = entity.get('number of relationships', '0')
            document_names = entity.get('document_names', [])

            content = f"Entity: {name} (Type: {entity_type})"
            if description:
                content += f"\nDescription: {description[:300]}"
            content += f"\nRelationships: {num_relationships}"
            if document_names:
                content += f"\nDocuments: {', '.join(document_names)}"

            return content
        except Exception:
            return f"Entity: {entity.get('entity', 'Unknown')}"

    def _build_relationship_content(self, relationship: Dict[str, Any]) -> str:
        """Build content string for relationship - updated for new API field names"""
        try:
            # NEW: source and target instead of source_entity and target_entity
            source = relationship.get('source', 'Unknown')
            target = relationship.get('target', 'Unknown')
            description = relationship.get('description', '')
            weight = relationship.get('weight', '')
            document_names = relationship.get('document_names', [])

            content = f"Relationship: {source} → {target}"
            if weight:
                content += f" (Weight: {weight})"
            if description:
                content += f"\nDescription: {description[:300]}"
            if document_names:
                content += f"\nDocuments: {', '.join(document_names)}"

            return content
        except Exception:
            return f"Relationship: {relationship.get('source', 'Unknown')} → {relationship.get('target', 'Unknown')}"

    def _build_report_content(self, report: Dict[str, Any]) -> str:
        """Build content string for report - NEW for new API format"""
        try:
            title = report.get('title', 'Unknown Report')
            content = report.get('content', '')
            report_id = report.get('id', '')
            document_names = report.get('document_names', [])

            result = f"Report: {title}"
            if report_id:
                result += f" (ID: {report_id})"
            if document_names:
                result += f"\nDocuments: {', '.join(document_names)}"
            if content:
                # Content is markdown, limit length
                result += f"\n\n{content[:500]}"

            return result
        except Exception:
            return f"Report: {report.get('title', 'Unknown')}"

    def _build_community_content(self, community: Dict[str, Any]) -> str:
        """Build content string for community - DEPRECATED, kept for backward compatibility"""
        try:
            title = community.get('title', 'Unknown Community')
            summary = community.get('summary', '')
            member_count = community.get('member_count', 0)

            content = f"Community: {title} ({member_count} members)"
            if summary:
                content += f"\nSummary: {summary[:300]}"

            return content
        except Exception:
            return f"Community: {community.get('title', 'Unknown')}"
    
    def _get_node_color(self, node_type: str) -> str:
        """Get color for node type"""
        color_map = {
            "PERSON": "#FF6B6B",
            "ORGANIZATION": "#4ECDC4", 
            "LOCATION": "#45B7D1",
            "RESEARCH_TOPIC": "#F7DC6F",
            "METHODOLOGY": "#FFEAA7",
            "DATASET": "#DDA0DD",
            "SYSTEM": "#6C5CE7",
            "TECHNOLOGY": "#FF9F43",
            "REVIEW PLATFORM": "#BDC3C7",
            "DECISION_MAKING": "#BDC3C7",
            "REPUTATION": "#BDC3C7",
            "UNKNOWN": "#BDC3C7"
        }
        return color_map.get(node_type.upper(), "#BDC3C7")
    
    def _create_empty_local_search_response(self, question: str) -> Dict[str, Any]:
        """Create empty response for failed local search - updated for new API format"""
        return {
            "success": False,
            "result": "No results found",
            "context": {
                "reports": [],
                "relationships": [],
                "entities": [],
                "claims": [],
                "sources": []
            },
            "titles": [],
            "query": question,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
        }
    
    def _create_empty_visualization_response(self, doc_name: str) -> Dict[str, Any]:
        """Create empty visualization response"""
        return {
            "success": True,
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
                "processing_timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "doc_name": doc_name
            }
        }
    
    def _create_error_visualization_response(self, doc_name: str, error: str) -> Dict[str, Any]:
        """Create error visualization response"""
        return {
            "success": False,
            "error": error,
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
                "processing_timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "doc_name": doc_name
            }
        }
    
    async def _test_connection(self):
        """Test connection to GraphRAG server"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.graphrag_base_url}/graphrag/health",
                    timeout=aiohttp.ClientTimeout(total=10.0)
                ) as response:
                    if response.status == 200:
                        logger.info("✅ GraphRAG server connection test successful")
                    else:
                        raise Exception(f"Server returned status {response.status}")
        except Exception as e:
            raise Exception(f"Cannot connect to GraphRAG server at {self.graphrag_base_url}: {e}")
    
    def _update_performance_stats(self, response_time: float, success: bool):
        """Update performance statistics"""
        if success:
            self.performance_stats["successful_requests"] += 1
        
        total_requests = self.performance_stats["total_requests"]
        current_avg = self.performance_stats["avg_response_time"]
        new_avg = ((current_avg * (total_requests - 1)) + response_time) / total_requests
        self.performance_stats["avg_response_time"] = new_avg
    
    async def health_check(self) -> bool:
        """Check GraphRAG API health"""
        try:
            if not self.is_initialized:
                return False
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.graphrag_base_url}/graphrag/health",
                    timeout=aiohttp.ClientTimeout(total=5.0)
                ) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"GraphRAG API health check failed: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics"""
        try:
            stats = {
                "initialized": self.is_initialized,
                "graphrag_server_url": self.graphrag_base_url,
                "performance": self.performance_stats,
                "api_timeout": self.timeout,
                "local_search_config": self.local_search_config,
                "visualization_config": self.visualization_config,
                "endpoints": {
                    "local_search": f"{self.graphrag_base_url}/graphrag/local-search",
                    "visualization": f"{self.graphrag_base_url}/graphrag/visualization",
                    "health": f"{self.graphrag_base_url}/graphrag/health"
                }
            }
            
            if self.is_initialized:
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            f"{self.graphrag_base_url}/graphrag/health",
                            timeout=aiohttp.ClientTimeout(total=5.0)
                        ) as response:
                            if response.status == 200:
                                server_stats = await response.json()
                                stats["server_health"] = server_stats
                except Exception as e:
                    stats["server_health_error"] = str(e)
            
            return stats
        except Exception as e:
            logger.error(f"Error getting GraphRAG API stats: {e}")
            return {"initialized": False, "error": str(e)}


# Global client instance
graphrag_api_client = GraphRAGAPIClient()


async def get_graphrag_api_client() -> GraphRAGAPIClient:
    """Get the GraphRAG API client instance"""
    if not graphrag_api_client.is_initialized:
        await graphrag_api_client.initialize()
    return graphrag_api_client