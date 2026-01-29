"""
Unified Milvus Storage
Handles all Milvus operations for chunks, summaries, and STP data
Manages 3 separate Milvus databases:
- chunks_database (regular document chunks)
- summaries_database (document summaries)
- STP_MILVUS_DATABASE (STP chunks with special schema)
"""

import logging
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from urllib.parse import urlparse

from storage.base import VectorStorageBackend
from config import config

logger = logging.getLogger(__name__)


class MilvusStorage(VectorStorageBackend):
    """
    Unified Milvus vector storage for chunks, summaries, and STP data
    Manages multiple Milvus databases with different schemas
    """

    def __init__(self):
        super().__init__(config.get('milvus', {}))
        self.chunks_database = self.config.get('chunks_database', 'chunk_test5')
        self.summaries_database = self.config.get('summaries_database', 'summary_test5')
        self.collections = {}
        # Chunk embedding dimension (Qwen3-Embedding-0.6B: 1024)
        self.chunk_embedding_dim = config.get('ollama.chunk_embedding_dim', 1024)
        # Summary embedding dimension (nomic-embed-text: 768)
        self.summary_embedding_dim = 768
        self._pymilvus_available = False

        logger.info(f"📊 Milvus embedding dims - Chunks: {self.chunk_embedding_dim}, Summaries: {self.summary_embedding_dim}")

    def connect(self) -> None:
        """Connect to Milvus and initialize collections"""
        try:
            # Import pymilvus
            try:
                from pymilvus import connections
                self._pymilvus_available = True
                logger.info("📦 pymilvus package available")
            except ImportError:
                logger.warning("⚠️ pymilvus not installed - vector storage unavailable")
                self._pymilvus_available = False
                return

            # Connect to Milvus
            host = self.config.get('host', 'localhost')
            port = self.config.get('port', 19530)
            user = self.config.get('user', '')
            password = self.config.get('password', '')

            logger.info(f"🔌 Connecting to Milvus at {host}:{port}")

            if user and password:
                connections.connect(
                    alias="default",
                    host=host,
                    port=port,
                    user=user,
                    password=password
                )
            else:
                connections.connect(
                    alias="default",
                    host=host,
                    port=port
                )

            # Test connection
            from pymilvus import utility
            server_version = utility.get_server_version()
            logger.info(f"✅ Connected to Milvus server version: {server_version}")

            # Log database configuration
            logger.info(f"📊 Chunks database: {self.chunks_database}")
            logger.info(f"📊 Summaries database: {self.summaries_database}")

            # Initialize collections for chunks and summaries
            self._init_collections()

            self.connected = True
            logger.info("✅ Milvus vector storage initialized successfully")

        except Exception as e:
            logger.error(f"❌ Milvus connection failed: {e}")
            self.connected = False
            self._pymilvus_available = False

    def disconnect(self) -> None:
        """Disconnect from Milvus"""
        if not self._pymilvus_available:
            return
        try:
            from pymilvus import connections
            connections.disconnect("default")
            self.connected = False
            logger.info("✅ Disconnected from Milvus")
        except Exception as e:
            logger.error(f"❌ Error disconnecting from Milvus: {e}")

    def health_check(self) -> bool:
        """Check Milvus health"""
        if not self._pymilvus_available:
            return False
        try:
            # Check if we can connect and list databases (tests connection)
            from pymilvus import connections, db, utility

            # Try to get current connection or reconnect
            try:
                # Test if connection is alive
                _ = utility.list_collections()
                return True
            except Exception:
                # Connection might be dead, try to reconnect
                host = self.config.get('host', 'localhost')
                port = self.config.get('port', 19530)
                user = self.config.get('user', '')
                password = self.config.get('password', '')

                if user and password:
                    connections.connect(alias="default", host=host, port=port, user=user, password=password)
                else:
                    connections.connect(alias="default", host=host, port=port)

                # Test again
                _ = utility.list_collections()
                self.connected = True
                return True

        except Exception as e:
            logger.debug(f"Milvus health check failed: {e}")
            self.connected = False
            return False

    def _init_collections(self):
        """Initialize Milvus collections for chunks and summaries"""
        if not self._pymilvus_available:
            return

        from pymilvus import Collection, utility, db, FieldSchema, CollectionSchema, DataType

        try:
            # Create databases if they don't exist
            existing_dbs = db.list_database()

            for db_name in [self.chunks_database, self.summaries_database]:
                if db_name not in existing_dbs:
                    try:
                        db.create_database(db_name)
                        logger.info(f"✅ Created database: {db_name}")
                    except Exception as e:
                        logger.warning(f"⚠️ Database creation issue for {db_name}: {e}")

            # Initialize collections for each data type and bucket
            for data_type in ['chunks', 'summaries']:
                self.collections[data_type] = {}

                # Use appropriate database
                db_name = self.chunks_database if data_type == 'chunks' else self.summaries_database
                db.using_database(db_name)
                logger.info(f"📂 Using database: {db_name}")

                for bucket, collection_name in self.config['collections'][data_type].items():
                    try:
                        if utility.has_collection(collection_name):
                            collection = Collection(collection_name)
                            logger.info(f"📋 Found existing collection: {collection_name}")
                        else:
                            collection = self._create_collection(collection_name, data_type, bucket)
                            logger.info(f"✅ Created new collection: {collection_name}")

                        collection.load()
                        self.collections[data_type][bucket] = collection
                        logger.info(f"🔄 Loaded collection: {collection_name} in database: {db_name}")

                    except Exception as e:
                        logger.error(f"❌ Collection init failed for {bucket}: {e}")

        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")

    def _create_collection(self, name: str, data_type: str, bucket: str):
        """Create Milvus collection with appropriate schema"""
        if not self._pymilvus_available:
            return None

        from pymilvus import Collection, CollectionSchema, FieldSchema, DataType

        # Use appropriate embedding dimension based on data type
        embedding_dim = self.chunk_embedding_dim if data_type == "chunks" else self.summary_embedding_dim

        # Common fields
        common_fields = [
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=embedding_dim),
            FieldSchema(name="bucket_source", dtype=DataType.VARCHAR, max_length=100),
            FieldSchema(name="processing_timestamp", dtype=DataType.VARCHAR, max_length=100)
        ]

        if data_type == "chunks":
            fields = [
                FieldSchema(name="chunk_id", dtype=DataType.VARCHAR, max_length=100, is_primary=True),
                FieldSchema(name="chunk_text", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="chunk_index", dtype=DataType.INT64),
                FieldSchema(name="token_count", dtype=DataType.INT64),
            ] + common_fields

            # Add source field based on bucket type
            if bucket == "news":
                fields.append(FieldSchema(name="source_url", dtype=DataType.VARCHAR, max_length=500))
            else:
                fields.append(FieldSchema(name="doc_name", dtype=DataType.VARCHAR, max_length=500))

        else:  # summaries
            fields = [
                FieldSchema(name="summary_id", dtype=DataType.VARCHAR, max_length=100, is_primary=True),
                FieldSchema(name="document_type", dtype=DataType.VARCHAR, max_length=100),
                FieldSchema(name="abstractive_summary", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="title", dtype=DataType.VARCHAR, max_length=1000),
            ] + common_fields

            # Add source field based on bucket type
            if bucket == "news":
                fields.append(FieldSchema(name="source_url", dtype=DataType.VARCHAR, max_length=500))
            else:
                fields.append(FieldSchema(name="doc_name", dtype=DataType.VARCHAR, max_length=500))

        schema = CollectionSchema(fields=fields, description=f"{data_type} collection for {bucket}")
        collection = Collection(name=name, schema=schema)

        # Create index
        index_params = {"metric_type": "COSINE", "index_type": "IVF_FLAT", "params": {"nlist": 512}}
        collection.create_index(field_name="embedding", index_params=index_params)

        logger.info(f"✅ Created {data_type} collection: {name}")
        return collection

    # VectorStorageBackend interface implementation
    def create_collection(self, collection_name: str, schema: Dict[str, Any]) -> bool:
        """Create a collection with specified schema"""
        # Implementation for custom collection creation
        pass

    def insert_vectors(self, collection_name: str, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Insert vectors into collection"""
        # Generic insertion method
        pass

    def search_vectors(self, collection_name: str, query_vector: List[float],
                      limit: int = 10, filter_expr: str = None) -> List[Dict[str, Any]]:
        """Search for similar vectors"""
        # Generic search method
        pass

    def delete_vectors(self, collection_name: str, filter_expr: str) -> bool:
        """Delete vectors matching filter"""
        # Generic deletion method
        pass

    def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """Get statistics for specific collection"""
        # Get stats for one collection
        pass

    # Chunk storage methods
    async def insert_chunks(self, chunks_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Insert chunks into appropriate collection (async)"""
        if not self._pymilvus_available or not chunks_data:
            logger.warning("⚠️ Pymilvus not available or no chunks data")
            return {"status": "skipped", "inserted_count": 0}

        # Ensure connection is established
        if not self.connected:
            logger.info("🔌 Establishing Milvus connection...")
            self.connect()
            if not self.connected:
                return {"status": "failed", "inserted_count": 0, "error": "Connection failed"}

        bucket = chunks_data[0]["bucket_source"]

        try:
            from pymilvus import db, connections

            # Ensure connection exists before switching database
            if not connections.has_connection("default"):
                logger.warning("⚠️ Connection lost, reconnecting...")
                self.connect()

            # Switch to chunks database
            db.using_database(self.chunks_database)
            logger.info(f"🔄 Switched to chunks database: {self.chunks_database}")

            collection = self.collections.get("chunks", {}).get(bucket)

            if not collection:
                logger.error(f"❌ No chunks collection for bucket: {bucket}")
                return {"status": "failed", "inserted_count": 0, "error": f"No collection for bucket {bucket}"}

            # Prepare data for insertion
            entities = self._prepare_chunk_entities(chunks_data, bucket)

            logger.info(f"📝 Inserting {len(chunks_data)} chunks into {bucket} chunks collection")

            result = collection.insert(entities)
            collection.flush()

            logger.info(f"✅ Inserted {len(chunks_data)} chunks into {bucket} collection")
            return {"status": "success", "inserted_count": len(chunks_data)}

        except Exception as e:
            logger.error(f"❌ Failed to insert chunks into {bucket}: {e}")
            return {"status": "failed", "inserted_count": 0, "error": str(e)}

    async def insert_summary(self, summary_data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert summary into appropriate collection (async)"""
        if not self._pymilvus_available:
            logger.warning("⚠️ Pymilvus not available")
            return {"status": "skipped", "inserted_count": 0}

        # Ensure connection is established
        if not self.connected:
            logger.info("🔌 Establishing Milvus connection...")
            self.connect()
            if not self.connected:
                return {"status": "failed", "inserted_count": 0, "error": "Connection failed"}

        bucket = summary_data["bucket_source"]

        try:
            from pymilvus import db, connections

            # Ensure connection exists before switching database
            if not connections.has_connection("default"):
                logger.warning("⚠️ Connection lost, reconnecting...")
                self.connect()

            # Switch to summaries database
            db.using_database(self.summaries_database)
            logger.info(f"🔄 Switched to summaries database: {self.summaries_database}")

            collection = self.collections.get("summaries", {}).get(bucket)

            if not collection:
                logger.error(f"❌ No summaries collection for bucket: {bucket}")
                return {"status": "failed", "inserted_count": 0, "error": f"No collection for bucket {bucket}"}

            # Prepare data for insertion
            entities = self._prepare_summary_entities([summary_data], bucket)

            logger.info(f"📝 Inserting summary into {bucket} summaries collection")

            result = collection.insert(entities)
            collection.flush()

            logger.info(f"✅ Inserted summary into {bucket} collection")
            return {"status": "success", "inserted_count": 1}

        except Exception as e:
            logger.error(f"❌ Failed to insert summary into {bucket}: {e}")
            return {"status": "failed", "inserted_count": 0, "error": str(e)}

    def _prepare_chunk_entities(self, chunks_data: List[Dict], bucket: str) -> List[List]:
        """Prepare chunk data for Milvus insertion"""
        entities = [
            [chunk.get("chunk_id", str(uuid.uuid4())) for chunk in chunks_data],
            [chunk.get("chunk_text", "") for chunk in chunks_data],
            [chunk.get("chunk_index", 0) for chunk in chunks_data],
            [chunk.get("token_count", 0) for chunk in chunks_data],
            [chunk.get("embedding", [0.0] * self.chunk_embedding_dim) for chunk in chunks_data],
            [chunk.get("bucket_source", bucket) for chunk in chunks_data],
            [chunk.get("processing_timestamp", datetime.now().isoformat()) for chunk in chunks_data]
        ]

        # Add source field based on bucket type
        if bucket == "news":
            entities.append([chunk.get("source_url", "") for chunk in chunks_data])
        else:
            entities.append([chunk.get("doc_name", "") for chunk in chunks_data])

        return entities

    def _prepare_summary_entities(self, summaries_data: List[Dict], bucket: str) -> List[List]:
        """Prepare summary data for Milvus insertion"""
        entities = [
            [summary.get("summary_id", str(uuid.uuid4())) for summary in summaries_data],
            [summary.get("document_type", "unknown") for summary in summaries_data],
            [summary.get("abstractive_summary", "") for summary in summaries_data],
            [summary.get("title", "") for summary in summaries_data],
            [summary.get("embedding", [0.0] * self.summary_embedding_dim) for summary in summaries_data],
            [summary.get("bucket_source", bucket) for summary in summaries_data],
            [summary.get("processing_timestamp", datetime.now().isoformat()) for summary in summaries_data]
        ]

        # Add source field based on bucket type
        if bucket == "news":
            entities.append([summary.get("source_url", "") for summary in summaries_data])
        else:
            entities.append([summary.get("doc_name", "") for summary in summaries_data])

        return entities

    def search_chunks(self, query_embedding: List[float], bucket: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Search in chunks collections"""
        return self._search("chunks", query_embedding, bucket, limit)

    def search_summaries(self, query_embedding: List[float], bucket: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Search in summaries collections"""
        return self._search("summaries", query_embedding, bucket, limit)

    def _search(self, data_type: str, query_embedding: List[float],
               bucket: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Search in vector collections"""
        if not self._pymilvus_available or not self.connected:
            logger.warning("⚠️ Pymilvus not available or not connected")
            return []

        search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}
        all_results = []

        buckets_to_search = [bucket] if bucket else list(self.collections.get(data_type, {}).keys())

        for search_bucket in buckets_to_search:
            collection = self.collections.get(data_type, {}).get(search_bucket)
            if not collection:
                continue

            # Determine output fields based on bucket and data type
            if data_type == "chunks":
                if search_bucket == "news":
                    output_fields = ["chunk_id", "source_url", "bucket_source", "chunk_text", "chunk_index"]
                else:
                    output_fields = ["chunk_id", "doc_name", "bucket_source", "chunk_text", "chunk_index"]
            else:  # summaries
                if search_bucket == "news":
                    output_fields = ["summary_id", "source_url", "bucket_source", "abstractive_summary", "document_type", "title"]
                else:
                    output_fields = ["summary_id", "doc_name", "bucket_source", "abstractive_summary", "document_type", "title"]

            try:
                results = collection.search(
                    data=[query_embedding],
                    anns_field="embedding",
                    param=search_params,
                    limit=limit,
                    output_fields=output_fields
                )

                for hits in results:
                    for hit in hits:
                        result_dict = {
                            "bucket_source": hit.entity.get("bucket_source"),
                            "similarity_score": 1 - hit.distance
                        }

                        # Add all entity fields
                        for field in output_fields:
                            if field != "bucket_source":
                                result_dict[field] = hit.entity.get(field)

                        all_results.append(result_dict)

            except Exception as e:
                logger.error(f"❌ Search failed for {search_bucket}: {e}")

        # Sort by similarity and return top results
        all_results.sort(key=lambda x: x["similarity_score"], reverse=True)
        return all_results[:limit]

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive storage statistics"""
        stats = {
            "connected": self.connected,
            "pymilvus_available": self._pymilvus_available,
            "chunk_embedding_dimension": self.chunk_embedding_dim,
            "summary_embedding_dimension": self.summary_embedding_dim,
            "collections": {},
            "databases": {
                "chunks_database": self.chunks_database,
                "summaries_database": self.summaries_database
            }
        }

        if not self._pymilvus_available or not self.connected:
            return stats

        try:
            for data_type, buckets in self.collections.items():
                stats["collections"][data_type] = {}
                for bucket, collection in buckets.items():
                    try:
                        count = collection.num_entities
                        stats["collections"][data_type][bucket] = {
                            "count": count,
                            "collection_name": collection.name,
                            "status": "loaded" if collection.is_loaded else "not_loaded",
                            "schema_type": "source_url" if bucket == "news" else "doc_name"
                        }
                    except Exception as e:
                        stats["collections"][data_type][bucket] = {"error": str(e)}

            from pymilvus import utility
            stats["server_version"] = utility.get_server_version()

        except Exception as e:
            logger.error(f"❌ Failed to get collection stats: {e}")
            stats["error"] = str(e)

        return stats


class STPMilvusManager:
    """
    STP-specific Milvus manager
    Handles STP chunks with specialized schema in separate database
    Moved from stp/milvus_manager.py
    """

    def __init__(self, milvus_config: Dict[str, Any]):
        """
        Initialize STP Milvus Manager

        Args:
            milvus_config: Configuration dict with:
                - endpoint: Milvus endpoint (host:port)
                - username: Auth username
                - password: Auth password
                - db_name: STP database name
                - collection: STP collection name
                - embedding_model: Embedding model name
                - embedding_display: Display name
        """
        self.config = milvus_config
        self.embedding_model = None
        self.milvus_client = None
        self.collection_initialized = False

        # Parse endpoint
        endpoint = self.config['endpoint']
        logger.info(f"Parsing endpoint: {endpoint}")

        if '://' in endpoint:
            endpoint = endpoint.split('://')[-1]

        if ':' in endpoint:
            parts = endpoint.split(':')
            self.host = parts[0].strip()
            self.port = int(parts[1].strip())
        else:
            self.host = endpoint.strip()
            self.port = 19530

        logger.info(f"Parsed connection: host={self.host}, port={self.port}")

        # Embedding dimensions
        self.embedding_dims = {
            'sentence-transformers/all-MiniLM-L6-v2': 384,
            'sentence-transformers/all-mpnet-base-v2': 768,
            'BAAI/bge-small-en-v1.5': 384,
            'BAAI/bge-base-en-v1.5': 768
        }

        logger.info(f"STP MilvusManager initialized for endpoint: {self.config['endpoint']}")

        # Automatically check and create collection if needed
        self._ensure_collection_exists()

    def _get_embedding_dim(self) -> int:
        """Get embedding dimension for configured model"""
        return self.embedding_dims.get(self.config['embedding_model'], 384)

    def _create_milvus_client(self) -> bool:
        """Create MilvusClient instance"""
        try:
            from pymilvus import MilvusClient

            uri = self.config['endpoint']
            if not uri.startswith(('http://', 'https://')):
                uri = f"http://{uri}"

            token = f"{self.config['username']}:{self.config['password']}"

            self.milvus_client = MilvusClient(
                uri=uri,
                token=token,
                db_name=self.config['db_name']
            )

            logger.info(f"✅ STP MilvusClient created for database: {self.config['db_name']}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to create STP MilvusClient: {e}")
            return False

    def _connect_to_milvus(self) -> bool:
        """Establish connection to Milvus"""
        try:
            if self.milvus_client is None:
                if not self._create_milvus_client():
                    return False

            collections = self.milvus_client.list_collections()
            logger.info(f"✅ STP connected to Milvus: {len(collections)} collections found")
            return True

        except Exception as e:
            logger.error(f"❌ STP failed to connect to Milvus: {e}")
            return False

    def _disconnect_from_milvus(self):
        """Disconnect from Milvus"""
        try:
            if hasattr(self, 'milvus_client') and self.milvus_client:
                self.milvus_client.close()
                self.milvus_client = None
        except Exception as e:
            logger.warning(f"Error during STP disconnect: {e}")

        try:
            from pymilvus import connections
            if connections.has_connection("default"):
                connections.disconnect("default")
        except Exception:
            pass

    def _ensure_collection_exists(self) -> bool:
        """Ensure STP collection exists, create if needed"""
        try:
            logger.info("🔍 Checking if STP collection exists...")

            if not self._connect_to_milvus():
                logger.error("❌ Cannot connect to Milvus to check STP collection")
                return False

            collection_name = self.config['collection']
            collections = self.milvus_client.list_collections()

            if collection_name in collections:
                logger.info(f"✅ STP collection '{collection_name}' already exists")
                self.collection_initialized = True
                self._disconnect_from_milvus()
                return True

            logger.warning(f"⚠️ STP collection '{collection_name}' does not exist")
            logger.info(f"🏗️ Creating STP collection '{collection_name}'...")

            success = self._create_collection()

            if success:
                logger.info(f"✅ STP collection '{collection_name}' created successfully")
                self.collection_initialized = True
                return True
            else:
                logger.error(f"❌ Failed to create STP collection '{collection_name}'")
                return False

        except Exception as e:
            logger.error(f"❌ Error ensuring STP collection exists: {e}")
            return False

    def _create_collection(self) -> bool:
        """Create STP collection with proper schema"""
        try:
            from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType

            collection_name = self.config['collection']
            db_name = self.config['db_name']
            dim = self._get_embedding_dim()

            logger.info(f"🔧 Creating STP collection '{collection_name}' in database '{db_name}'")

            # Connect legacy API for collection creation
            try:
                if connections.has_connection("default"):
                    connections.disconnect("default")

                connect_params = {
                    "alias": "default",
                    "host": str(self.host),
                    "port": int(self.port),
                    "db_name": db_name
                }

                if self.config.get('username') and self.config.get('password'):
                    connect_params["user"] = self.config.get('username')
                    connect_params["password"] = self.config.get('password')

                connections.connect(**connect_params)
                logger.info(f"✅ Connected legacy API for STP")

            except Exception as legacy_conn_error:
                logger.error(f"❌ Failed to connect legacy Milvus API: {legacy_conn_error}")
                return False

            # Define STP schema
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="original_content", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="rephrased_content", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="doc_name", dtype=DataType.VARCHAR, max_length=512),
                FieldSchema(name="stp_confidence", dtype=DataType.FLOAT),
                FieldSchema(name="qualifying_factors", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="chunk_id", dtype=DataType.VARCHAR, max_length=256),
                FieldSchema(name="processing_timestamp", dtype=DataType.VARCHAR, max_length=100),
                FieldSchema(name="tokens", dtype=DataType.INT64),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim)
            ]

            schema = CollectionSchema(fields, f"STP documents collection in database '{db_name}'")
            collection = Collection(collection_name, schema)
            logger.info(f"✅ Created STP collection '{collection_name}'")

            # Create index
            index_params = {
                "metric_type": "COSINE",
                "index_type": "IVF_FLAT",
                "params": {"nlist": 128}
            }
            collection.create_index("embedding", index_params)
            logger.info("✅ Created vector index for STP collection")

            # Load collection
            collection.load()
            logger.info("✅ STP collection loaded and ready")

            # Disconnect legacy connection
            try:
                connections.disconnect("default")
            except Exception:
                pass

            return True

        except Exception as e:
            logger.error(f"❌ STP collection creation failed: {e}")
            return False

    def _load_embedding_model(self):
        """Load embedding model for STP"""
        if self.embedding_model is None:
            logger.info(f"📥 Loading STP embedding model: {self.config['embedding_display']}...")
            try:
                from sentence_transformers import SentenceTransformer

                self.embedding_model = SentenceTransformer(self.config['embedding_model'])

                # Auto-detect and use GPU if available
                device = config.get_device(prefer_gpu=True)
                if device == 'cuda':
                    self.embedding_model = self.embedding_model.to('cuda')
                    logger.info("🚀 STP model loaded on GPU")
                else:
                    logger.info("💻 STP model loaded on CPU")

            except Exception as e:
                logger.error(f"❌ Failed to load STP embedding model: {e}")
                raise

        return self.embedding_model

    def _generate_embeddings_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """Generate embeddings for batch of texts"""
        model = self._load_embedding_model()
        embeddings = []

        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            try:
                batch_embeddings = model.encode(batch_texts, convert_to_tensor=True, show_progress_bar=False)
                batch_embeddings = batch_embeddings.cpu().numpy().tolist()
                embeddings.extend(batch_embeddings)
            except Exception as e:
                logger.error(f"❌ Failed to generate STP embeddings for batch: {e}")
                raise

        return embeddings

    def _validate_and_clean_data(self, chunk_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate and clean STP data before insertion"""
        cleaned_data = []

        for i, chunk in enumerate(chunk_data):
            try:
                # Extract doc_name
                doc_name = None
                if chunk.get('article_link'):
                    doc_name = str(chunk.get('article_link'))
                else:
                    for field in ['doc_name', 'source_file', 'document_name', 'filename']:
                        if chunk.get(field):
                            doc_name = str(chunk.get(field))
                            break

                if not doc_name:
                    doc_name = 'Unknown'

                # For URLs, keep full URL; for paths, use basename
                if not doc_name.startswith(('http://', 'https://')):
                    import os
                    doc_name = os.path.basename(doc_name)

                original = str(chunk.get('original_content', chunk.get('content', '')) or '')
                rephrased = str(chunk.get('rephrased_content', chunk.get('content', '')) or '')

                cleaned_chunk = {
                    'original_content': original[:65535],
                    'rephrased_content': rephrased[:65535],
                    'doc_name': doc_name[:512],
                    'stp_confidence': float(chunk.get('stp_confidence', 0.0)),
                    'qualifying_factors': str(chunk.get('qualifying_factors', '') or '')[:65535],
                    'chunk_id': str(chunk.get('chunk_id', f'chunk_{i}'))[:256],
                    'processing_timestamp': str(chunk.get('processing_timestamp', ''))[:100],
                    'tokens': int(chunk.get('tokens', len(rephrased.split()))),
                    'embedding': chunk.get('embedding', [])
                }

                # Validate embedding
                if not isinstance(cleaned_chunk['embedding'], list):
                    continue
                if len(cleaned_chunk['embedding']) != self._get_embedding_dim():
                    continue
                try:
                    cleaned_chunk['embedding'] = [float(x) for x in cleaned_chunk['embedding']]
                except (ValueError, TypeError):
                    continue

                cleaned_data.append(cleaned_chunk)

            except Exception as e:
                logger.error(f"❌ Failed to clean STP chunk {i}: {e}")
                continue

        logger.info(f"Cleaned {len(cleaned_data)}/{len(chunk_data)} STP chunks")
        return cleaned_data

    def generate_embeddings_and_store(self, stp_chunks: List[Dict[str, Any]],
                                     batch_size: int = 32,
                                     overwrite_existing: bool = False,
                                     include_failed_qf: bool = True) -> bool:
        """Generate embeddings for STP chunks and store in Milvus"""
        try:
            if not stp_chunks:
                logger.error("❌ No STP chunks provided")
                return False

            logger.info(f"🚀 Processing {len(stp_chunks)} STP chunks for storage...")

            if not self.collection_initialized:
                if not self._ensure_collection_exists():
                    return False

            if not self._connect_to_milvus():
                return False

            collection_name = self.config['collection']
            collections = self.milvus_client.list_collections()

            if collection_name not in collections:
                logger.error(f"❌ STP collection '{collection_name}' not found")
                return False

            # Prepare data
            texts_for_embedding = []
            chunk_data = []

            for i, chunk in enumerate(stp_chunks):
                try:
                    content = chunk.get('rephrased_content', chunk.get('content', ''))
                    if not content:
                        continue

                    texts_for_embedding.append(str(content))

                    doc_name = None
                    for field in ['doc_name', 'article_link', 'source_file']:
                        if chunk.get(field):
                            doc_name = str(chunk.get(field))
                            break

                    if not doc_name:
                        doc_name = 'Unknown'

                    if not doc_name.startswith(('http://', 'https://')):
                        import os
                        doc_name = os.path.basename(doc_name)

                    chunk_record = {
                        'original_content': str(chunk.get('content', '')),
                        'rephrased_content': str(content),
                        'doc_name': doc_name,
                        'stp_confidence': float(chunk.get('stp_confidence', 0.0)),
                        'qualifying_factors': str(chunk.get('qualifying_factors', '')),
                        'chunk_id': str(chunk.get('chunk_id', f'chunk_{i}')),
                        'processing_timestamp': str(chunk.get('processing_timestamp', '')),
                        'tokens': int(chunk.get('tokens', len(str(content).split())))
                    }
                    chunk_data.append(chunk_record)

                except Exception as chunk_error:
                    logger.warning(f"⚠️ Error processing STP chunk {i}: {chunk_error}")
                    continue

            if not texts_for_embedding:
                logger.error("❌ No valid STP chunks for processing")
                return False

            # Generate embeddings
            logger.info("Generating STP embeddings...")
            embeddings = self._generate_embeddings_batch(texts_for_embedding, batch_size)

            if len(embeddings) != len(chunk_data):
                logger.error(f"❌ STP embedding count mismatch")
                return False

            # Add embeddings to chunk data
            for i, embedding in enumerate(embeddings):
                chunk_data[i]['embedding'] = embedding

            # Validate and clean
            cleaned_chunk_data = self._validate_and_clean_data(chunk_data)

            if not cleaned_chunk_data:
                logger.error("❌ No valid STP chunks after cleaning")
                return False

            # Insert into Milvus
            insert_data = []
            for chunk in cleaned_chunk_data:
                insert_data.append({
                    "original_content": chunk['original_content'],
                    "rephrased_content": chunk['rephrased_content'],
                    "doc_name": chunk['doc_name'],
                    "stp_confidence": chunk['stp_confidence'],
                    "qualifying_factors": chunk['qualifying_factors'],
                    "chunk_id": chunk['chunk_id'],
                    "processing_timestamp": chunk['processing_timestamp'],
                    "tokens": chunk['tokens'],
                    "embedding": chunk['embedding']
                })

            logger.info(f"Inserting {len(insert_data)} STP records into Milvus...")
            res = self.milvus_client.insert(collection_name=collection_name, data=insert_data)
            logger.info(f"✅ Inserted {len(insert_data)} STP records successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to generate embeddings and store STP data: {e}")
            return False
        finally:
            self._disconnect_from_milvus()

    def get_collection_stats(self) -> Optional[Dict[str, Any]]:
        """Get STP collection statistics"""
        try:
            if not self._connect_to_milvus():
                return None

            collection_name = self.config['collection']
            collections = self.milvus_client.list_collections()

            if collection_name not in collections:
                self._disconnect_from_milvus()
                return None

            collection_info = self.milvus_client.describe_collection(collection_name)

            stats = {
                'collection_name': collection_name,
                'database_name': self.config['db_name'],
                'embedding_dim': self._get_embedding_dim(),
                'embedding_model': self.config['embedding_display'],
                'total_entities': collection_info.get('num_entities', 0),
                'collection_initialized': self.collection_initialized
            }

            self._disconnect_from_milvus()
            return stats

        except Exception as e:
            logger.error(f"❌ Failed to get STP collection stats: {e}")
            self._disconnect_from_milvus()
            return None


# Global instances
milvus_storage = MilvusStorage()

logger.info("✅ Milvus storage loaded")
